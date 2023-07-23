import asyncio
import json
from typing import Any, List, Optional, cast
from typing_extensions import override

from nonebot.adapters import Adapter as BaseAdapter
from nonebot.drivers import (
    URL,
    Driver,
    ForwardDriver,
    HTTPServerSetup,
    Request,
    Response,
    ReverseDriver,
)
from nonebot.exception import WebSocketClosed
from nonebot.utils import escape_tag

from pydantic import parse_obj_as

from .api import API_HANDLERS
from .bot import Bot
from .config import Config
from .event import event_classes, pre_handle_event
from .exception import ApiNotAvailable
from .utils import log


class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.villa_config: Config = Config(**self.config.dict())
        self.tasks: List[asyncio.Task] = []
        self.base_url: URL = URL("https://bbs-api.miyoushe.com")
        self._setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        return "大别野"

    def _setup(self):
        # ReverseDriver用于接收回调事件，ForwardDriver用于调用API
        if not (
            isinstance(self.driver, ReverseDriver)
            and isinstance(self.driver, ForwardDriver)
        ):
            raise RuntimeError(
                (
                    f"Current driver {self.config.driver} doesn't support connections!"
                    "Villa Adapter need a ReverseDriver and ForwardDriver to work."
                ),
            )
        self.driver.on_startup(self._forward_http)
        self.driver.on_startup(self._start_forward)
        self.driver.on_shutdown(self._stop_forward)

    async def _forward_http(self):
        for bot_info in self.villa_config.villa_bots:
            if bot_info.callback_url:
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
                    event = parse_obj_as(event_classes, pre_handle_event(payload_data))
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
                            data.decode() if isinstance(data, bytes) else data,
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
        for bot_info in self.villa_config.villa_bots:
            if bot_info.ws_url:
                bot = Bot(self, bot_info.bot_id, bot_info)
                self.bot_connect(bot)
                log("INFO", f"<y>Bot {bot.self_id} connected</y>")
                self.tasks.append(
                    asyncio.create_task(
                        self._forward_ws(URL(bot_info.ws_url), bot_info.ws_secret),
                    ),
                )

    async def _forward_ws(self, url: URL, secret: Optional[str] = None):
        if secret is not None:
            request = Request("GET", url, headers={"ws-secret": secret}, timeout=30)
        else:
            request = Request("GET", url, timeout=30)
        bot: Optional[Bot] = None
        while True:
            try:
                async with self.websocket(request) as ws:
                    log(
                        "DEBUG",
                        f"WebSocket Connection to {escape_tag(str(url))} established",
                    )
                    try:
                        while True:
                            data = await ws.receive()
                            json_data = json.loads(data)
                            if payload_data := json_data.get("event"):
                                try:
                                    event = parse_obj_as(
                                        event_classes,
                                        pre_handle_event(payload_data),
                                    )
                                    bot_id = event.bot_id
                                    if (bot := self.bots.get(bot_id, None)) is None:  # type: ignore  # noqa: E501
                                        if (
                                            bot_info := next(
                                                (
                                                    bot
                                                    for bot in self.villa_config.villa_bots  # noqa: E501
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
                                            log(
                                                "INFO",
                                                f"<y>Bot {bot.self_id} connected</y>",
                                            )
                                        else:
                                            log(
                                                "WARNING",
                                                (
                                                    "<r>Missing bot secret for bot"
                                                    f" {bot_id}</r>, event won't be"
                                                    " handle"
                                                ),
                                            )
                                            await ws.send(
                                                json.dumps(
                                                    {
                                                        "retcode": 0,
                                                        "message": "NoneBot2 Get it!",
                                                    },
                                                ),
                                            )
                                    bot = cast(Bot, bot)
                                    bot._bot_info = event.robot
                                except Exception as e:
                                    log(
                                        "WARNING",
                                        (
                                            "Failed to parse event "
                                            f"{escape_tag(str(payload_data))}"
                                        ),
                                        e,
                                    )
                                else:
                                    asyncio.create_task(bot.handle_event(event))
                                await ws.send(
                                    json.dumps(
                                        {"retcode": 0, "message": "NoneBot2 Get it!"},
                                    ),
                                )
                            else:
                                await ws.send(
                                    json.dumps(
                                        {
                                            "retcode": -100,
                                            "message": "Invalid Request Body",
                                        },
                                    ),
                                )
                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            (  # noqa: E501
                                "<r><bg #f8bbd0>Error while process data from"
                                f" websocket {escape_tag(str(url))}. Trying to"
                                " reconnect...</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        if bot:
                            self.bot_disconnect(bot)
            except Exception as e:
                log(
                    "ERROR",
                    (
                        "<r><bg #f8bbd0>Error while setup websocket to"
                        f" {escape_tag(str(url))}. Trying to reconnect...</bg"
                        " #f8bbd0></r>"
                    ),
                    e,
                )
                await asyncio.sleep(3.0)

    async def _stop_forward(self) -> None:
        for task in self.tasks:
            if not task.done():
                task.cancel()

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        log("DEBUG", f"Calling API <y>{api}</y>")
        log("TRACE", f"With Data <y>{escape_tag(str(data))}</y>")
        if (api_handler := API_HANDLERS.get(api)) is None:
            raise ApiNotAvailable(api)
        return await api_handler(self, bot, **data)
