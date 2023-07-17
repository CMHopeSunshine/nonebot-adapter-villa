from typing import Iterable, Optional, Type, Union
from typing_extensions import override

from nonebot.adapters import (
    Message as BaseMessage,
    MessageSegment as BaseMessageSegment,
)
from nonebot.utils import escape_tag

from .api.models import *


class MessageSegment(BaseMessageSegment["Message"]):
    @classmethod
    @override
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @override
    def __repr__(self) -> str:
        return self.__str__()

    @override
    def __add__(
        self,
        other: Union[str, "MessageSegment", Iterable["MessageSegment"]],
    ) -> "Message":
        return super().__add__(other)

    @override
    def __radd__(
        self,
        other: Union[str, "MessageSegment", Iterable["MessageSegment"]],
    ) -> "Message":
        return super().__radd__(other)

    @override
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
            "mention_robot",
            {"mention_robot": MentionedRobot(bot_id=bot_id, bot_name=bot_name)},
        )

    @staticmethod
    def mention_user(
        user_id: int,
        user_name: Optional[str] = None,
        villa_id: Optional[int] = None,
    ) -> "MentionUserSegement":
        """@用户消息段

        user_name和villa_id必须有其中之一

        参数:
            user_id: 用户ID
            user_name: 用户名称
            villa_id: 用户所在大别野ID

        返回:
            MentionUserSegement: 消息段对象
        """
        if not (user_name or villa_id):
            raise ValueError("user_name and villa_id must have one of them")
        return MentionUserSegement(
            "mention_user",
            {
                "mention_user": MentionedUser(
                    user_id=str(user_id),
                    user_name=user_name,
                ),
                "villa_id": villa_id,
            },
        )

    @staticmethod
    def mention_all(show_text: str = "全体成员") -> "MentionAllSegement":
        """@全体成员消息段

        参数:
            show_text: 展示文本. 默认为 "全体成员".

        返回:
            MentionAllSegement: 消息段对象
        """
        return MentionAllSegement(
            "mention_all",
            {"mention_all": MentionedAll(show_text=show_text)},
        )

    @staticmethod
    def room_link(
        villa_id: int,
        room_id: int,
        room_name: Optional[str] = None,
    ) -> "RoomLinkSegment":
        """房间链接消息段，点击后可以跳转到指定房间

        参数:
            villa_id: 大别野ID
            room_id: 房间ID

        返回:
            VillaRoomLinkSegment: 消息段对象
        """
        return RoomLinkSegment(
            "room_link",
            {
                "room_link": VillaRoomLink(
                    villa_id=str(villa_id),
                    room_id=str(room_id),
                    room_name=room_name,
                ),
            },
        )

    @staticmethod
    def link(
        url: str,
        show_text: Optional[str] = None,
        requires_bot_access_token: bool = False,
    ) -> "LinkSegment":
        """链接消息段，使用该消息段才能让链接可以直接点击进行跳转

        参数:
            url: 链接
            show_text: 链接显示的文本

        返回:
            LinkSegment: 消息段对象
        """
        return LinkSegment(
            "link",
            {
                "link": Link(
                    url=url,
                    show_text=show_text or url,
                    requires_bot_access_token=requires_bot_access_token,
                ),
            },
        )

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
            "quote",
            {
                "quote": QuoteInfo(
                    quoted_message_id=message_id,
                    quoted_message_send_time=message_send_time,
                    original_message_id=message_id,
                    original_message_send_time=message_send_time,
                ),
            },
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
            {
                "image": Image(
                    url=url,
                    size=(
                        ImageSize(width=width, height=height)
                        if width and height
                        else None
                    ),
                    file_size=file_size,
                ),
            },
        )

    @staticmethod
    def post(post_id: str) -> "PostSegment":
        """帖子转发消息段

        参数:
            post_id: 帖子ID

        返回:
            PostSegment: 消息段对象
        """
        return PostSegment("post", {"post": PostMessageContent(post_id=post_id)})

    @staticmethod
    def preview_link(
        icon_url: str,
        image_url: str,
        is_internal_link: bool,
        title: str,
        content: str,
        url: str,
        source_name: str,
    ) -> "PreviewLinkSegment":
        """预览链接(卡片)消息段

        参数:
            icon_url: 图标链接
            image_url: 封面链接
            is_internal_link: 是否为官方
            title: 标题
            content: 内容
            url: 链接
            source_name: 来源

        返回:
            PreviewLinkSegment: 消息段对象
        """
        return PreviewLinkSegment(
            "preview_link",
            {
                "preview_link": PreviewLink(
                    icon_url=icon_url,
                    image_url=image_url,
                    is_internal_link=is_internal_link,
                    title=title,
                    content=content,
                    url=url,
                    source_name=source_name,
                ),
            },
        )

    @staticmethod
    def badge(
        icon_url: str,
        text: str,
        url: str,
    ) -> "BadgeSegment":
        """消息下方徽标

        参数:
            icon_url: 图标链接
            text: 文本
            url: 链接

        返回:
            BadgeSegment: 消息段对象
        """
        return BadgeSegment(
            "badge",
            {
                "badge": Badge(
                    icon_url=icon_url,
                    text=text,
                    url=url,
                ),
            },
        )


class TextSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return escape_tag(self.data["text"])


class MentionRobotSegement(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["mention_robot"])


class MentionUserSegement(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["mention_user"])


class MentionAllSegement(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["mention_all"])


class RoomLinkSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["room_link"])


class LinkSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["link"])


class ImageSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["image"])


class QuoteSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["quote"])


class PostSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["post"])


class PreviewLinkSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["preview_link"])


class BadgeSegment(MessageSegment):
    @override
    def __str__(self) -> str:
        return repr(self.data["badge"])


class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    @override
    def __add__(
        self,
        other: Union[str, MessageSegment, Iterable[MessageSegment]],
    ) -> "Message":
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other,
        )

    @override
    def __radd__(
        self,
        other: Union[str, MessageSegment, Iterable[MessageSegment]],
    ) -> "Message":
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other,
        )

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment.text(msg)
