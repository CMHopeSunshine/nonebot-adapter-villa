from typing import TYPE_CHECKING, Any, Dict, List, Union, Optional

from nonebot.typing import overrides
from nonebot.message import handle_event
from nonebot.internal.adapter.adapter import Adapter

from nonebot.adapters import Bot as BaseBot

from .utils import log
from .event import Event, SendMessageEvent
from .message import Message, MessageSegment
from .api import (
    Link,
    Image,
    Robot,
    Command,
    ApiClient,
    ImageSize,
    QuoteInfo,
    TextEntity,
    MentionType,
    MentionedAll,
    MentionedInfo,
    MentionedUser,
    VillaRoomLink,
    MentionedRobot,
    MessageContentInfo,
    PostMessageContent,
    TextMessageContent,
    ImageMessageContent,
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
    def commands(self) -> Optional[List[Command]]:
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
        if isinstance(content_info.content, TextMessageContent):
            object_name = "MHY:Text"
        elif isinstance(content_info.content, ImageMessageContent):
            object_name = "MHY:Image"
        else:
            object_name = "MHY:Post"
        return await self.send_message(
            villa_id=event.villa_id,
            room_id=event.room_id,
            object_name=object_name,
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
        if images_msg := (message["image"] or None):
            images = [
                Image(
                    url=seg.data["url"],
                    size=ImageSize(width=seg.data["width"], height=seg.data["height"])
                    if seg.data["width"] and seg.data["height"]
                    else None,
                    file_size=seg.data["file_size"],
                )
                for seg in images_msg
            ]
        else:
            images = None
        if posts_msg := (message["post"] or None):
            post_ids: Optional[List[str]] = [seg.data["post_id"] for seg in posts_msg]
        else:
            post_ids = None
        cal_len = lambda x: len(x.encode("utf-16")) // 2 - 1
        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:
            try:
                if seg.type in ("quote", "image", "post"):
                    continue
                if seg.type == "text":
                    seg_text = seg.data["text"]
                    length = cal_len(seg_text)
                elif seg.type == "mention_all":
                    seg_text = f"@{seg.data['show_text']} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedAll(show_text=seg.data["show_text"]),
                        )
                    )
                    mentioned.type = MentionType.ALL
                elif seg.type == "mentioned_robot":
                    seg_text = f"@{seg.data['bot_name']} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedRobot(
                                bot_id=seg.data["bot_id"], bot_name=seg.data["bot_name"]
                            ),
                        )
                    )
                    mentioned.user_id_list.append(seg.data["bot_id"])
                elif seg.type == "mentioned_user":
                    # 需要调用API获取被@的用户的昵称
                    user = await self.get_member(
                        villa_id=seg.data["villa_id"], uid=seg.data["user_id"]
                    )
                    seg_text = f"@{user.basic.nickname} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=MentionedUser(
                                user_id=str(user.basic.uid),
                                user_name=user.basic.nickname,
                            ),
                        )
                    )
                    mentioned.user_id_list.append(str(user.basic.uid))
                elif seg.type == "villa_room_link":
                    # 需要调用API获取房间的名称
                    room = await self.get_room(
                        villa_id=seg.data["villa_id"], room_id=seg.data["room_id"]
                    )
                    seg_text = f"#{room.room_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=VillaRoomLink(
                                villa_id=str(seg.data["villa_id"]),
                                room_id=str(seg.data["room_id"]),
                                room_name=room.room_name,
                            ),
                        )
                    )
                else:
                    seg_text = seg.data["show_text"]
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=Link(
                                url=seg.data["url"], show_text=seg.data["show_text"]
                            ),
                        )
                    )
                message_offset += length
                message_text += seg_text
            except Exception as e:
                log("WARNING", "error when parse message content", e)

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None

        if not (message_text or entities):
            if images:
                if len(images) > 1:
                    content = TextMessageContent(text="\u200B", images=images)
                else:
                    content = ImageMessageContent(**images[-1].dict())
            elif post_ids:
                content = PostMessageContent(post_id=post_ids[-1])
            else:
                raise ValueError("message content is empty")
        else:
            content = TextMessageContent(
                text=message_text, entities=entities, images=images
            )

        return MessageContentInfo(
            content=content,
            mentionedInfo=mentioned,
            quote=quote,  # type: ignore
        )
