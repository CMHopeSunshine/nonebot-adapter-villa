from datetime import datetime
from enum import Enum, IntEnum
import inspect
import json
import sys
from typing import Any, Dict, List, Literal, Optional, Union
from typing_extensions import TypeAlias

from pydantic import BaseModel, Field, validator


class ApiResponse(BaseModel):
    retcode: int
    message: str = ""
    data: Any

    class Config:
        allow_population_by_field_name = True
        fields = {"message": {"alias": "msg"}}


class BotAuth(BaseModel):
    bot_id: str
    bot_secret: str


# http事件回调部分
# see https://webstatic.mihoyo.com/vila/bot/doc/callback.html
class CommandParam(BaseModel):
    desc: str


class Command(BaseModel):
    name: str
    desc: Optional[str] = None
    params: Optional[List[CommandParam]] = None


class TemplateCustomSettings(BaseModel):
    name: str
    url: str


class Template(BaseModel):
    id: str
    name: str
    desc: Optional[str] = None
    icon: str
    commands: Optional[List[Command]] = None
    custom_settings: Optional[List[TemplateCustomSettings]] = None
    is_allowed_add_to_other_villa: Optional[bool] = None


class Robot(BaseModel):
    villa_id: int
    template: Template


class QuoteMessage(BaseModel):
    content: str
    msg_uid: str
    bot_msg_id: Optional[str] = None
    send_at: int
    msg_type: str
    from_user_id: Optional[int] = None
    from_user_nickname: Optional[str] = None
    from_user_id_str: str
    images: Optional[List[str]] = None


## 鉴权部分
## see https://webstatic.mihoyo.com/vila/bot/doc/auth_api/
class BotMemberAccessInfo(BaseModel):
    uid: int
    villa_id: int
    member_access_token: str
    bot_tpl_id: str


class CheckMemberBotAccessTokenReturn(BaseModel):
    access_info: BotMemberAccessInfo
    member: "Member"


# 大别野部分
# see https://webstatic.mihoyo.com/vila/bot/doc/villa_api/
class Villa(BaseModel):
    villa_id: int
    name: str
    villa_avatar_url: str
    onwer_uid: int
    is_official: bool
    introduce: str
    category_id: int
    tags: List[str]


# 用户部分
# see https://webstatic.mihoyo.com/vila/bot/doc/member_api/
class MemberBasic(BaseModel):
    uid: int
    nickname: str
    introduce: str
    avatar_url: str


class Member(BaseModel):
    basic: MemberBasic
    role_id_list: List[int]
    joined_at: datetime
    role_list: List["MemberRole"]


# 消息部分
# see https://webstatic.mihoyo.com/vila/bot/doc/message_api/
class MentionType(IntEnum):
    ALL = 1
    PART = 2

    def __repr__(self) -> str:
        return self.name


class MentionedRobot(BaseModel):
    type: Literal["mentioned_robot"] = Field(default="mentioned_robot", repr=False)
    bot_id: str

    bot_name: str = Field(exclude=True)


class MentionedUser(BaseModel):
    type: Literal["mentioned_user"] = Field(default="mentioned_user", repr=False)
    user_id: str

    user_name: Optional[str] = Field(exclude=True)


class MentionedAll(BaseModel):
    type: Literal["mention_all"] = Field(default="mention_all", repr=False)

    show_text: str = Field(exclude=True)


class VillaRoomLink(BaseModel):
    type: Literal["villa_room_link"] = Field(default="villa_room_link", repr=False)
    villa_id: str
    room_id: str

    room_name: Optional[str] = Field(exclude=True)


class Link(BaseModel):
    type: Literal["link"] = Field(default="link", repr=False)
    url: str
    requires_bot_access_token: bool

    show_text: str = Field(exclude=True)


class TextStyle(BaseModel):
    type: Literal["style"] = Field(default="style", repr=False)
    font_style: Literal["bold", "italic", "strikethrough", "underline"]


class TextEntity(BaseModel):
    offset: int
    length: int
    entity: Union[
        MentionedRobot,
        MentionedUser,
        MentionedAll,
        VillaRoomLink,
        Link,
        TextStyle,
    ]


class ImageSize(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None


class Image(BaseModel):
    url: str
    size: ImageSize = Field(default_factory=ImageSize)
    file_size: Optional[int] = None


class PreviewLink(BaseModel):
    icon_url: str
    image_url: str
    is_internal_link: bool
    title: str
    content: str
    url: str
    source_name: str


class Badge(BaseModel):
    icon_url: str
    text: str
    url: str


class PostMessageContent(BaseModel):
    post_id: str

    @validator("post_id")
    @classmethod
    def __deal_post_id(cls, v: str):
        s = v.split("/")[-1]
        if s.isdigit():
            return s
        raise ValueError(f"Invalid post_id: {v}, post_id must be a number.")


class TextMessageContent(BaseModel):
    text: str
    entities: List[TextEntity] = Field(default_factory=list)
    images: Optional[List[Image]] = None
    preview_link: Optional[PreviewLink] = None
    badge: Optional[Badge] = None


ImageMessageContent: TypeAlias = Image


class MentionedInfo(BaseModel):
    type: MentionType
    user_id_list: List[str] = Field(default_factory=list, alias="userIdList")


class QuoteInfo(BaseModel):
    quoted_message_id: str
    quoted_message_send_time: int
    original_message_id: str
    original_message_send_time: int


class User(BaseModel):
    portrait_uri: str = Field(alias="portraitUri")
    extra: Dict[str, Any]
    name: str
    alias: str
    id: str
    portrait: str

    @validator("extra", pre=True)
    @classmethod
    def extra_str_to_dict(cls, v: Any):
        if isinstance(v, str):
            return json.loads(v)
        return v


class Component(BaseModel):
    id: str
    text: str
    type: int = 1
    need_callback: Optional[bool] = None
    extra: str = ""


ComponentGroup = List[Component]


class Panel(BaseModel):
    template_id: Optional[int] = None
    small_component_group_list: Optional[List[ComponentGroup]] = None
    mid_component_group_list: Optional[List[ComponentGroup]] = None
    big_component_group_list: Optional[List[ComponentGroup]] = None


class ButtonType(IntEnum):
    Callback = 1
    Input = 2
    Link = 3


class Button(Component):
    c_type: ButtonType
    input: Optional[str] = None
    link: Optional[str] = None
    need_token: Optional[bool] = None


class CallbackButton(Button):
    c_type: Literal[ButtonType.Callback] = Field(
        default=ButtonType.Callback,
        init=False,
    )
    need_callback: Literal[True] = True


class InputButton(Button):
    c_type: Literal[ButtonType.Input] = Field(default=ButtonType.Input, init=False)
    input: str


class LinkButton(Button):
    c_type: Literal[ButtonType.Link] = Field(default=ButtonType.Link, init=False)
    link: str
    need_token: bool


class Trace(BaseModel):
    visual_room_version: str
    app_version: str
    action_type: int
    bot_msg_id: str
    client: str
    env: str
    rong_sdk_version: str


class MessageContentInfo(BaseModel):
    content: Union[TextMessageContent, ImageMessageContent, PostMessageContent]
    mentioned_info: Optional[MentionedInfo] = Field(default=None, alias="mentionedInfo")
    quote: Optional[QuoteInfo] = None
    panel: Optional[Panel] = None


class MessageContentInfoGet(MessageContentInfo):
    user: User
    trace: Optional[Trace] = None


# 房间部分
# see https://webstatic.mihoyo.com/vila/bot/doc/room_api/
class ListRoom(BaseModel):
    room_id: int
    room_name: str
    room_type: "RoomType"
    group_id: int


class Room(ListRoom):
    room_default_notify_type: "RoomDefaultNotifyType"
    send_msg_auth_range: "SendMsgAuthRange"


class RoomType(str, Enum):
    CHAT = "BOT_PLATFORM_ROOM_TYPE_CHAT_ROOM"
    POST = "BOT_PLATFORM_ROOM_TYPE_POST_ROOM"
    SCENE = "BOT_PLATFORM_ROOM_TYPE_SCENE_ROOM"
    LIVE = "BOT_PLATFORM_ROOM_TYPE_LIVE_ROOM"
    INVALID = "BOT_PLATFORM_ROOM_TYPE_INVALID"

    def __repr__(self) -> str:
        return self.name


class RoomDefaultNotifyType(str, Enum):
    NOTIFY = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_NOTIFY"
    IGNORE = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_IGNORE"
    INVALID = "BOT_PLATFORM_DEFAULT_NOTIFY_TYPE_INVALID"

    def __repr__(self) -> str:
        return self.name


class SendMsgAuthRange(BaseModel):
    is_all_send_msg: bool
    roles: List[int]


class GroupRoom(BaseModel):
    group_id: int
    group_name: str
    room_list: List[ListRoom]


class ListRoomType(IntEnum):
    CHAT = 1
    POST = 2
    SCENE = 3

    def __repr__(self) -> str:
        return self.name


class CreateRoomType(IntEnum):
    CHAT = 1
    POST = 2
    SCENE = 3

    def __repr__(self) -> str:
        return self.name


class CreateRoomDefaultNotifyType(IntEnum):
    NOTIFY = 1
    IGNORE = 2

    def __repr__(self) -> str:
        return self.name


class Group(BaseModel):
    group_id: int
    group_name: str


# 身份组部分
# see https://webstatic.mihoyo.com/vila/bot/doc/role_api/
class MemberRole(BaseModel):
    id: int
    name: str
    color: str
    role_type: "RoleType"
    villa_id: int
    member_num: Optional[int] = None
    web_color: str
    font_color: str
    bg_color: str
    has_manage_perm: Optional[bool] = None
    is_all_room: bool
    room_ids: List[int]
    color_scheme_id: int
    priority: int
    permissions: Optional[List["Permission"]] = None


class PermissionDetail(BaseModel):
    key: str
    name: str
    describe: str


class RoleType(str, Enum):
    ALL_MEMBER = "MEMBER_ROLE_TYPE_ALL_MEMBER"
    ADMIN = "MEMBER_ROLE_TYPE_ADMIN"
    OWNER = "MEMBER_ROLE_TYPE_OWNER"
    CUSTOM = "MEMBER_ROLE_TYPE_CUSTOM"
    UNKNOWN = "MEMBER_ROLE_TYPE_UNKNOWN"

    def __repr__(self) -> str:
        return self.name


class Permission(str, Enum):
    MENTION_ALL = "mention_all"
    RECALL_MESSAGE = "recall_message"
    PIN_MESSAGE = "pin_message"
    MANAGE_MEMBER_ROLE = "manage_member_role"
    EDIT_VILLA_INFO = "edit_villa_info"
    MANAGE_GROUP_AND_ROOM = "manage_group_and_room"
    VILLA_SILENCE = "villa_silence"
    BLACK_OUT = "black_out"
    HANDLE_APPLY = "handle_apply"
    MANAGE_CHAT_ROOM = "manage_chat_room"
    VIEW_DATA_BOARD = "view_data_board"
    MANAGE_CUSTOM_EVENT = "manage_custom_event"
    LIVE_ROOM_ORDER = "live_room_order"
    MANAGE_SPOTLIGHT_COLLECTION = "manage_spotlight_collection"

    def __repr__(self) -> str:
        return self.name


class Color(str, Enum):
    GREY = "#6173AB"
    PINK = "#F485D8"
    RED = "#F47884"
    ORANGE = "#FFA54B"
    GREEN = "#7ED321"
    BLUE = "#59A1EA"
    PURPLE = "#977EE1"
    LIGHT_BLUE = "#8F9BBF"  # 此颜色为所有人身份组颜色，无法作为创建和编辑身份组的颜色


# 表态表情部分
# see https://webstatic.mihoyo.com/vila/bot/doc/emoticon_api/
class Emoticon(BaseModel):
    emoticon_id: int
    describe_text: str
    icon: str


# 审核部分
# see https://webstatic.mihoyo.com/vila/bot/doc/audit_api/audit.html
class ContentType(str, Enum):
    TEXT = "AuditContentTypeText"
    IMAGE = "AuditContentTypeImage"


# 图片部分
# see https://webstatic.mihoyo.com/vila/bot/doc/img_api/upload.html


class CallbackVar(BaseModel):
    x_extra: str = Field(alias="x:extra")


class ImageUploadParams(BaseModel):
    accessid: str
    callback: str
    callback_var: CallbackVar
    dir: str
    expire: str
    host: str
    name: str
    policy: str
    signature: str
    x_oss_content_type: str
    object_acl: str
    content_disposition: str
    key: str
    success_action_status: str

    def to_upload_data(self) -> Dict[str, Any]:
        return {
            "x:extra": self.callback_var.x_extra,
            "OSSAccessKeyId": self.accessid,
            "signature": self.signature,
            "success_action_status": self.success_action_status,
            "name": self.name,
            "callback": self.callback,
            "x-oss-content-type": self.x_oss_content_type,
            "key": self.key,
            "policy": self.policy,
            "Content-Disposition": self.content_disposition,
        }


class UploadImageParamsReturn(BaseModel):
    type: str
    file_name: str
    max_file_size: int
    params: ImageUploadParams


class ImageUploadResult(BaseModel):
    object: str
    secret_url: str
    url: str


# Websocket 部分
# see https://webstatic.mihoyo.com/vila/bot/doc/websocket/websocket_api.html
class WebsocketInfo(BaseModel):
    websocket_url: str
    uid: int
    app_id: int
    platform: int
    device_id: str


for _, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and issubclass(obj, BaseModel):
        obj.update_forward_refs()


__all__ = [
    "ApiResponse",
    "BotAuth",
    "Command",
    "Template",
    "Robot",
    "QuoteMessage",
    "BotMemberAccessInfo",
    "CheckMemberBotAccessTokenReturn",
    "Villa",
    "MemberBasic",
    "Member",
    "MentionType",
    "MentionedRobot",
    "MentionedUser",
    "MentionedAll",
    "VillaRoomLink",
    "Link",
    "TextStyle",
    "TextEntity",
    "TextMessageContent",
    "ImageMessageContent",
    "PostMessageContent",
    "MentionedInfo",
    "QuoteInfo",
    "User",
    "Component",
    "Panel",
    "ButtonType",
    "Button",
    "CallbackButton",
    "InputButton",
    "LinkButton",
    "Trace",
    "ImageSize",
    "Image",
    "PreviewLink",
    "Badge",
    "MessageContentInfo",
    "MessageContentInfoGet",
    "Room",
    "RoomType",
    "RoomDefaultNotifyType",
    "SendMsgAuthRange",
    "GroupRoom",
    "ListRoomType",
    "CreateRoomType",
    "CreateRoomDefaultNotifyType",
    "Group",
    "MemberRole",
    "PermissionDetail",
    "RoleType",
    "Permission",
    "Color",
    "Emoticon",
    "ContentType",
    "ImageUploadParams",
    "UploadImageParamsReturn",
    "WebsocketInfo",
]
