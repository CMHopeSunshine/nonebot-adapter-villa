from typing import TYPE_CHECKING, List, Union

from .models import *

if TYPE_CHECKING:

    class ApiClient:
        async def check_member_bot_access_token(
            self, *, villa_id: int, token: str
        ) -> CheckMemberBotAccessTokenReturn:
            ...

        async def get_villa(self, *, villa_id: int) -> Villa:
            ...

        async def get_member(self, *, villa_id: int, uid: int) -> Member:
            ...

        async def get_villa_members(
            self, *, villa_id: int, offset: int, size: int
        ) -> MemberListReturn:
            ...

        async def delete_villa_member(self, *, villa_id: int, uid: int) -> None:
            ...

        async def pin_message(
            self,
            *,
            villa_id: int,
            msg_uid: str,
            is_cancel: bool,
            room_id: int,
            send_at: int,
        ) -> None:
            ...

        async def recall_message(
            self, *, villa_id: int, msg_uid: str, room_id: int, msg_time: int
        ) -> None:
            ...

        async def send_message(
            self,
            *,
            villa_id: int,
            room_id: int,
            object_name: str,
            msg_content: Union[str, MessageContentInfo],
        ) -> str:
            ...

        async def create_group(self, *, villa_id: int, group_name: str) -> int:
            ...

        async def edit_group(
            self, *, villa_id: int, group_id: int, group_name: str
        ) -> None:
            ...

        async def delete_group(self, *, villa_id: int, group_id: int) -> None:
            ...

        async def get_group_list(self, *, villa_id: int) -> List[Group]:
            ...

        async def sort_group_list(self, *, villa_id: int, group_ids: List[int]) -> None:
            ...

        async def edit_room(
            self, *, villa_id: int, room_id: int, room_name: str
        ) -> None:
            ...

        async def delete_room(self, *, villa_id: int, room_id: int) -> None:
            ...

        async def get_room(self, *, villa_id: int, room_id: int) -> Room:
            ...

        async def get_villa_group_room_list(self, *, villa_id: int) -> GroupRoom:
            ...

        async def sort_room_list(
            self, *, villa_id: int, room_list: List[RoomSort]
        ) -> None:
            ...

        async def operate_member_to_role(
            self, *, villa_id: int, role_id: int, uid: int, is_add: bool
        ) -> None:
            ...

        async def create_member_role(
            self,
            *,
            villa_id: int,
            name: str,
            color: Color,
            permissions: List[Permission],
        ) -> int:
            ...

        async def edit_member_role(
            self,
            *,
            villa_id: int,
            role_id: int,
            name: str,
            color: Color,
            permissions: List[Permission],
        ) -> None:
            ...

        async def delete_member_role(self, *, villa_id: int, role_id: int) -> None:
            ...

        async def get_member_role_info(
            self, *, villa_id: int, role_id: int
        ) -> MemberRoleDetail:
            ...

        async def get_villa_member_roles(
            self, *, villa_id: int
        ) -> List[MemberRoleDetail]:
            ...

        async def get_all_emoticon(self) -> List[Emoticon]:
            ...

        async def audit(
            self,
            *,
            villa_id: int,
            audit_content: str,
            pass_through: str,
            room_id: int,
            uid: int,
        ) -> str:
            ...

else:

    class ApiClient:
        ...
