import base64
import hashlib
import hmac
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from typing_extensions import override
from urllib.parse import urlencode

from nonebot.adapters import Bot as BaseBot
from nonebot.message import handle_event

import rsa

from .api import (
    ApiClient,
    Badge,
    Command,
    Image,
    ImageMessageContent,
    Link,
    MentionedAll,
    MentionedInfo,
    MentionedRobot,
    MentionedUser,
    MentionType,
    MessageContentInfo,
    PostMessageContent,
    PreviewLink,
    QuoteInfo,
    Robot,
    TextEntity,
    TextMessageContent,
    VillaRoomLink,
)
from .config import BotInfo
from .event import AddQuickEmoticonEvent, Event, SendMessageEvent
from .message import Message, MessageSegment
from .utils import log

if TYPE_CHECKING:
    from .adapter import Adapter


def _check_reply(bot: "Bot", event: SendMessageEvent):
    """检查事件是否有引用消息，如果有则删除。

    参数:
        bot: Bot对象
        event: 事件
    """
    if event.content.quote is not None:
        event.message = event.message.exclude("quote")
    if not event.message:
        event.message.append(MessageSegment.text(""))


def _check_at_me(bot: "Bot", event: SendMessageEvent):
    """检查事件是否和机器人有关，如果有关则设置 to_me 为 True，并删除消息中的 at 信息。

    参数:
        bot: Bot对象
        event: 事件

    """
    # 目前只能收到艾特机器人的消息，所以永远为 True
    # if (
    #     event.content.mentioned_info
    #     and bot.self_id in event.content.mentioned_info.user_id_list
    # ):
    #     event.to_me = True

    def _is_at_me_seg(segment: MessageSegment) -> bool:
        return (
            segment.type == "mention_robot"
            and segment.data["mention_robot"].bot_id == bot.self_id
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

    @override
    def __init__(
        self,
        adapter: "Adapter",
        self_id: str,
        bot_info: BotInfo,
        **kwargs: Any,
    ) -> None:
        super().__init__(adapter, self_id)
        self.adapter: Adapter = adapter
        self.bot_secret: str = bot_info.bot_secret
        self.bot_secret_encrypt = hmac.new(
            bot_info.pub_key.encode(),
            bot_info.bot_secret.encode(),
            hashlib.sha256,
        ).hexdigest()
        self.pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(bot_info.pub_key.encode())
        self.verify_event = bot_info.verify_event
        self._bot_info: Optional[Robot] = None

    @override
    def __repr__(self) -> str:
        return f"Bot(type={self.type!r}, self_id={self.self_id!r})"

    @property
    def nickname(self) -> str:
        """Bot 昵称"""
        if not self._bot_info:
            raise ValueError(f"Bot {self.self_id} hasn't received any events yet.")
        return self._bot_info.template.name

    @property
    def commands(self) -> Optional[List[Command]]:
        """Bot 命令预设命令列表"""
        if not self._bot_info:
            raise ValueError(f"Bot {self.self_id} hasn't received any events yet.")
        return self._bot_info.template.commands

    @property
    def description(self) -> str:
        """Bot 介绍描述"""
        if not self._bot_info:
            raise ValueError(f"Bot {self.self_id} hasn't received any events yet.")
        return self._bot_info.template.desc

    @property
    def avatar_icon(self) -> str:
        """Bot 头像图标地址"""
        if not self._bot_info:
            raise ValueError(f"Bot {self.self_id} hasn't received any events yet.")
        return self._bot_info.template.icon

    @property
    def current_villd_id(self) -> int:
        if not self._bot_info:
            raise ValueError(f"Bot {self.self_id} hasn't received any events yet.")
        return self._bot_info.villa_id

    async def handle_event(self, event: Event):
        """处理事件"""
        if isinstance(event, SendMessageEvent):
            _check_at_me(self, event)
            _check_reply(self, event)
        await handle_event(self, event)

    def _verify_signature(
        self,
        body: str,
        bot_sign: str,
    ):
        sign = base64.b64decode(bot_sign)
        sign_data = urlencode(
            {"body": body.rstrip("\n"), "secret": self.bot_secret},
        ).encode()
        try:
            rsa.verify(sign_data, sign, self.pub_key)
        except rsa.VerificationError:
            return False
        return True

    def get_authorization_header(
        self,
        villa_id: Optional[int] = None,
    ) -> Dict[str, str]:
        """Bot 鉴权凭证请求头

        参数:
            villa_id: 大别野ID

        返回:
            Dict[str, str]: 请求头
        """
        return {
            "x-rpc-bot_id": self.self_id,
            "x-rpc-bot_secret": self.bot_secret_encrypt,
            "x-rpc-bot_villa_id": str(villa_id or ""),
        }

    @override
    async def send(
        self,
        event: Event,
        message: Union[str, Message, MessageSegment],
        **kwargs: Any,
    ) -> str:
        """发送消息

        参数:
            event: 事件
            message: 消息
            mention_sender: 是否@消息发送者. 默认为 False.
            quote_message: 是否引用原消息. 默认为 False.

        异常:
            RuntimeError: 事件不是消息事件时抛出

        返回:
            str: 消息ID
        """
        if not isinstance(event, (SendMessageEvent, AddQuickEmoticonEvent)):
            raise RuntimeError("Event cannot be replied to!")
        message = MessageSegment.text(message) if isinstance(message, str) else message
        message = message if isinstance(message, Message) else Message(message)
        if kwargs.pop("mention_sender", False) or kwargs.pop("at_sender", False):
            message.insert(
                0,
                MessageSegment.mention_user(
                    user_id=int(event.get_user_id()),
                    user_name=(
                        event.content.user.name
                        if isinstance(event, SendMessageEvent)
                        else None
                    ),
                    villa_id=event.villa_id,
                ),
            )
        if kwargs.pop("quote_message", False) or kwargs.pop("reply_message", False):
            message += MessageSegment.quote(event.msg_uid, event.send_at)
        content_info = await self.parse_message_content(message)
        if isinstance(content_info.content, PostMessageContent):
            object_name = "MHY:Post"
        elif isinstance(content_info.content, ImageMessageContent):
            object_name = "MHY:Image"
        else:
            object_name = "MHY:Text"
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
        if quote_seg := message["quote"]:
            quote: Optional[QuoteInfo] = quote_seg[-1].data["quote"]
        else:
            quote = None
        if images_seg := message["image"]:
            images: Optional[List[Image]] = [
                image.data["image"] for image in images_seg
            ]
        else:
            images = None
        if post_seg := message["post"]:
            post: Optional[PostMessageContent] = post_seg[-1].data["post"]
        else:
            post = None
        if badge_seg := message["badge"]:
            badge: Optional[Badge] = badge_seg[-1].data["badge"]
        else:
            badge = None
        if preview_link_seg := message["preview_link"]:
            preview_link: Optional[PreviewLink] = preview_link_seg[-1].data[
                "preview_link"
            ]
        else:
            preview_link = None

        def cal_len(x):
            return len(x.encode("utf-16")) // 2 - 1

        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:
            try:
                if seg.type in ("quote", "image", "post", "badge", "preview_link"):
                    continue
                if seg.type == "text":
                    seg_text = seg.data["text"]
                    length = cal_len(seg_text)
                elif seg.type == "mention_all":
                    mention_all: MentionedAll = seg.data["mention_all"]
                    seg_text = f"@{mention_all.show_text} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=mention_all,
                        ),
                    )
                    mentioned.type = MentionType.ALL
                elif seg.type == "mention_robot":
                    mention_robot: MentionedRobot = seg.data["mention_robot"]
                    seg_text = f"@{mention_robot.bot_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=mention_robot,
                        ),
                    )
                    mentioned.user_id_list.append(mention_robot.bot_id)
                elif seg.type == "mention_user":
                    mention_user: MentionedUser = seg.data["mention_user"]
                    if mention_user.user_name is None:
                        # 需要调用API获取被@的用户的昵称
                        user = await self.get_member(
                            villa_id=seg.data["villa_id"],
                            uid=int(mention_user.user_id),
                        )
                        seg_text = f"@{user.basic.nickname} "
                        mention_user.user_name = user.basic.nickname
                    else:
                        seg_text = f"@{mention_user.user_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=mention_user,
                        ),
                    )
                    mentioned.user_id_list.append(str(mention_user.user_id))
                elif seg.type == "room_link":
                    room_link: VillaRoomLink = seg.data["room_link"]
                    if room_link.room_name is None:
                        # 需要调用API获取房间的名称
                        room = await self.get_room(
                            villa_id=int(room_link.villa_id),
                            room_id=int(room_link.room_id),
                        )
                        seg_text = f"#{room.room_name} "
                        room_link.room_name = room.room_name
                    else:
                        seg_text = f"#{room_link.room_name} "
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(
                            offset=message_offset,
                            length=length,
                            entity=room_link,
                        ),
                    )
                else:
                    link: Link = seg.data["link"]
                    seg_text = link.show_text
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(offset=message_offset, length=length, entity=link),
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
                    content = TextMessageContent(
                        text="\u200b",
                        images=images,
                        preview_link=preview_link,
                        badge=badge,
                    )
                else:
                    content = ImageMessageContent(**images[-1].dict())
            elif preview_link:
                content = TextMessageContent(
                    text="\u200b",
                    preview_link=preview_link,
                    badge=badge,
                )
            elif post:
                content = post
            else:
                raise ValueError("message content is empty")
        else:
            content = TextMessageContent(
                text=message_text,
                entities=entities,
                images=images,
                preview_link=preview_link,
                badge=badge,
            )

        return MessageContentInfo(content=content, mentionedInfo=mentioned, quote=quote)
