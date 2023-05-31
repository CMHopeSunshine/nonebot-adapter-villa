import json
from enum import IntEnum
from typing import Any, Dict, Type, Optional

from pydantic import validator
from nonebot.typing import overrides
from nonebot.utils import escape_tag

from nonebot.adapters import Event as BaseEvent

from .message import Message
from .api import MessageContentInfo


class EventType(IntEnum):
    JoinVilla = 1
    SendMessage = 2
    CreateRobot = 3
    DeleteRobot = 4
    AddQuickEmoticon = 5
    AuditCallback = 6


class AuditResult(IntEnum):
    Compatibility = 0
    Pass = 1
    Reject = 2


class Event(BaseEvent):
    """Villa 事件"""

    __type__: EventType

    @overrides(BaseEvent)
    def get_event_name(self) -> str:
        return self.__type__.name

    @overrides(BaseEvent)
    def get_event_description(self) -> str:
        return escape_tag(str(self.dict()))

    @overrides(BaseEvent)
    def get_message(self):
        raise ValueError("Event has no message!")

    @overrides(BaseEvent)
    def get_user_id(self) -> str:
        raise ValueError("Event has no context!")

    @overrides(BaseEvent)
    def get_session_id(self) -> str:
        raise ValueError("Event has no context!")

    @overrides(BaseEvent)
    def is_tome(self) -> bool:
        return False


class NoticeEvent(Event):
    @overrides(BaseEvent)
    def get_type(self) -> str:
        return "notice"


class MessageEvent(Event):
    @overrides(BaseEvent)
    def get_type(self) -> str:
        return "message"


class JoinVillaEvent(NoticeEvent):
    __type__ = EventType.JoinVilla
    join_uid: int
    join_user_nickname: str
    join_at: int

    @overrides(BaseEvent)
    def get_user_id(self) -> str:
        return str(self.join_uid)

    @overrides(BaseEvent)
    def get_session_id(self) -> str:
        return str(self.join_uid)


class SendMessageEvent(MessageEvent):
    __type__ = EventType.SendMessage
    content: MessageContentInfo
    from_user_id: int
    send_at: int
    room_id: int
    object_name: int
    nickname: str
    msg_uid: str
    bot_msg_id: Optional[str]

    to_me: bool = False

    @overrides(BaseEvent)
    def get_message(self) -> Message:
        if not hasattr(self, "_message"):
            setattr(self, "_message", Message.parse(self.content))
        return getattr(self, "_message")

    @overrides(Event)
    def is_tome(self) -> bool:
        return self.to_me

    @overrides(BaseEvent)
    def get_user_id(self) -> str:
        return str(self.from_user_id)

    @overrides(BaseEvent)
    def get_session_id(self) -> str:
        return f"{self.room_id}-{self.from_user_id}"

    @validator("content", pre=True)
    def content_str_to_dict(cls, v: Any):
        if isinstance(v, str):
            return json.loads(v)
        return v


class CreateRobotEvent(NoticeEvent):
    __type__ = EventType.CreateRobot
    villa_id: int


class DeleteRobotEvent(Event):
    __type__ = EventType.DeleteRobot
    villa_id: int

    @overrides(BaseEvent)
    def get_type(self) -> str:
        return "notice"


class AddQuickEmoticonEvent(NoticeEvent):
    __type__ = EventType.AddQuickEmoticon
    villa_id: int
    room_id: int
    uid: int
    emoticon_id: int
    emoticon: str
    msg_uid: str
    bot_msg_id: Optional[str]
    is_cancel: bool = False


class AuditCallback(NoticeEvent):
    __type__ = EventType.AuditCallback
    audit_id: str
    bot_tpl_id: str
    villa_id: int
    room_id: int
    user_id: int
    pass_through: str
    audit_result: AuditResult


event_classes: Dict[int, Type[Event]] = {
    EventType.JoinVilla.value: JoinVillaEvent,
    EventType.SendMessage.value: SendMessageEvent,
    EventType.CreateRobot.value: CreateRobotEvent,
    EventType.DeleteRobot.value: DeleteRobotEvent,
    EventType.AddQuickEmoticon.value: AddQuickEmoticonEvent,
    EventType.AuditCallback.value: AuditCallback,
}

__all__ = [
    "Event",
    "NoticeEvent",
    # "MessageEvent",
    "JoinVillaEvent",
    "SendMessageEvent",
    "CreateRobotEvent",
    "DeleteRobotEvent",
    "AddQuickEmoticonEvent",
    "AuditCallback",
]
