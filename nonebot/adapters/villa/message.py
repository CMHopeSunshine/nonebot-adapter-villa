from typing import Type, Union, Iterable, Optional

from nonebot.typing import overrides
from nonebot.utils import escape_tag

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment


class MessageSegment(BaseMessageSegment["Message"]):
    @classmethod
    @overrides(BaseMessageSegment)
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @overrides(BaseMessageSegment)
    def __add__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return super().__add__(other)

    @overrides(BaseMessageSegment)
    def __radd__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return super().__radd__(other)

    @overrides(BaseMessageSegment)
    def is_text(self) -> bool:
        return self.type == "text"

    @staticmethod
    def text(text: str) -> "TextSegment":
        """纯文本消息段

        参数:
            text: 文本内容

        返回:
            TextSegment: 消息段对象
        """
        return TextSegment("text", {"text": text})

    @staticmethod
    def mention_robot(bot_id: str, bot_name: str) -> "MentionRobotSegement":
        """@机器人消息段

        参数:
            bot_id: 机器人ID
            bot_name: 机器人的名字

        返回:
            MentionRobotSegement: 消息段对象
        """
        return MentionRobotSegement(
            "mentioned_robot", {"bot_id": bot_id, "bot_name": bot_name}
        )

    @staticmethod
    def mention_user(villa_id: int, user_id: int) -> "MentionUserSegement":
        """@用户消息段

        参数:
            villa_id: 用户所在大别野ID
            user_id: 用户ID

        返回:
            MentionUserSegement: 消息段对象
        """
        return MentionUserSegement(
            "mentioned_user", {"villa_id": villa_id, "user_id": user_id}
        )

    @staticmethod
    def mention_all(show_text: str = "全体成员") -> "MentionAllSegement":
        """@全体成员消息段"""
        return MentionAllSegement("mention_all", {"show_text": show_text})

    @staticmethod
    def room_link(villa_id: int, room_id: int) -> "RoomLinkSegment":
        """房间链接消息段，点击后可以跳转到指定房间

        参数:
            villa_id: 大别野ID
            room_id: 房间ID

        返回:
            VillaRoomLinkSegment: 消息段对象
        """
        return RoomLinkSegment(
            "villa_room_link", {"villa_id": villa_id, "room_id": room_id}
        )

    @staticmethod
    def link(url: str, show_text: Optional[str] = None) -> "LinkSegment":
        """链接消息段，使用该消息段才能让链接可以直接点击进行跳转

        参数:
            url: 链接
            show_text: 链接显示的文本

        返回:
            LinkSegment: 消息段对象
        """
        return LinkSegment("link", {"url": url, "show_text": show_text or url})

    @staticmethod
    def quote(message_id: str, message_send_time: int) -> "QuoteSegment":
        """引用(回复)消息段

        参数:
            message_id: 被引用的消息ID
            message_send_time: 被引用的消息发送时间

        返回:
            QuoteSegment: 消息段对象
        """
        return QuoteSegment(
            "quote", {"msg_id": message_id, "msg_send_time": message_send_time}
        )

    @staticmethod
    def image(
        url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> "ImageSegment":
        """图片消息段

        参数:
            url: 图片链接
            width: 图片宽度
            height: 图片高度
            file_size: 图片大小

        返回:
            ImageSegment: 消息段对象
        """
        return ImageSegment(
            "image",
            {"url": url, "width": width, "height": height, "file_size": file_size},
        )

    @staticmethod
    def post(post_id: str) -> "PostSegment":
        """帖子转发消息段

        参数:
            post_id: 帖子ID

        返回:
            PostSegment: 消息段对象
        """
        return PostSegment("post", {"post_id": post_id})


class TextSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return escape_tag(self.data["text"])


class MentionRobotSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<MentionRobot:bot_id={self.data['bot_id']} bot_name={self.data['bot_name']}>"


class MentionUserSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<MentionUser:user_id={self.data['user_id']}>"


class MentionAllSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<MentionAll:show_text={self.data['show_text']}>"


class RoomLinkSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<RoomLink:villa_id={self.data['villa_id']} room_id={self.data['room_id']}>"


class LinkSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"Link:url={self.data['url']}"


class ImageSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<Image:url={self.data['url']}>"


class QuoteSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<Quote:msg_id={self.data['msg_id']}>"


class PostSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<Post:post_id={self.data['post_id']}>"


class Message(BaseMessage[MessageSegment]):
    @classmethod
    @overrides(BaseMessage)
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    @overrides(BaseMessage)
    def __add__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> "Message":
        return super(Message, self).__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @overrides(BaseMessage)
    def __radd__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> "Message":
        return super(Message, self).__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @staticmethod
    @overrides(BaseMessage)
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(msg)
