import json
import asyncio
from typing import Any, cast

from pydantic import parse_obj_as
from nonebot.typing import overrides
from nonebot.utils import escape_tag
from nonebot.drivers import (
    URL,
    Driver,
    Request,
    Response,
    ForwardDriver,
    ReverseDriver,
    HTTPServerSetup,
)

from nonebot.adapters import Adapter as BaseAdapter

from .bot import Bot
from .utils import log
from .config import Config
from .api import API_HANDLERS
from .exception import ApiNotAvailable
from .event import event_classes, pre_handle_event


class Adapter(BaseAdapter):
    @overrides(BaseAdapter)
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.villa_config: Config = Config(**self.config.dict())
        self.base_url: URL = URL("https://bbs-api.miyoushe.com")
        self._setup()

    @classmethod
    @overrides(BaseAdapter)
    def get_name(cls) -> str:
        return "大别野"

    def _setup(self):
        # ReverseDriver用于接收回调事件，ForwardDriver用于调用API
        if not (
            isinstance(self.driver, ReverseDriver)
            and isinstance(self.driver, ForwardDriver)
        ):
            raise RuntimeError(
                f"Current driver {self.config.driver} doesn't support connections!"
                "Villa Adapter need a ReverseDriver and ForwardDriver to work."
            )
        for bot_info in self.villa_config.villa_bots:
            # TODO: 在启动时就先将Bot添加到bots中，而不是在收到事件时再添加
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
                            bot_secret := next(
                                (
                                    bot.bot_secret
                                    for bot in self.villa_config.villa_bots
                                    if bot.bot_id == bot_id
                                ),
                                None,
                            )
                        ) is not None:
                            bot = Bot(self, bot_id, event.robot, bot_secret=bot_secret)
                            self.bot_connect(bot)
                            log("INFO", f"<y>Bot {bot.self_id} connected</y>")
                        else:
                            log(
                                "WARNING",
                                f"<r>Missing bot secret for bot {bot_id}</r>, event will not be handle",
                            )
                            return Response(
                                200,
                                content=json.dumps(
                                    {"retcode": 0, "message": "NoneBot2 Get it!"}
                                ),
                            )
                    bot = cast(Bot, bot)
                    bot._bot_info = event.robot
                except Exception as e:
                    log(
                        "WARNING",
                        f"Failed to parse event {escape_tag(str(payload_data))}",
                        e,
                    )
                else:
                    asyncio.create_task(bot.handle_event(event))
                # (Path().cwd() / f'test_event_{payload.created_at}.json').write_text(json.dumps(json_data, indent=4, ensure_ascii=False), encoding='utf-8')
                return Response(
                    200,
                    content=json.dumps({"retcode": 0, "message": "NoneBot2 Get it!"}),
                )
            return Response(400, content="Invalid Request Body")
        return Response(400, content="Invalid Request Body")

    @overrides(BaseAdapter)
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        log("DEBUG", f"Calling API <y>{api}</y>")
        log("TRACE", f"With Data <y>{escape_tag(str(data))}</y>")
        if (api_handler := API_HANDLERS.get(api)) is None:
            raise ApiNotAvailable(api)
        return await api_handler(self, bot, **data)
