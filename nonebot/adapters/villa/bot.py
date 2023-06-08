from typing import TYPE_CHECKING, Any, Dict, List, Union, Optional

from nonebot.typing import overrides
from nonebot.message import handle_event
from nonebot.internal.adapter.adapter import Adapter

from nonebot.adapters import Bot as BaseBot

from .event import Event, SendMessageEvent
from .message import Message, MessageSegment
from .api import (
    Link,
    Image,
    Robot,
    ApiClient,
    ImageSize,
    QuoteInfo,
    TextEntity,
    MentionType,
    MentionedAll,
    RobotCommand,
    MentionedInfo,
    MentionedUser,
    VillaRoomLink,
    MentionedRobot,
    MessageContent,
    MessageContentInfo,
)

if TYPE_CHECKING:
    from .adapter import Adapter


async def _check_reply(bot: "Bot", event: SendMessageEvent):
    """检查事件是否有引用消息，如果有则设置 reply 字段。

    但是目前并没有API能获取被引用的消息的内容，所以现在不做。

    参数:
        bot: Bot对象
        event: 事件
    """
    ...


def _check_at_me(bot: "Bot", event: SendMessageEvent):
    """检查事件是否和机器人有关，如果有关则设置 to_me 为 True，并删除消息中的 at 信息。

    参数:
        bot: Bot对象
        event: 事件

    """
    if (
        event.content.mentioned_info
        and bot.self_id in event.content.mentioned_info.user_id_list
    ):
        event.to_me = True

    def _is_at_me_seg(segment: MessageSegment) -> bool:
        return (
            segment.type == "mentioned_robot"
            and segment.data.get("bot_id") == bot.self_id
        )

    message = event.get_message()
    if not message:
        message.append(MessageSegment.text(""))

    deleted = False
    if _is_at_me_seg(message[0]):
        message.pop(0)
        deleted = True
        if message and message[0].type == "text":
            message[0].data["text"] = message[0].data["text"].lstrip("\xa0").lstrip()
            if not message[0].data["text"]:
                del message[0]

    if not deleted:
        # check the last segment
        i = -1
        last_msg_seg = message[i]
        if (
            last_msg_seg.type == "text"
            and not last_msg_seg.data["text"].strip()
            and len(message) >= 2
        ):
            i -= 1
            last_msg_seg = message[i]

        if _is_at_me_seg(last_msg_seg):
            deleted = True
            del message[i:]

    if not message:
        message.append(MessageSegment.text(""))


class Bot(BaseBot, ApiClient):
    """
    大别野协议 Bot 适配。
    """

    @overrides(BaseBot)
    def __init__(
        self, adapter: Adapter, self_id: str, bot_info: Robot, bot_secret: str
    ):
        super().__init__(adapter, self_id)
        self.adapter: Adapter = adapter
        self.bot_secret: str = bot_secret
        self._bot_info: Robot = bot_info

    @overrides(BaseBot)
    def __repr__(self) -> str:
        return f"Bot(type={self.type!r}, self_id={self.self_id!r})"

    @property
    def nickname(self) -> str:
        """Bot 昵称"""
        return self._bot_info.template.name

    @property
    def commands(self) -> Optional[List[RobotCommand]]:
        """Bot 命令预设命令列表"""
        return self._bot_info.template.commands

    @property
    def description(self) -> str:
        """Bot 介绍描述"""
        return self._bot_info.template.desc

    @property
    def avatar_icon(self) -> str:
        """Bot 头像图标地址"""
        return self._bot_info.template.icon

    @property
    def current_villd_id(self) -> int:
        return self._bot_info.villa_id

    async def handle_event(self, event: Event):
        """处理事件"""
        if isinstance(event, SendMessageEvent):
            _check_at_me(self, event)
            # await _check_reply(self, event)
        await handle_event(self, event)

    def get_authorization_header(
        self, villa_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Bot 鉴权凭证请求头

        参数:
            villa_id: 大别野ID

        返回:
            Dict[str, str]: 请求头
        """
        return {
            "x-rpc-bot_id": self.self_id,
            "x-rpc-bot_secret": self.bot_secret,
            "x-rpc-bot_villa_id": str(villa_id or ""),
        }

    @overrides(BaseBot)
    async def send(
        self,
        event: Event,
        message: Union[str, Message, MessageSegment],
        mention_sender: bool = False,
        reply_message: bool = False,
        **kwargs: Any,
    ) -> str:
        """发送消息

        参数:
            event: 事件
            message: 消息
            mention_sender: 是否@消息发送者. 默认为 False.
            reply_message: 是否引用原消息. 默认为 False.

        异常:
            RuntimeError: 事件不是消息事件时抛出

        返回:
            str: 消息ID
        """
        if not isinstance(event, SendMessageEvent):
            raise RuntimeError("Event cannot be replied to!")
        message = MessageSegment.text(message) if isinstance(message, str) else message
        message = message if isinstance(message, Message) else Message(message)
        if mention_sender:
            message.insert(
                0, MessageSegment.mention_user(event.villa_id, event.from_user_id)
            )
        if reply_message:
            message += MessageSegment.quote(event.msg_uid, event.send_at)
        content_info = await self.parse_message_content(message)
        return await self.send_message(
            villa_id=event.villa_id,
            room_id=event.room_id,
            object_name="MHY:Text",
            # object_name="MHY:Image" if content_info.content.images else "MHY:Text",
            msg_content=content_info.json(by_alias=True, exclude_none=True),
        )

    async def parse_message_content(self, message: Message) -> MessageContentInfo:
        """将适配器的Message对象转为大别野发送所需要的MessageContentInfo对象

        参数:
            message: 消息

        返回:
            MessageContentInfo: 消息内容对象
        """
        if quote := (message["quote"] or None):
            quote = quote[-1]
            quote = QuoteInfo(
                quoted_message_id=quote.data["msg_id"],
                quoted_message_send_time=quote.data["msg_send_time"],
                original_message_id=quote.data["msg_id"],
                original_message_send_time=quote.data["msg_send_time"],
            )

        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        images: List[Image] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:
            if seg.type == "text":
                message_text += seg.data["text"]
                message_offset += len(seg.data["text"])
            elif seg.type == "mention_all":
                message_text += f"@{seg.data['show_text']} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=6,
                        entity=MentionedAll(show_text=seg.data["show_text"]),
                    )
                )
                message_offset += 6
                mentioned.type = MentionType.ALL
            elif seg.type == "mentioned_robot":
                message_text += f"@{seg.data['bot_name']} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(f"@{seg.data['bot_name']}".encode("utf-16")) // 2,
                        entity=MentionedRobot(
                            bot_id=seg.data["bot_id"], bot_name=seg.data["bot_name"]
                        ),
                    )
                )
                message_offset += len(f"@{seg.data['bot_name']}") + 1
                mentioned.user_id_list.append(seg.data["bot_id"])
            elif seg.type == "mentioned_user":
                # 需要调用API获取被@的用户的昵称
                user = await self.get_member(
                    villa_id=seg.data["villa_id"], uid=seg.data["user_id"]
                )
                message_text += f"@{user.basic.nickname} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(f"@{user.basic.nickname}".encode("utf-16")) // 2,
                        entity=MentionedUser(
                            user_id=str(user.basic.uid), user_name=user.basic.nickname
                        ),
                    )
                )
                message_offset += len(f"@{user.basic.nickname}") + 1
                mentioned.user_id_list.append(str(user.basic.uid))
            elif seg.type == "villa_room_link":
                # 需要调用API获取房间的名称
                room = await self.get_room(
                    villa_id=seg.data["villa_id"], room_id=seg.data["room_id"]
                )
                message_text += f"#{room.room_name} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(f"#{room.room_name}".encode("utf-16")) // 2,
                        entity=VillaRoomLink(
                            villa_id=str(seg.data["villa_id"]),
                            room_id=str(seg.data["room_id"]),
                            room_name=room.room_name,
                        ),
                    )
                )
                message_offset += len(f"#{room.room_name} ")
            elif seg.type == "link":
                message_text += seg.data["show_text"]
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(seg.data["show_text"].encode("utf-16")) // 2,
                        entity=Link(
                            url=seg.data["url"], show_text=seg.data["show_text"]
                        ),
                    )
                )
                message_offset += len(seg.data["show_text"]) + 1
            elif seg.type == "image":
                images.append(
                    Image(
                        url=seg.data["url"],
                        size=ImageSize(
                            width=seg.data["width"], height=seg.data["height"]
                        )
                        if seg.data["width"] and seg.data["height"]
                        else None,
                        file_size=seg.data["file_size"],
                    )
                )

        # 不能单独只发图片而没有其他文本内容，塞一个零宽度空格
        if images and not message_text:
            message_text = "\u200B"

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None
        return MessageContentInfo(
            content=MessageContent(text=message_text, entities=entities, images=images),
            mentionedInfo=mentioned,
            quote=quote,  # type: ignore
        )
