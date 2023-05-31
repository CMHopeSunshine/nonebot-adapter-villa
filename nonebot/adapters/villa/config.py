from typing import List

from pydantic import Extra, Field, BaseModel


class BotInfo(BaseModel):
    bot_id: str
    bot_secret: str
    callback_url: str


class Config(BaseModel, extra=Extra.ignore):
    villa_bots: List[BotInfo] = Field(default_factory=list)
