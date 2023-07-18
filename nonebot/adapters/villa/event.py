from enum import IntEnum
import json
from typing import Any, Dict, Literal, Optional, Union
from typing_extensions import override

from nonebot.adapters import Event as BaseEvent
from nonebot.utils import escape_tag

from pydantic import root_validator

from .api import MessageContentInfoGet, Robot
from .message import Message, MessageSegment


class EventType(IntEnum):
    """事件类型"""

    JoinVilla = 1
    SendMessage = 2
    CreateRobot = 3
    DeleteRobot = 4
    AddQuickEmoticon = 5
    AuditCallback = 6


class AuditResult(IntEnum):
    """审核结果类型"""

    Compatibility = 0
    """兼容"""
    Pass = 1
    """通过"""
    Reject = 2
    """驳回"""


class Event(BaseEvent):
    """Villa 事件基类"""

    robot: Robot
    """用户机器人访问凭证"""
    type: EventType
    """事件类型"""
    id: str
    """事件 id"""
    created_at: int
    """事件创建时间"""
    send_at: int
    """事件回调时间"""

    @property
    def bot_id(self) -> str:
        """机器人ID"""
        return self.robot.template.id

    @override
    def get_event_name(self) -> str:
        return self.type.name

    @override
    def get_event_description(self) -> str:
        return escape_tag(repr(self.dict()))

    @override
    def get_message(self):
        raise ValueError("Event has no message!")

    @override
    def get_user_id(self) -> str:
        raise ValueError("Event has no context!")

    @override
    def get_session_id(self) -> str:
        return f"{self.robot.villa_id}_{self.id}"

    @override
    def is_tome(self) -> bool:
        return False


class NoticeEvent(Event):
    """通知事件"""

    @override
    def get_type(self) -> str:
        return "notice"


class MessageEvent(Event):
    """消息事件

    但目前大别野只有SendMessageEvent这一种消息事件，所以推荐直接使用SendMessageEvent"""

    @override
    def get_type(self) -> str:
        return "message"


class JoinVillaEvent(NoticeEvent):
    """新用户加入大别野事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###JoinVilla"""

    type: Literal[EventType.JoinVilla] = EventType.JoinVilla
    join_uid: int
    """用户ID"""
    join_user_nickname: str
    """用户昵称"""
    join_at: int
    """用户加入时间的时间戳"""

    @property
    def villa_id(self) -> int:
        """大别野ID"""
        return self.robot.villa_id

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            (
                f"User(nickname={self.join_user_nickname},id={self.join_uid}) "
                f"join Villa(id={self.villa_id})"
            ),
        )

    @override
    def get_user_id(self) -> str:
        return str(self.join_uid)

    @override
    def get_session_id(self) -> str:
        return f"{self.villa_id}_{self.join_uid}"


class SendMessageEvent(MessageEvent):
    """用户@机器人发送消息事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###SendMessage"""

    type: Literal[EventType.SendMessage] = EventType.SendMessage
    content: MessageContentInfoGet
    """消息内容"""
    from_user_id: int
    """发送者ID"""
    send_at: int
    """发送时间的时间戳"""
    room_id: int
    """房间ID"""
    object_name: int
    """目前只支持文本类型消息"""
    nickname: str
    """用户昵称"""
    msg_uid: str
    """消息ID"""
    bot_msg_id: Optional[str]
    """如果被回复的消息从属于机器人，则该字段不为空字符串"""

    to_me: bool = True
    """是否和Bot有关"""
    message: Message
    """事件消息"""
    raw_message: Message
    """事件原始消息"""

    @property
    def villa_id(self) -> int:
        """大别野ID"""
        return self.robot.villa_id

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            (
                f"Message(id={self.msg_uid}) was sent from"
                f" User(nickname={self.nickname}, id={self.from_user_id}) in"
                f" Room(id={self.room_id}) of Villa(id={self.villa_id}),"
                f" content={repr(self.message)}"
            ),
        )

    @override
    def get_message(self) -> Message:
        """获取事件消息"""
        return self.message

    @override
    def is_tome(self) -> bool:
        """是否和Bot有关"""
        return self.to_me

    @override
    def get_user_id(self) -> str:
        """获取用户ID"""
        return str(self.from_user_id)

    @override
    def get_session_id(self) -> str:
        """获取会话ID"""
        return f"{self.villa_id}_{self.room_id}_{self.from_user_id}"

    @root_validator(pre=True)
    @classmethod
    def _(cls, data: Dict[str, Any]):
        if not data.get("content"):
            return data
        msg = Message()
        data["content"] = json.loads(data["content"])
        msg_content_info = data["content"]
        if quote := msg_content_info.get("quote"):
            msg.append(
                MessageSegment.quote(
                    message_id=quote["quoted_message_id"],
                    message_send_time=quote["quoted_message_send_time"],
                ),
            )

        content = msg_content_info["content"]
        text = content["text"]
        entities = content["entities"]
        if not entities:
            return Message(MessageSegment.text(text))
        text = text.encode("utf-16")
        last_offset: int = 0
        last_length: int = 0
        for entity in entities:
            end_offset: int = last_offset + last_length
            offset: int = entity["offset"]
            length: int = entity["length"]
            entity_detail = entity["entity"]
            if offset != end_offset:
                msg.append(
                    MessageSegment.text(
                        text[((end_offset + 1) * 2) : ((offset + 1) * 2)].decode(
                            "utf-16",
                        ),
                    ),
                )
            entity_text = text[(offset + 1) * 2 : (offset + length + 1) * 2].decode(
                "utf-16",
            )
            if entity_detail["type"] == "mentioned_robot":
                entity_detail["bot_name"] = entity_text.lstrip("@")[:-1]
                msg.append(
                    MessageSegment.mention_robot(
                        entity_detail["bot_id"],
                        entity_detail["bot_name"],
                    ),
                )
            elif entity_detail["type"] == "mentioned_user":
                entity_detail["user_name"] = entity_text.lstrip("@")[:-1]
                msg.append(
                    MessageSegment.mention_user(
                        int(entity_detail["user_id"]),
                        data["villa_id"],
                    ),
                )
            elif entity_detail["type"] == "mention_all":
                entity_detail["show_text"] = entity_text.lstrip("@")[:-1]
                msg.append(MessageSegment.mention_all(entity_detail["show_text"]))
            elif entity_detail["type"] == "villa_room_link":
                entity_detail["room_name"] = entity_text.lstrip("#")[:-1]
                msg.append(
                    MessageSegment.room_link(
                        int(entity_detail["villa_id"]),
                        int(entity_detail["room_id"]),
                    ),
                )
            else:
                entity_detail["show_text"] = entity_text
                msg.append(MessageSegment.link(entity_detail["url"], entity_text))
            last_offset = offset
            last_length = length
        end_offset = last_offset + last_length
        if last_text := text[(end_offset + 1) * 2 :].decode("utf-16"):
            msg.append(MessageSegment.text(last_text))
        data["message"] = msg
        data["raw_message"] = msg
        return data


class CreateRobotEvent(NoticeEvent):
    """大别野添加机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###CreateRobot"""

    type: Literal[EventType.CreateRobot] = EventType.CreateRobot
    villa_id: int
    """大别野ID"""

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            f"Bot(id={self.bot_id}) was added to Villa(id={self.villa_id})",
        )

    @override
    def is_tome(self) -> bool:
        return True

    @override
    def get_session_id(self) -> str:
        return f"{self.villa_id}_{self.bot_id}"


class DeleteRobotEvent(NoticeEvent):
    """大别野删除机器人实例事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html###DeleteRobot"""

    type: Literal[EventType.DeleteRobot] = EventType.DeleteRobot
    villa_id: int
    """大别野ID"""

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            f"Bot(id={self.bot_id}) was removed from Villa(id={self.villa_id})",
        )

    @override
    def is_tome(self) -> bool:
        return True

    @override
    def get_session_id(self) -> str:
        return f"{self.villa_id}_{self.bot_id}"


class AddQuickEmoticonEvent(NoticeEvent):
    """用户使用表情回复消息表态事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AddQuickEmoticon"""

    type: Literal[EventType.AddQuickEmoticon] = EventType.AddQuickEmoticon
    villa_id: int
    """大别野ID"""
    room_id: int
    """房间ID"""
    uid: int
    """发送表情的用户ID"""
    emoticon_id: int
    """表情ID"""
    emoticon: str
    """表情内容"""
    msg_uid: str
    """被回复的消息 id"""
    bot_msg_id: Optional[str]
    """如果被回复的消息从属于机器人，则该字段不为空字符串"""
    is_cancel: bool = False
    """是否是取消表情"""

    @override
    def get_user_id(self) -> str:
        return str(self.uid)

    @override
    def is_tome(self) -> bool:
        return True

    @override
    def get_session_id(self) -> str:
        return (
            f"{self.villa_id}_{self.room_id}_{self.uid}"
            f"_{self.emoticon_id}_{self.is_cancel}"
        )

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            (
                f"Emoticon(name={self.emoticon}, id={self.emoticon_id}) was "
                f"{'removed from' if self.is_cancel else 'added to'} "
                f"Message(id={self.msg_uid}) by User(id={self.uid}) in "
                f"Room(id=Villa(id={self.room_id}) of Villa(id={self.villa_id})"
            ),
        )


class AuditCallbackEvent(NoticeEvent):
    """审核结果回调事件

    see https://webstatic.mihoyo.com/vila/bot/doc/callback.html#AuditCallback"""

    type: Literal[EventType.AuditCallback] = EventType.AuditCallback
    audit_id: str
    """审核事件 id"""
    bot_tpl_id: str
    """机器人 id"""
    villa_id: int
    """大别野 ID"""
    room_id: int
    """房间 id（和审核接口调用方传入的值一致）"""
    user_id: int
    """用户 id（和审核接口调用方传入的值一致）"""
    pass_through: str
    """透传数据（和审核接口调用方传入的值一致）"""
    audit_result: AuditResult
    """审核结果"""

    @override
    def get_user_id(self) -> str:
        return str(self.user_id)

    @override
    def is_tome(self) -> bool:
        return self.bot_id == self.bot_tpl_id

    @override
    def get_session_id(self) -> str:
        return f"{self.villa_id}_{self.bot_tpl_id}_{self.audit_id}"

    @override
    def get_event_description(self) -> str:
        return escape_tag(
            (
                f"Audit(id={self.audit_id},result={self.audit_result}) of "
                f"User(id={self.user_id}) in Room(id={self.room_id}) of "
                f"Villa(id={self.villa_id})"
            ),
        )


event_classes = Union[
    JoinVillaEvent,
    SendMessageEvent,
    CreateRobotEvent,
    DeleteRobotEvent,
    AddQuickEmoticonEvent,
    AuditCallbackEvent,
]


def pre_handle_event(payload: Dict[str, Any]):
    if (event_type := EventType._value2member_map_.get(payload["type"])) is None:
        raise ValueError(
            f"Unknown event type: {payload['type']} data={escape_tag(str(payload))}",
        )
    event_name = event_type.name
    if event_name not in payload["extend_data"]["EventData"]:
        raise ValueError("Cannot find event data for event type: {event_name}")
    payload.update(payload["extend_data"]["EventData"][event_name])
    payload.pop("extend_data")
    return payload


__all__ = [
    "Event",
    "NoticeEvent",
    "MessageEvent",
    "JoinVillaEvent",
    "SendMessageEvent",
    "CreateRobotEvent",
    "DeleteRobotEvent",
    "AddQuickEmoticonEvent",
    "AuditCallbackEvent",
]
