from typing import Union

from nonebot.adapters.villa import AddQuickEmoticonEvent, Bot, SendMessageEvent
from nonebot.adapters.villa.api import RoleType
from nonebot.permission import Permission


async def is_owner_or_admin(
    bot: Bot,
    event: Union[SendMessageEvent, AddQuickEmoticonEvent],
) -> bool:
    user_id = event.from_user_id if isinstance(event, SendMessageEvent) else event.uid
    user = await bot.get_member(villa_id=event.villa_id, uid=user_id)
    return any(
        role.role_type in (RoleType.OWNER, RoleType.ADMIN) for role in user.role_list
    )


OWNER_OR_ADMIN = Permission(is_owner_or_admin)
"""别野房东或管理员权限"""


async def is_owner(
    bot: Bot,
    event: Union[SendMessageEvent, AddQuickEmoticonEvent],
) -> bool:
    user_id = event.from_user_id if isinstance(event, SendMessageEvent) else event.uid
    user = await bot.get_member(villa_id=event.villa_id, uid=user_id)
    return any(role.role_type == RoleType.OWNER for role in user.role_list)


OWNER = Permission(is_owner)
"""别野房东权限"""


async def is_admin(
    bot: Bot,
    event: Union[SendMessageEvent, AddQuickEmoticonEvent],
) -> bool:
    user_id = event.from_user_id if isinstance(event, SendMessageEvent) else event.uid
    user = await bot.get_member(villa_id=event.villa_id, uid=user_id)
    return any(role.role_type == RoleType.ADMIN for role in user.role_list)


ADMIN = Permission(is_admin)
"""管理员权限"""
