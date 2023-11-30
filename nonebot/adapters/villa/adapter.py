import asyncio
import json
import time
from typing import Any, Dict, List, Literal, Optional, cast
from typing_extensions import override

from nonebot.adapters import Adapter as BaseAdapter
from nonebot.drivers import (
    URL,
    Driver,
    HTTPClientMixin,
    HTTPServerSetup,
    Request,
    Response,
    ReverseMixin,
    WebSocket,
    WebSocketClientMixin,
)
from nonebot.exception import WebSocketClosed
from nonebot.utils import escape_tag

from pydantic import parse_obj_as

from .bot import Bot
from .config import BotInfo, Config
from .event import (
    Event,
    event_classes,
    pre_handle_event_websocket,
    pre_handle_webhook_event,
)
from .exception import ApiNotAvailable, DisconnectError, ReconnectError
from .models import WebsocketInfo
from .payload import (
    BizType,
    HeartBeat,
    HeartBeatReply,
    KickOff,
    Login,
    LoginReply,
    Logout,
    LogoutReply,
    Payload,
    RobotEvent,
    Shutdown,
)
from .utils import API, log


class Adapter(BaseAdapter):
    bots: Dict[str, Bot]

    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.villa_config: Config = Config(**self.config.dict())
        self.tasks: List[asyncio.Task] = []
        self.ws: Dict[str, WebSocket] = {}
        self.base_url: URL = URL("https://bbs-api.miyoushe.com/vila/api/bot/platform")
        self._setup()

    @classmethod
    @override
    def get_name(cls) -> Literal["Villa"]:
        return "Villa"

    def _setup(self):
        self.driver.on_startup(self._forward_http)
        self.driver.on_startup(self._start_forward)
        self.driver.on_shutdown(self._stop_forwards)

    async def _forward_http(self):
        webhook_bots = [
            bot_info
            for bot_info in self.villa_config.villa_bots
            if bot_info.connection_type == "webhook"
        ]
        if webhook_bots and not (
            isinstance(self.driver, ReverseMixin)
            and isinstance(self.driver, HTTPClientMixin)
        ):
            raise RuntimeError(
                (
                    f"Current driver {self.config.driver}"
                    "doesn't support connections!"
                    "Villa Adapter Webhook need a "
                    "ReverseMixin and HTTPClientMixin to work."
                ),
            )
        for bot_info in webhook_bots:
            if not bot_info.callback_url:
                log(
                    "WARNING",
                    f"<r>Missing callback url for bot {bot_info.bot_id}</r>, "
                    "bot will not be connected",
                )
                continue
            bot = Bot(self, bot_info.bot_id, bot_info)
            self.bot_connect(bot)
            log("INFO", f"<y>Bot {bot.self_id} connected</y>")
            http_setup = HTTPServerSetup(
                URL(bot_info.callback_url),
                "POST",
                f"大别野 {bot_info.bot_id} HTTP",
                self._handle_http,
            )
            self.setup_http_server(http_setup)

    async def _handle_http(self, request: Request) -> Response:
        if data := request.content:
            json_data = json.loads(data)
            if payload_data := json_data.get("event"):
                try:
                    event = parse_obj_as(
                        event_classes,
                        pre_handle_webhook_event(payload_data),
                    )
                    bot_id = event.bot_id
                    if (bot := self.bots.get(bot_id, None)) is None:
                        if (
                            bot_info := next(
                                (
                                    bot
                                    for bot in self.villa_config.villa_bots
                                    if bot.bot_id == bot_id
                                ),
                                None,
                            )
                        ) is not None:
                            bot = Bot(
                                self,
                                bot_info.bot_id,
                                bot_info,
                            )
                            self.bot_connect(bot)
                            log("INFO", f"<y>Bot {bot.self_id} connected</y>")
                        else:
                            log(
                                "WARNING",
                                (
                                    f"<r>Missing bot secret for bot {bot_id}</r>, "
                                    "event will not be handle"
                                ),
                            )
                            return Response(
                                200,
                                content=json.dumps(
                                    {"retcode": 0, "message": "NoneBot2 Get it!"},
                                ),
                            )
                    bot = cast(Bot, bot)
                    if bot.verify_event and (
                        (bot_sign := request.headers.get("x-rpc-bot_sign")) is None
                        or not bot._verify_signature(
                            data.decode() if isinstance(data, bytes) else str(data),
                            bot_sign,
                        )
                    ):
                        log("WARNING", f"Received invalid signature {bot_sign}.")
                        return Response(401, content="Invalid Signature")
                    bot._bot_info = event.robot
                except Exception as e:
                    log(
                        "WARNING",
                        f"Failed to parse event {escape_tag(str(payload_data))}",
                        e,
                    )
                else:
                    asyncio.create_task(bot.handle_event(event))
                return Response(
                    200,
                    content=json.dumps({"retcode": 0, "message": "NoneBot2 Get it!"}),
                )
            return Response(415, content="Invalid Request Body")
        return Response(415, content="Invalid Request Body")

    async def _start_forward(self) -> None:
        ws_bots = [
            bot_info
            for bot_info in self.villa_config.villa_bots
            if bot_info.connection_type == "websocket"
        ]
        if ws_bots and not (
            isinstance(self.driver, HTTPClientMixin)
            and isinstance(self.driver, WebSocketClientMixin)
        ):
            raise RuntimeError(
                f"Current driver {self.config.driver}"
                "doesn't support connections!"
                "Villa Adapter Websocket need a "
                "HTTPClientMixin and WebSocketClientMixin to work.",
            )
        for bot_config in ws_bots:
            if bot_config.connection_type == "websocket":
                bot = Bot(self, bot_config.bot_id, bot_config)
                ws_info = await bot.get_websocket_info()
                self.tasks.append(
                    asyncio.create_task(
                        self._forward_ws(bot, bot_config, ws_info),
                    ),
                )

    async def _forward_ws(
        self,
        bot: Bot,
        bot_config: BotInfo,
        ws_info: WebsocketInfo,
    ) -> None:
        request = Request(method="GET", url=URL(ws_info.websocket_url), timeout=30.0)
        heartbeat_task: Optional["asyncio.Task"] = None
        while True:
            try:
                async with self.websocket(request) as ws:
                    log(
                        "DEBUG",
                        "WebSocket Connection to"
                        f" {escape_tag(ws_info.websocket_url)} established",
                    )
                    try:
                        # 登录
                        result = await self._login(bot, ws, bot_config, ws_info)
                        if not result:
                            await asyncio.sleep(3.0)
                            continue

                        # 开启心跳
                        heartbeat_task = asyncio.create_task(
                            self._heartbeat(bot, ws),
                        )

                        # 处理事件
                        await self._loop(bot, ws)
                    except DisconnectError as e:
                        raise e
                    except ReconnectError as e:
                        log("ERROR", str(e), e)
                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            (
                                "<r><bg #f8bbd0>Error while process data from"
                                f" websocket {escape_tag(ws_info.websocket_url)}. "
                                "Trying to reconnect...</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        if bot.self_id in self.bots:
                            bot._ws_squence = 0
                            self.ws.pop(bot.self_id)
                            self.bot_disconnect(bot)
                        if heartbeat_task:
                            heartbeat_task.cancel()
                            heartbeat_task = None
            except DisconnectError:
                return
            except Exception as e:
                log(
                    "ERROR",
                    (
                        "<r><bg #f8bbd0>Error while setup websocket to"
                        f" {escape_tag(ws_info.websocket_url)}. "
                        "Trying to reconnect...</bg #f8bbd0></r>"
                    ),
                    e,
                )
                await asyncio.sleep(3.0)

    async def _stop_forwards(self) -> None:
        await asyncio.gather(
            *[
                self._stop_forward(self.bots[bot[0]], bot[1], task)
                for bot, task in zip(self.ws.items(), self.tasks)
            ],
        )

    async def _stop_forward(
        self,
        bot: Bot,
        ws: WebSocket,
        task: "asyncio.Task",
    ) -> None:
        await self._logout(bot, ws)
        await asyncio.sleep(1.0)
        if not task.done():
            task.cancel()

    async def _login(
        self,
        bot: Bot,
        ws: WebSocket,
        bot_config: BotInfo,
        ws_info: WebsocketInfo,
    ):
        try:
            login = Login(
                ws_info.uid,
                str(bot_config.test_villa_id)
                + f".{bot.bot_secret_encrypt}.{bot.self_id}",
                ws_info.platform,
                ws_info.app_id,
                ws_info.device_id,
            )
            log("TRACE", f"Sending Login {escape_tag(repr(login))}")
            await ws.send_bytes(login.to_bytes_package(bot._ws_squence))
            bot._ws_squence += 1

        except Exception as e:
            log(
                "ERROR",
                "<r><bg #f8bbd0>Error while sending Login</bg #f8bbd0></r>",
                e,
            )
            return None
        login_reply = await self.receive_payload(ws)
        if not isinstance(login_reply, LoginReply):
            log(
                "ERROR",
                "Received unexpected event while login: "
                f"{escape_tag(repr(login_reply))}",
            )
            return None
        if login_reply.code == 0:
            bot.ws_info = ws_info
            if bot.self_id not in self.bots:
                self.bot_connect(bot)
                self.ws[bot.self_id] = ws
                log(
                    "INFO",
                    f"<y>Bot {escape_tag(bot.self_id)}</y> connected",
                )
            return True
        return None

    async def _logout(self, bot: Bot, ws: WebSocket):
        try:
            await ws.send_bytes(
                Logout(
                    uid=bot.ws_info.uid,
                    platform=bot.ws_info.platform,
                    app_id=bot.ws_info.app_id,
                    device_id=bot.ws_info.device_id,
                ).to_bytes_package(bot._ws_squence),
            )
            bot._ws_squence += 1
        except Exception as e:
            log("WARNING", "Error while sending logout, Ignored!", e)

    async def _heartbeat(self, bot: Bot, ws: WebSocket):
        while True:
            await asyncio.sleep(20.0)
            timestamp = str(int(time.time() * 1000))
            log("TRACE", f"Heartbeat {timestamp}")
            try:
                await ws.send_bytes(
                    HeartBeat(timestamp).to_bytes_package(bot._ws_squence),
                )
                bot._ws_squence += 1
            except Exception as e:
                log("WARNING", "Error while sending heartbeat, Ignored!", e)

    async def _loop(self, bot: Bot, ws: WebSocket):
        while True:
            payload = await self.receive_payload(ws)
            if not payload:
                raise ReconnectError
            if isinstance(payload, HeartBeatReply):
                log("TRACE", f"Heartbeat ACK in {payload.server_timestamp}")
                continue
            if isinstance(payload, (LogoutReply, KickOff)):
                if isinstance(payload, KickOff):
                    log("WARNING", f"Bot {bot.self_id} kicked off by server: {payload}")
                    raise DisconnectError
                log("INFO", f"<y>Bot {bot.self_id} disconnected: {payload}</y>")
                if bot.self_id in self.bots:
                    self.ws.pop(bot.self_id)
                    self.bot_disconnect(bot)
            if isinstance(payload, Event):
                bot._bot_info = payload.robot
                asyncio.create_task(bot.handle_event(payload))

    @staticmethod
    async def receive_payload(ws: WebSocket):
        payload = Payload.from_bytes(await ws.receive_bytes())
        if payload.biz_type in {BizType.P_LOGIN, BizType.P_LOGOUT, BizType.P_HEARTBEAT}:
            if payload.biz_type == BizType.P_LOGIN:
                payload = LoginReply.FromString(payload.body_data)
            elif payload.biz_type == BizType.P_LOGOUT:
                payload = LogoutReply.FromString(payload.body_data)
            else:
                payload = HeartBeatReply.FromString(payload.body_data)
            if payload.code != 0:
                if isinstance(payload, LogoutReply):
                    log("WARNING", f"Error when logout from server: {payload}")
                    return payload
                raise ReconnectError(payload)
        elif payload.biz_type == BizType.P_KICK_OFF:
            payload = KickOff.FromString(payload.body_data)
        elif payload.biz_type == BizType.SHUTDOWN:
            payload = Shutdown()
        elif payload.biz_type == BizType.EVENT:
            event_data = RobotEvent.FromString(payload.body_data)
            return parse_obj_as(
                event_classes,
                pre_handle_event_websocket(event_data),
            )
        else:
            raise ReconnectError
        log("TRACE", f"Received payload: {escape_tag(repr(payload))}")
        return payload

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        log("DEBUG", f"Calling API <y>{api}</y>")
        log("TRACE", f"With Data <y>{escape_tag(str(data))}</y>")
        api_handler: Optional[API] = getattr(bot.__class__, api, None)
        if api_handler is None:
            raise ApiNotAvailable(api)
        return await api_handler(bot, **data)
