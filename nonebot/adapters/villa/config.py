from typing import List, Optional

from pydantic import BaseModel, Extra, Field, root_validator


class BotInfo(BaseModel):
    bot_id: str
    bot_secret: str
    pub_key: str
    callback_url: Optional[str] = None
    ws_url: Optional[str] = None
    ws_secret: Optional[str] = None
    verify_event: bool = True

    # 不能同时存在 callback_url 和 ws_url
    @root_validator
    @classmethod
    def check_url(cls, values):
        if values.get("callback_url") and values.get("ws_url"):
            raise ValueError("callback_url and ws_url cannot exist at the same time")
        return values


class Config(BaseModel, extra=Extra.ignore):
    villa_bots: List[BotInfo] = Field(default_factory=list)
