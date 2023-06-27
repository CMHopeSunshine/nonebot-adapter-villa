from typing import List, Optional

from pydantic import Extra, Field, BaseModel


class BotInfo(BaseModel):
    bot_id: str
    bot_secret: str
    callback_url: Optional[str] = None
    ws_url: Optional[str] = None
    ws_secret: Optional[str] = None


class Config(BaseModel, extra=Extra.ignore):
    villa_bots: List[BotInfo] = Field(default_factory=list)
