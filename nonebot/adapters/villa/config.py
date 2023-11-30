from typing import List, Literal, Optional

from pydantic import BaseModel, Extra, Field


class BotInfo(BaseModel):
    bot_id: str
    bot_secret: str
    connection_type: Literal["webhook", "websocket"] = "webhook"
    test_villa_id: int = 0
    pub_key: str
    callback_url: Optional[str] = None
    verify_event: bool = True


class Config(BaseModel, extra=Extra.ignore):
    villa_bots: List[BotInfo] = Field(default_factory=list)
