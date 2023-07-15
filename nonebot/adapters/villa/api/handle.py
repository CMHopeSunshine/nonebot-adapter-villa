from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Union

from nonebot.drivers import Request

from pydantic import parse_obj_as

from .models import *
from .request import _request

if TYPE_CHECKING:
    from ..adapter import Adapter
    from ..bot import Bot


async def _check_member_bot_access_token(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    token: str,
) -> CheckMemberBotAccessTokenReturn:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/checkMemberBotAccessToken",
        headers=bot.get_authorization_header(
            villa_id,
        ),
        json={"token": token},
    )
    return parse_obj_as(
        CheckMemberBotAccessTokenReturn,
        await _request(adapter, bot, request),
    )


async def _get_villa(adapter: "Adapter", bot: "Bot", villa_id: int) -> Villa:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getVilla",
        headers=bot.get_authorization_header(villa_id),
    )
    return parse_obj_as(Villa, (await _request(adapter, bot, request))["villa"])


async def _get_member(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    uid: int,
) -> Member:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getMember",
        headers=bot.get_authorization_header(villa_id),
        json={"uid": uid},
    )
    return parse_obj_as(Member, (await _request(adapter, bot, request))["member"])


async def _get_villa_members(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    offset: int,
    size: int,
) -> MemberListReturn:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getVillaMembers",
        headers=bot.get_authorization_header(villa_id),
        json={"offset": offset, "size": size},
    )
    return parse_obj_as(MemberListReturn, await _request(adapter, bot, request))


async def _delete_villa_member(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    uid: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/deleteVillaMember",
        headers=bot.get_authorization_header(villa_id),
        json={"uid": uid},
    )
    await _request(adapter, bot, request)


async def _pin_message(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    msg_uid: str,
    is_cancel: bool,
    room_id: int,
    send_at: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/pinMessage",
        headers=bot.get_authorization_header(villa_id),
        json={
            "msg_uid": msg_uid,
            "is_cancel": is_cancel,
            "room_id": room_id,
            "send_at": send_at,
        },
    )
    await _request(adapter, bot, request)


async def _recall_message(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    msg_uid: str,
    room_id: int,
    msg_time: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/recallMessage",
        headers=bot.get_authorization_header(villa_id),
        json={"msg_uid": msg_uid, "room_id": room_id, "msg_time": msg_time},
    )
    await _request(adapter, bot, request)


async def _send_message(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    room_id: int,
    object_name: str,
    msg_content: Union[str, MessageContentInfo],
) -> str:
    if isinstance(msg_content, MessageContentInfo):
        content = msg_content.json(by_alias=True, exclude_none=True)
    else:
        content = msg_content
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/sendMessage",
        headers=bot.get_authorization_header(villa_id),
        json={"room_id": room_id, "object_name": object_name, "msg_content": content},
    )
    return (await _request(adapter, bot, request))["bot_msg_id"]


async def _create_group(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    group_name: str,
) -> int:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/createGroup",
        headers=bot.get_authorization_header(villa_id),
        json={"group_name": group_name},
    )
    return (await _request(adapter, bot, request))["group_id"]


async def _edit_group(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    group_id: int,
    group_name: str,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/editGroup",
        headers=bot.get_authorization_header(villa_id),
        json={"group_id": group_id, "group_name": group_name},
    )
    await _request(adapter, bot, request)


async def _delete_group(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    group_id: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/deleteGroup",
        headers=bot.get_authorization_header(villa_id),
        json={"group_id": group_id},
    )
    await _request(adapter, bot, request)


async def _get_group_list(adapter: "Adapter", bot: "Bot", villa_id: int) -> List[Group]:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getGroupList",
        headers=bot.get_authorization_header(villa_id),
    )
    return parse_obj_as(List[Group], (await _request(adapter, bot, request))["list"])


async def _sort_group_list(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    group_ids: List[int],
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/sortGroupList",
        headers=bot.get_authorization_header(villa_id),
        json={"villa_id": villa_id, "group_ids": group_ids},
    )
    await _request(adapter, bot, request)


async def _edit_room(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    room_id: int,
    room_name: str,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/editRoom",
        headers=bot.get_authorization_header(villa_id),
        json={"room_id": room_id, "room_name": room_name},
    )
    await _request(adapter, bot, request)


async def _delete_room(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    room_id: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/deleteRoom",
        headers=bot.get_authorization_header(villa_id),
        json={"room_id": room_id},
    )
    await _request(adapter, bot, request)


async def _get_room(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    room_id: int,
) -> Room:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getRoom",
        headers=bot.get_authorization_header(villa_id),
        json={"room_id": room_id},
    )
    return parse_obj_as(Room, (await _request(adapter, bot, request))["room"])


async def _get_villa_group_room_list(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
) -> List[GroupRoom]:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getVillaGroupRoomList",
        headers=bot.get_authorization_header(villa_id),
    )
    return parse_obj_as(
        List[GroupRoom],
        (await _request(adapter, bot, request))["list"],
    )


async def _sort_room_list(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    room_list: List[RoomSort],
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/sortRoomList",
        headers=bot.get_authorization_header(villa_id),
        json={"villa_id": villa_id, "room_list": [room.dict() for room in room_list]},
    )
    await _request(adapter, bot, request)


async def _operate_member_to_role(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    role_id: int,
    uid: int,
    is_add: bool,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/operateMemberToRole",
        headers=bot.get_authorization_header(villa_id),
        json={"role_id": role_id, "uid": uid, "is_add": is_add},
    )
    await _request(adapter, bot, request)


async def _create_member_role(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    name: str,
    color: Color,
    permissions: List[Permission],
) -> int:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/createMemberRole",
        headers=bot.get_authorization_header(villa_id),
        json={"name": name, "color": str(color), "permissions": permissions},
    )
    return (await _request(adapter, bot, request))["id"]


async def _edit_member_role(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    role_id: int,
    name: str,
    color: Color,
    permissions: List[Permission],
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/editMemberRole",
        headers=bot.get_authorization_header(villa_id),
        json={
            "id": role_id,
            "name": name,
            "color": str(color),
            "permissions": permissions,
        },
    )
    await _request(adapter, bot, request)


async def _delete_member_role(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    role_id: int,
) -> None:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/deleteMemberRole",
        headers=bot.get_authorization_header(villa_id),
        json={"id": role_id},
    )
    await _request(adapter, bot, request)


async def _get_member_role_info(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    role_id: int,
) -> MemberRoleDetail:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getMemberRoleInfo",
        headers=bot.get_authorization_header(villa_id),
        json={"role_id": role_id},
    )
    return parse_obj_as(
        MemberRoleDetail,
        (await _request(adapter, bot, request))["role"],
    )


async def _get_villa_member_roles(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
) -> List[MemberRoleDetail]:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getVillaMemberRoles",
        headers=bot.get_authorization_header(villa_id),
    )
    return parse_obj_as(
        List[MemberRoleDetail],
        (await _request(adapter, bot, request))["list"],
    )


async def _get_all_emoticons(adapter: "Adapter", bot: "Bot") -> List[Emoticon]:
    request = Request(
        method="GET",
        url=adapter.base_url / "vila/api/bot/platform/getAllEmoticons",
    )
    return parse_obj_as(List[Emoticon], (await _request(adapter, bot, request))["list"])


async def _audit(
    adapter: "Adapter",
    bot: "Bot",
    villa_id: int,
    audit_content: str,
    pass_through: str,
    room_id: int,
    uid: int,
) -> str:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/audit",
        headers=bot.get_authorization_header(villa_id),
        json={
            "audit_content": audit_content,
            "pass_through": pass_through,
            "room_id": room_id,
            "uid": uid,
        },
    )
    return (await _request(adapter, bot, request))["audit_id"]


async def _transfer_image(
    adapter: "Adapter",
    bot: "Bot",
    url: str,
) -> str:
    request = Request(
        method="POST",
        url=adapter.base_url / "vila/api/bot/platform/transferImage",
        headers=bot.get_authorization_header(),
        json={
            "url": url,
        },
    )
    return (await _request(adapter, bot, request))["new_url"]


API_HANDLERS: Dict[str, Callable[..., Awaitable[Any]]] = {
    "check_member_bot_access_token": _check_member_bot_access_token,
    "get_villa": _get_villa,
    "get_member": _get_member,
    "get_villa_members": _get_villa_members,
    "delete_villa_member": _delete_villa_member,
    "pin_message": _pin_message,
    "recall_message": _recall_message,
    "send_message": _send_message,
    "create_group": _create_group,
    "edit_group": _edit_group,
    "delete_group": _delete_group,
    "get_group_list": _get_group_list,
    "sort_group_list": _sort_group_list,
    "edit_room": _edit_room,
    "delete_room": _delete_room,
    "get_room": _get_room,
    "get_villa_group_room_list": _get_villa_group_room_list,
    "sort_room_list": _sort_room_list,
    "operate_member_to_role": _operate_member_to_role,
    "create_member_role": _create_member_role,
    "edit_member_role": _edit_member_role,
    "delete_member_role": _delete_member_role,
    "get_member_role_info": _get_member_role_info,
    "get_villa_member_roles": _get_villa_member_roles,
    "get_all_emoticons": _get_all_emoticons,
    "audit": _audit,
    "transfer_image": _transfer_image,
}
