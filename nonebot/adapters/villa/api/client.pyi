from .models import *

class ApiClient:
    async def check_member_bot_access_token(
        self,
        *,
        villa_id: int,
        token: str,
    ) -> CheckMemberBotAccessTokenReturn: ...
    async def get_villa(self, *, villa_id: int) -> Villa: ...
    async def get_member(self, *, villa_id: int, uid: int) -> Member: ...
    async def get_villa_members(
        self,
        *,
        villa_id: int,
        offset: int,
        size: int,
    ) -> MemberListReturn: ...
    async def delete_villa_member(self, *, villa_id: int, uid: int) -> None: ...
    async def pin_message(
        self,
        *,
        villa_id: int,
        msg_uid: str,
        is_cancel: bool,
        room_id: int,
        send_at: int,
    ) -> None: ...
    async def recall_message(
        self,
        *,
        villa_id: int,
        msg_uid: str,
        room_id: int,
        msg_time: int,
    ) -> None: ...
    async def send_message(
        self,
        *,
        villa_id: int,
        room_id: int,
        object_name: str,
        msg_content: str | MessageContentInfo,
    ) -> str: ...
    async def create_group(self, *, villa_id: int, group_name: str) -> int: ...
    async def edit_group(
        self,
        *,
        villa_id: int,
        group_id: int,
        group_name: str,
    ) -> None: ...
    async def delete_group(self, *, villa_id: int, group_id: int) -> None: ...
    async def get_group_list(self, *, villa_id: int) -> list[Group]: ...
    async def sort_group_list(self, *, villa_id: int, group_ids: list[int]) -> None: ...
    async def edit_room(
        self,
        *,
        villa_id: int,
        room_id: int,
        room_name: str,
    ) -> None: ...
    async def delete_room(self, *, villa_id: int, room_id: int) -> None: ...
    async def get_room(self, *, villa_id: int, room_id: int) -> Room: ...
    async def get_villa_group_room_list(self, *, villa_id: int) -> list[GroupRoom]: ...
    async def sort_room_list(
        self,
        *,
        villa_id: int,
        room_list: list[RoomSort],
    ) -> None: ...
    async def operate_member_to_role(
        self,
        *,
        villa_id: int,
        role_id: int,
        uid: int,
        is_add: bool,
    ) -> None: ...
    async def create_member_role(
        self,
        *,
        villa_id: int,
        name: str,
        color: str,
        permissions: list[Permission],
    ) -> int: ...
    async def edit_member_role(
        self,
        *,
        villa_id: int,
        role_id: int,
        name: str,
        color: str,
        permissions: list[Permission],
    ) -> None: ...
    async def delete_member_role(self, *, villa_id: int, role_id: int) -> None: ...
    async def get_member_role(
        self,
        *,
        villa_id: int,
        role_id: int,
    ) -> MemberRoleDetail: ...
    async def get_villa_member_roles(
        self,
        *,
        villa_id: int,
    ) -> list[MemberRoleDetail]: ...
    async def get_all_emoticon(self) -> list[Emoticon]: ...
    async def audit(
        self,
        *,
        villa_id: int,
        audit_content: str,
        pass_through: str,
        room_id: int,
        uid: int,
    ) -> str: ...
    async def transfer_image(
        self,
        *,
        url: str,
    ) -> str: ...
