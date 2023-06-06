from typing import Type, Union, Iterable, Optional

from nonebot.typing import overrides
from nonebot.utils import escape_tag

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment

from .api import (
    Link,
    MentionedAll,
    MentionedUser,
    VillaRoomLink,
    MentionedRobot,
    MessageContentInfo,
)


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
    def mention_robot() -> "MentionRobotSegement":
        """@机器人消息段，目前暂时只能@自己"""
        # 好像目前并没有办法能艾特到其他机器人，因为没有办法获取到其他机器人的名称
        return MentionRobotSegement("mentioned_robot")

    # @staticmethod
    # def mention_robot(bot_id: str) -> "MentionRobotSegement":
    #     return MentionRobotSegement("mentioned_robot", {"bot_id": bot_id})

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
    def mention_all() -> "MentionAllSegement":
        """@全体成员消息段"""
        return MentionAllSegement("mention_all", {})

    @staticmethod
    def villa_room_link(villa_id: int, room_id: int) -> "VillaRoomLinkSegment":
        """房间链接消息段，点击后可以跳转到指定房间

        参数:
            villa_id: 大别野ID
            room_id: 房间ID

        返回:
            VillaRoomLinkSegment: 消息段对象
        """
        return VillaRoomLinkSegment(
            "villa_room_link", {"villa_id": villa_id, "room_id": room_id}
        )

    @staticmethod
    def link(url: str, text: Optional[str] = None) -> "LinkSegment":
        """链接消息段，使用该消息段才能让链接可以直接点击进行跳转

        参数:
            url: 链接

        返回:
            LinkSegment: 消息段对象
        """
        return LinkSegment("link", {"url": url, "text": text})

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


class TextSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return escape_tag(self.data["text"])


class MentionRobotSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return "@Bot"


class MentionUserSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"@{self.data['user_id']}"


class MentionAllSegement(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return "@全体成员"


class VillaRoomLinkSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"#{self.data['room_id']}-{self.data['villa_id']}]"  # TODO: 更好的展示方式


class LinkSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return self.data["url"]


class ImageSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f"<Image:{self.data['url']}>"


class QuoteSegment(MessageSegment):
    @overrides(MessageSegment)
    def __str__(self) -> str:
        return f">{self.data['msg_id']}"  # TODO: 更好的展示方式


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
        # TODO: 找到msg中的http或者https链接，将其转换为LinkSegment
        # text_begin = 0
        # for embed in re.finditer(r"https?://[^\s]+", msg):
        #     if embed.start() > text_begin:
        #         yield MessageSegment.text(msg[text_begin : embed.start()])
        #     yield MessageSegment.link(embed.group())
        #     text_begin = embed.end()

    @classmethod
    def parse(cls, content: MessageContentInfo, villa_id: int) -> "Message":
        """将大别野消息事件原始内容转为适配器使用的Message对象

        参数:
            content: 大别野消息事件原始内容

        返回:
            Message: 适配器Message对象
        """
        msg = Message()
        text = content.content.text
        text_begin = 0
        for entity in content.content.entities:
            if isinstance(entity.entity, MentionedRobot):
                msg.append(MessageSegment.mention_robot())
            elif isinstance(entity.entity, MentionedUser):
                msg.append(
                    MessageSegment.mention_user(int(entity.entity.user_id), villa_id)
                )
            elif isinstance(entity.entity, MentionedAll):
                msg.append(MessageSegment.mention_all())
            elif isinstance(entity.entity, VillaRoomLink):
                msg.append(
                    MessageSegment.villa_room_link(
                        int(entity.entity.villa_id),
                        int(entity.entity.room_id),
                    )
                )
            elif isinstance(entity.entity, Link):
                msg.append(MessageSegment.link(entity.entity.url))
            if text_sengment := text[text_begin : entity.offset]:
                msg.append(MessageSegment.text(text_sengment))
            text = text[(entity.offset + entity.length) :]
        if text:
            msg.append(MessageSegment.text(text))
        return msg
