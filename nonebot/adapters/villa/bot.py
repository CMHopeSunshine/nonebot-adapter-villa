import base64
import hashlib
import hmac
from io import BytesIO
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    NoReturn,
    Optional,
    Union,
    cast,
)
from typing_extensions import override
from urllib.parse import urlencode

from nonebot.adapters import Bot as BaseBot
from nonebot.drivers import Request, Response
from nonebot.message import handle_event
from nonebot.utils import escape_tag

from pydantic import parse_obj_as
import rsa

from .config import BotInfo
from .event import AddQuickEmoticonEvent, Event, SendMessageEvent
from .exception import (
    ActionFailed,
    BotNotAdded,
    InsufficientPermission,
    InvalidBotAuthInfo,
    InvalidMemberBotAccessToken,
    InvalidRequest,
    NetworkError,
    PermissionDenied,
    UnknownServerError,
    UnsupportedMsgType,
)
from .message import (
    BadgeSegment,
    ComponentsSegment,
    ImageSegment,
    LinkSegment,
    MentionAllSegement,
    MentionRobotSegement,
    MentionUserSegement,
    Message,
    MessageSegment,
    PanelSegment,
    PostSegment,
    PreviewLinkSegment,
    QuoteSegment,
    RoomLinkSegment,
    TextSegment,
)
from .models import (
    ApiResponse,
    CheckMemberBotAccessTokenReturn,
    Color,
    Command,
    Component,
    ContentType,
    Emoticon,
    Group,
    GroupRoom,
    ImageMessageContent,
    ImageUploadResult,
    Link,
    Member,
    MemberListReturn,
    MemberRoleDetail,
    MentionedAll,
    MentionedInfo,
    MentionType,
    MessageContentInfo,
    Panel,
    Permission,
    PostMessageContent,
    Robot,
    Room,
    RoomSort,
    TextEntity,
    TextMessageContent,
    TextStyle,
    UploadImageParamsReturn,
    Villa,
    VillaRoomLink,
    WebsocketInfo,
)
from .utils import API, get_img_extenion, get_img_md5, log

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


class Bot(BaseBot):
    """
    大别野协议 Bot 适配。
    """

    adapter: "Adapter"

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
        self.test_villa_id = bot_info.test_villa_id
        self._bot_info: Optional[Robot] = None
        self._ws_info: Optional[WebsocketInfo] = None
        self._ws_squence: int = 0

    @override
    def __repr__(self) -> str:
        return f"Bot(type={self.type!r}, self_id={self.self_id!r})"

    @override
    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(
            f'"{self.__class__.__name__}" object has no attribute "{name}"',
        )

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
    def description(self) -> Optional[str]:
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

    @property
    def ws_info(self) -> WebsocketInfo:
        if self._ws_info is None:
            raise RuntimeError(f"Bot {self.self_id} is not connected!")
        return self._ws_info

    @ws_info.setter
    def ws_info(self, ws_info: WebsocketInfo):
        self._ws_info = ws_info

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
    ) -> bool:
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
            "x-rpc-bot_villa_id": str(
                villa_id if villa_id is not None else self.test_villa_id,
            ),
        }

    async def _handle_respnose(self, response: Response) -> Any:
        if not response.content:
            raise NetworkError("API request error when parsing response")
        resp = ApiResponse.parse_raw(response.content)
        if resp.retcode == 0:
            return resp.data
        if resp.retcode == -502:
            raise UnknownServerError(resp)
        if resp.retcode == -1:
            raise InvalidRequest(resp)
        if resp.retcode == 10318001:
            raise InsufficientPermission(resp)
        if resp.retcode == 10322002:
            raise BotNotAdded(resp)
        if resp.retcode == 10322003:
            raise PermissionDenied(resp)
        if resp.retcode == 10322004:
            raise InvalidMemberBotAccessToken(resp)
        if resp.retcode == 10322005:
            raise InvalidBotAuthInfo(resp)
        if resp.retcode == 10322006:
            raise UnsupportedMsgType(resp)
        raise ActionFailed(response.status_code, resp)

    async def _request(self, request: Request):
        try:
            resp = await self.adapter.request(request)
            log(
                "TRACE",
                f"API status_code:{resp.status_code} content: {escape_tag(str(resp.content))}",  # noqa: E501
            )
        except Exception as e:
            raise NetworkError("API request failed") from e
        return await self._handle_respnose(resp)

    async def send_to(
        self,
        villa_id: int,
        room_id: int,
        message: Union[str, Message, MessageSegment],
    ) -> str:
        """向指定房间发送消息

        参数:
            villa_id: 大别野 ID
            room_id: 房间 ID
            message: 消息

        返回:
            str: 消息 ID
        """
        message = message if isinstance(message, Message) else Message(message)
        content_info = await self.parse_message_content(message)
        if isinstance(content_info.content, PostMessageContent):
            object_name = "MHY:Post"
        elif isinstance(content_info.content, ImageMessageContent):
            object_name = "MHY:Image"
        else:
            object_name = "MHY:Text"
        return await self.send_message(
            villa_id=villa_id,
            room_id=room_id,
            object_name=object_name,
            msg_content=content_info.json(
                by_alias=True,
                exclude_none=True,
                ensure_ascii=False,
            ),
        )

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
        return await self.send_to(
            villa_id=event.villa_id,
            room_id=event.room_id,
            message=message,
        )

    async def parse_message_content(self, message: Message) -> MessageContentInfo:
        """将适配器的Message对象转为大别野发送所需要的MessageContentInfo对象

        参数:
            message: 消息

        返回:
            MessageContentInfo: 消息内容对象
        """
        quote = image = post = badge = preview_link = panel = None
        if quote_seg := cast(Optional[List[QuoteSegment]], message["quote"] or None):
            quote = quote_seg[-1].data["quote"]
        if image_seg := cast(
            Optional[List[ImageSegment]],
            message["image"] or None,
        ):
            image = image_seg[-1].data["image"]
        if post_seg := cast(Optional[List[PostSegment]], message["post"] or None):
            post = post_seg[-1].data["post"]
        if badge_seg := cast(Optional[List[BadgeSegment]], message["badge"] or None):
            badge = badge_seg[-1].data["badge"]
        if preview_link_seg := cast(
            Optional[List[PreviewLinkSegment]],
            message["preview_link"] or None,
        ):
            preview_link = preview_link_seg[-1].data["preview_link"]
        if panel_seg := cast(Optional[List[PanelSegment]], message["panel"] or None):
            panel = panel_seg[-1].data["panel"]
        if panel is None:
            components: List[Component] = []
            for com in message["components"]:
                components.extend(cast(ComponentsSegment, com).data["components"])
            if components:
                panel = _parse_components(components)

        def cal_len(x):
            return len(x.encode("utf-16")) // 2 - 1

        message = message.exclude("quote", "image", "post", "badge", "preview_link")
        message_text = ""
        message_offset = 0
        entities: List[TextEntity] = []
        mentioned = MentionedInfo(type=MentionType.PART)
        for seg in message:
            try:
                if isinstance(seg, TextSegment):
                    seg_text = seg.data["text"]
                    length = cal_len(seg_text)
                    for style in {"bold", "italic", "underline", "strikethrough"}:
                        if seg.data[style]:
                            entities.append(
                                TextEntity(
                                    offset=message_offset,
                                    length=length,
                                    entity=TextStyle(font_style=style),  # type: ignore
                                ),
                            )
                elif isinstance(seg, MentionAllSegement):
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
                elif isinstance(seg, MentionRobotSegement):
                    mention_robot = seg.data["mention_robot"]
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
                elif isinstance(seg, MentionUserSegement):
                    mention_user = seg.data["mention_user"]
                    if mention_user.user_name is None:
                        if not seg.data["villa_id"]:
                            raise ValueError("cannot get user name without villa_id")
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
                elif isinstance(seg, RoomLinkSegment):
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
                elif isinstance(seg, LinkSegment):
                    link: Link = seg.data["link"]
                    seg_text = link.show_text
                    length = cal_len(seg_text)
                    entities.append(
                        TextEntity(offset=message_offset, length=length, entity=link),
                    )
                else:
                    continue
                message_offset += length
                message_text += seg_text
            except Exception as e:
                log("WARNING", "error when parse message content", e)

        if not (mentioned.type == MentionType.ALL and mentioned.user_id_list):
            mentioned = None

        if not (message_text or entities):
            if preview_link or badge:
                content = TextMessageContent(
                    text="\u200b",
                    preview_link=preview_link,
                    badge=badge,
                    images=[image] if image else None,
                )
            elif image:
                content = image
            elif post:
                content = post
            else:
                raise ValueError("message content is empty")
        else:
            content = TextMessageContent(
                text=message_text,
                entities=entities,
                images=[image] if image else None,
                preview_link=preview_link,
                badge=badge,
            )

        return MessageContentInfo(
            content=content,
            mentionedInfo=mentioned,
            quote=quote,
            panel=panel,
        )

    @API
    async def check_member_bot_access_token(
        self,
        *,
        villa_id: int,
        token: str,
    ) -> CheckMemberBotAccessTokenReturn:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "checkMemberBotAccessToken",
            headers=self.get_authorization_header(
                villa_id,
            ),
            json={"token": token},
        )
        return parse_obj_as(
            CheckMemberBotAccessTokenReturn,
            await self._request(request),
        )

    @API
    async def get_villa(self, villa_id: int) -> Villa:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getVilla",
            headers=self.get_authorization_header(villa_id),
        )
        return parse_obj_as(Villa, (await self._request(request))["villa"])

    @API
    async def get_member(
        self,
        *,
        villa_id: int,
        uid: int,
    ) -> Member:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getMember",
            headers=self.get_authorization_header(villa_id),
            params={"uid": uid},
        )
        return parse_obj_as(Member, (await self._request(request))["member"])

    @API
    async def get_villa_members(
        self,
        *,
        villa_id: int,
        offset: int,
        size: int,
    ) -> MemberListReturn:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getVillaMembers",
            headers=self.get_authorization_header(villa_id),
            params={"offset": offset, "size": size},
        )
        return parse_obj_as(MemberListReturn, await self._request(request))

    @API
    async def delete_villa_member(
        self,
        *,
        villa_id: int,
        uid: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "deleteVillaMember",
            headers=self.get_authorization_header(villa_id),
            json={"uid": uid},
        )
        await self._request(request)

    @API
    async def pin_message(
        self,
        *,
        villa_id: int,
        msg_uid: str,
        is_cancel: bool,
        room_id: int,
        send_at: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "pinMessage",
            headers=self.get_authorization_header(villa_id),
            json={
                "msg_uid": msg_uid,
                "is_cancel": is_cancel,
                "room_id": room_id,
                "send_at": send_at,
            },
        )
        await self._request(request)

    @API
    async def recall_message(
        self,
        *,
        villa_id: int,
        msg_uid: str,
        room_id: int,
        msg_time: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "recallMessage",
            headers=self.get_authorization_header(villa_id),
            json={"msg_uid": msg_uid, "room_id": room_id, "msg_time": msg_time},
        )
        await self._request(request)

    @API
    async def send_message(
        self,
        *,
        villa_id: int,
        room_id: int,
        object_name: str,
        msg_content: Union[str, MessageContentInfo],
    ) -> str:
        if isinstance(msg_content, MessageContentInfo):
            content = msg_content.json(
                by_alias=True,
                exclude_none=True,
                ensure_ascii=False,
            )
        else:
            content = msg_content
        request = Request(
            method="POST",
            url=self.adapter.base_url / "sendMessage",
            headers=self.get_authorization_header(villa_id),
            json={
                "room_id": room_id,
                "object_name": object_name,
                "msg_content": content,
            },
        )
        return (await self._request(request))["bot_msg_id"]

    @API
    async def create_component_template(
        self,
        *,
        panel: Panel,
    ) -> int:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "createComponentTemplate",
            headers=self.get_authorization_header(),
            json={
                "panel": panel.json(exclude_none=True, ensure_ascii=False),
            },
        )
        return (await self._request(request))["template_id"]

    @API
    async def create_group(
        self,
        *,
        villa_id: int,
        group_name: str,
    ) -> int:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "createGroup",
            headers=self.get_authorization_header(villa_id),
            json={"group_name": group_name},
        )
        return (await self._request(request))["group_id"]

    @API
    async def edit_group(
        self,
        *,
        villa_id: int,
        group_id: int,
        group_name: str,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "editGroup",
            headers=self.get_authorization_header(villa_id),
            json={"group_id": group_id, "group_name": group_name},
        )
        await self._request(request)

    @API
    async def delete_group(
        self,
        *,
        villa_id: int,
        group_id: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "deleteGroup",
            headers=self.get_authorization_header(villa_id),
            json={"group_id": group_id},
        )
        await self._request(request)

    @API
    async def get_group_list(self, *, villa_id: int) -> List[Group]:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getGroupList",
            headers=self.get_authorization_header(villa_id),
        )
        return parse_obj_as(List[Group], (await self._request(request))["list"])

    @API
    async def sort_group_list(
        self,
        *,
        villa_id: int,
        group_ids: List[int],
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "sortGroupList",
            headers=self.get_authorization_header(villa_id),
            json={"villa_id": villa_id, "group_ids": group_ids},
        )
        await self._request(request)

    @API
    async def edit_room(
        self,
        *,
        villa_id: int,
        room_id: int,
        room_name: str,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "editRoom",
            headers=self.get_authorization_header(villa_id),
            json={"room_id": room_id, "room_name": room_name},
        )
        await self._request(request)

    @API
    async def delete_room(
        self,
        *,
        villa_id: int,
        room_id: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "deleteRoom",
            headers=self.get_authorization_header(villa_id),
            json={"room_id": room_id},
        )
        await self._request(request)

    @API
    async def get_room(
        self,
        *,
        villa_id: int,
        room_id: int,
    ) -> Room:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getRoom",
            headers=self.get_authorization_header(villa_id),
            params={"room_id": room_id},
        )
        return parse_obj_as(Room, (await self._request(request))["room"])

    @API
    async def get_villa_group_room_list(
        self,
        *,
        villa_id: int,
    ) -> List[GroupRoom]:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getVillaGroupRoomList",
            headers=self.get_authorization_header(villa_id),
        )
        return parse_obj_as(
            List[GroupRoom],
            (await self._request(request))["list"],
        )

    @API
    async def sort_room_list(
        self,
        *,
        villa_id: int,
        room_list: List[RoomSort],
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "sortRoomList",
            headers=self.get_authorization_header(villa_id),
            json={
                "villa_id": villa_id,
                "room_list": [room.dict() for room in room_list],
            },
        )
        await self._request(request)

    @API
    async def operate_member_to_role(
        self,
        *,
        villa_id: int,
        role_id: int,
        uid: int,
        is_add: bool,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "operateMemberToRole",
            headers=self.get_authorization_header(villa_id),
            json={"role_id": role_id, "uid": uid, "is_add": is_add},
        )
        await self._request(request)

    @API
    async def create_member_role(
        self,
        *,
        villa_id: int,
        name: str,
        color: Color,
        permissions: List[Permission],
    ) -> int:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "createMemberRole",
            headers=self.get_authorization_header(villa_id),
            json={"name": name, "color": str(color), "permissions": permissions},
        )
        return (await self._request(request))["id"]

    @API
    async def edit_member_role(
        self,
        *,
        villa_id: int,
        role_id: int,
        name: str,
        color: Color,
        permissions: List[Permission],
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "editMemberRole",
            headers=self.get_authorization_header(villa_id),
            json={
                "id": role_id,
                "name": name,
                "color": str(color),
                "permissions": permissions,
            },
        )
        await self._request(request)

    @API
    async def delete_member_role(
        self,
        *,
        villa_id: int,
        role_id: int,
    ) -> None:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "deleteMemberRole",
            headers=self.get_authorization_header(villa_id),
            json={"id": role_id},
        )
        await self._request(request)

    @API
    async def get_member_role_info(
        self,
        *,
        villa_id: int,
        role_id: int,
    ) -> MemberRoleDetail:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getMemberRoleInfo",
            headers=self.get_authorization_header(villa_id),
            params={"role_id": role_id},
        )
        return parse_obj_as(
            MemberRoleDetail,
            (await self._request(request))["role"],
        )

    @API
    async def get_villa_member_roles(
        self,
        *,
        villa_id: int,
    ) -> List[MemberRoleDetail]:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getVillaMemberRoles",
            headers=self.get_authorization_header(villa_id),
        )
        return parse_obj_as(
            List[MemberRoleDetail],
            (await self._request(request))["list"],
        )

    @API
    async def get_all_emoticons(self) -> List[Emoticon]:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getAllEmoticons",
            headers=self.get_authorization_header(),
        )
        return parse_obj_as(List[Emoticon], (await self._request(request))["list"])

    @API
    async def audit(
        self,
        *,
        villa_id: int,
        audit_content: str,
        pass_through: str,
        room_id: int,
        uid: int,
        content_type: ContentType,
    ) -> str:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "audit",
            headers=self.get_authorization_header(villa_id),
            json={
                "audit_content": audit_content,
                "pass_through": pass_through,
                "room_id": room_id,
                "uid": uid,
                "content_type": content_type,
            },
        )
        return (await self._request(request))["audit_id"]

    @API
    async def transfer_image(
        self,
        *,
        url: str,
    ) -> str:
        request = Request(
            method="POST",
            url=self.adapter.base_url / "transferImage",
            headers=self.get_authorization_header(),
            json={
                "url": url,
            },
        )
        return (await self._request(request))["new_url"]

    @API
    async def get_upload_image_params(
        self,
        *,
        md5: str,
        ext: str,
        villa_id: Optional[int] = None,
    ) -> UploadImageParamsReturn:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getUploadImageParams",
            headers=self.get_authorization_header(villa_id),
            params={
                "md5": md5,
                "ext": ext,
            },
        )
        return parse_obj_as(UploadImageParamsReturn, await self._request(request))

    async def upload_image(
        self,
        image: Union[bytes, BytesIO, Path],
        ext: Optional[str] = None,
        villa_id: Optional[int] = None,
    ) -> ImageUploadResult:
        """上传图片

        参数:
            image: 图片内容/路径
            ext: 图片拓展，不填时自动判断
            villa_id: 上传所在的大别野 ID，不传时使用测试别野 ID

        异常:
            ValueError: 无法获取图片拓展名

        返回:
            ImageUploadResult: 上传结果
        """
        if isinstance(image, Path):
            image = image.read_bytes()
        elif isinstance(image, BytesIO):
            image = image.getvalue()
        img_md5 = get_img_md5(image)
        ext = ext or get_img_extenion(image)
        if ext is None:
            raise ValueError("cannot guess image extension")
        upload_params = await self.get_upload_image_params(
            md5=img_md5,
            ext=ext,
            villa_id=villa_id,
        )
        request = Request(
            "POST",
            url=upload_params.params.host,
            data=upload_params.params.to_upload_data(),
            files={"file": image},
        )
        return parse_obj_as(ImageUploadResult, await self._request(request))

    async def get_websocket_info(
        self,
    ) -> WebsocketInfo:
        request = Request(
            method="GET",
            url=self.adapter.base_url / "getWebsocketInfo",
            headers=self.get_authorization_header(),
        )
        return parse_obj_as(WebsocketInfo, await self._request(request))


def _parse_components(components: List[Component]) -> Optional[Panel]:
    small_total = [[]]
    mid_total = [[]]
    big_total = []
    for com in components:
        com_lenght = len(com.text.encode("utf-8"))
        if com_lenght <= 0:
            log("warning", f"component {com.id} text is empty, ignore")
        elif com_lenght <= 6:
            small_total[-1].append(com)
            if len(small_total[-1]) >= 3:
                small_total.append([])
        elif com_lenght <= 12:
            mid_total[-1].append(com)
            if len(mid_total[-1]) >= 2:
                mid_total.append([])
        elif com_lenght <= 30:
            big_total[-1].append([com])
        else:
            log("warning", f"component {com.id} text is too long, ignore")
    if not small_total[-1]:
        small_total.pop()
    small_total = small_total or None
    if not mid_total[-1]:
        mid_total.pop()
    mid_total = mid_total or None
    big_total = big_total or None
    if small_total or mid_total or big_total:
        return Panel(
            small_component_group_list=small_total,
            mid_component_group_list=mid_total,
            big_component_group_list=big_total,
        )
    return None
