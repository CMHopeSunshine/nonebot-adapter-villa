from typing import TYPE_CHECKING, Any, Dict, Union

from nonebot.typing import overrides
from nonebot.message import handle_event
from nonebot.internal.adapter.adapter import Adapter

from nonebot.adapters import Bot as BaseBot

from .event import Event, SendMessageEvent
from .message import Message, MessageSegment
from .api import (
    Link,
    Robot,
    ApiClient,
    QuoteInfo,
    TextEntity,
    MentionType,
    MentionedAll,
    MentionedInfo,
    MentionedUser,
    VillaRoomLink,
    MentionedRobot,
    MessageContent,
    MessageContentInfo,
)

if TYPE_CHECKING:
    from .adapter import Adapter


# def  _check_reply(bot: "Bot", event: SendMessageEvent):
#     if event.content.quote


def _check_at_me(bot: "Bot", event: SendMessageEvent):
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
    Villa 协议 Bot 适配。
    """

    @overrides(BaseBot)
    def __init__(
        self, adapter: Adapter, self_id: str, bot_info: Robot, bot_secret: str
    ):
        super().__init__(adapter, self_id)
        self.adapter: Adapter = adapter
        self.bot_info: Robot = bot_info
        self.bot_secret: str = bot_secret

    @overrides(BaseBot)
    def __repr__(self) -> str:
        return f"Bot(type={self.type!r}, self_id={self.self_id!r})"

    async def handle_event(self, event: Event):
        if isinstance(event, SendMessageEvent):
            _check_at_me(self, event)
        await handle_event(self, event)

    def get_authorization_header(self, villa_id: int) -> Dict[str, Any]:
        return {
            "x-rpc-bot_id": self.self_id,
            "x-rpc-bot_secret": self.bot_secret,
            "x-rpc-bot_villa_id": str(villa_id),
            # "Content-Type": "application/json"
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
        if not isinstance(event, SendMessageEvent):
            raise ValueError("Villa adapter can only send message in MessageEvent")
        message = MessageSegment.text(message) if isinstance(message, str) else message
        message = message if isinstance(message, Message) else Message(message)
        if mention_sender:
            message.insert(0, MessageSegment.mention_user(event.from_user_id))
        if reply_message:
            message += MessageSegment.quote(event.msg_uid, event.send_at)
        content_info = await self.parse_message_content(message)
        return await self.send_message(
            villa_id=self.bot_info.villa_id,
            room_id=event.room_id,
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
        entities = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:
            if seg.type == "quote":
                continue
            elif seg.type == "text":
                message_text += seg.data["text"]
                message_offset += len(seg.data["text"])
            elif seg.type == "mention_all":
                message_text += "@全体成员 "
                entities.append(
                    TextEntity(offset=message_offset, length=6, entity=MentionedAll())
                )
                message_offset += 6
                mentioned.type = MentionType.ALL
            elif seg.type == "mentioned_robot":
                message_text += f"@{self.bot_info.template.name} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(f"@{self.bot_info.template.name}".encode("utf-16"))
                        // 2,
                        entity=MentionedRobot(bot_id=self.self_id),
                    )
                )
                message_offset += len(f"@{self.bot_info.template.name}") + 1
                mentioned.user_id_list.append(self.self_id)
            elif seg.type == "mentioned_user":
                user = await self.get_member(
                    villa_id=self.bot_info.villa_id, uid=seg.data["user_id"]
                )
                message_text += f"@{user.basic.nickname} "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(f"@{user.basic.nickname}".encode("utf-16")) // 2,
                        entity=MentionedUser(user_id=str(user.basic.uid)),
                    )
                )
                message_offset += len(f"@{user.basic.nickname}") + 1
                mentioned.user_id_list.append(str(user.basic.uid))
            elif seg.type == "villa_room_link":
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
                        ),
                    )
                )
                message_offset += len(f"#{room.room_name} ")
            elif seg.type == "link":
                message_text += seg.data["url"] + " "
                entities.append(
                    TextEntity(
                        offset=message_offset,
                        length=len(seg.data["url"].encode("utf-16")) // 2,
                        entity=Link(url=seg.data["url"]),
                    )
                )
                message_offset += len(seg.data["url"]) + 1

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None
        return MessageContentInfo(
            content=MessageContent(text=message_text, entities=entities),
            mentionedInfo=mentioned,
            quote=quote,  # type: ignore
        )
        # from pathlib import Path
        # (Path().cwd() / 'send_msg.json').write_text(a.json(by_alias=True, exclude_none=True))
        # return a
