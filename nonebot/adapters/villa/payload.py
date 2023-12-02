from enum import IntEnum
import struct
from typing import Literal

from google.protobuf.json_format import MessageToDict, Parse
from pydantic import BaseModel

from .pb.command_pb2 import (
    PHeartBeat,  # type: ignore
    PHeartBeatReply,  # type: ignore
    PKickOff,  # type: ignore
    PLogin,  # type: ignore
    PLoginReply,  # type: ignore
    PLogout,  # type: ignore
    PLogoutReply,  # type: ignore
)
from .pb.model_pb2 import RobotEvent as PRobotEvent  # type: ignore


class BizType(IntEnum):
    UNKNOWN = 0
    EXCHANGE_KEY = 1
    HEARTBEAT = 2
    LOGIN = 3
    LOGOUT = 4
    P_EXCHANGE_KEY = 5
    P_HEARTBEAT = 6
    P_LOGIN = 7
    P_LOGOUT = 8
    KICK_OFF = 51
    SHUTDOWN = 52
    P_KICK_OFF = 53
    ROOM_ENTER = 60
    ROOM_LEAVE = 61
    ROOM_CLOSE = 62
    ROOM_MSG = 63
    EVENT = 30001


class Payload(BaseModel):
    id: int
    flag: Literal[1, 2]
    biz_type: BizType
    app_id: Literal[104] = 104
    body_data: bytes

    @classmethod
    def from_bytes(cls, data: bytes):
        magic, data_len = struct.unpack("<II", data[:8])
        header_len, packet_id, flag, biz_type, app_id = struct.unpack(
            "<IQIIi",
            data[8:32],
        )
        body_data = data[32 : 8 + data_len]
        return cls(
            id=packet_id,
            flag=flag,
            biz_type=BizType(biz_type),
            app_id=app_id,
            body_data=body_data,
        )

    def to_bytes(self) -> bytes:
        changeable = (
            struct.pack(
                "<IQIIi",
                24,
                self.id,
                self.flag,
                self.biz_type,
                self.app_id,
            )
            + self.body_data
        )

        return (
            struct.pack(
                "<II",
                0xBABEFACE,
                len(changeable),
            )
            + changeable
        )


class HeartBeat(BaseModel):
    """心跳请求命令字"""

    # 客户端时间戳，精确到ms
    client_timestamp: str

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=1,
            biz_type=BizType.P_HEARTBEAT,
            body_data=Parse(self.json(), PHeartBeat()).SerializeToString(),
        ).to_bytes()


class HeartBeatReply(BaseModel):
    """心跳返回"""

    # 错误码 非0表示失败
    code: int = 0
    # 服务端时间戳，精确到ms
    server_timestamp: int

    @classmethod
    def from_proto(cls, content: bytes) -> "HeartBeatReply":
        return cls.parse_obj(
            MessageToDict(
                PHeartBeatReply().FromString(content),
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            ),
        )


class Login(BaseModel):
    """登录命令"""

    # 长连接侧唯一id，uint64格式
    uid: int
    # 用于业务后端验证的token
    token: str
    # 客户端操作平台枚举
    platform: int
    # 业务所在客户端应用标识，用于在同一个客户端隔离不同业务的长连接通道。
    app_id: int
    device_id: str
    # # 区域划分字段，通过uid+app_id+platform+region四个字段唯一确定一条长连接
    ## region: str
    # # 长连内部的扩展字段，是个map
    # meta: Dict[str, str]

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=1,
            biz_type=BizType.P_LOGIN,
            body_data=Parse(self.json(), PLogin()).SerializeToString(),
        ).to_bytes()


class LoginReply(BaseModel):
    """登录命令返回"""

    # 错误码 非0表示失败
    code: int = 0
    # 错误信息
    msg: str = ""
    # 服务端时间戳，精确到ms
    server_timestamp: int
    # 唯一连接ID
    conn_id: int

    @classmethod
    def from_proto(cls, content: bytes) -> "LoginReply":
        return cls.parse_obj(
            MessageToDict(
                PLoginReply().FromString(content),
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            ),
        )


class Logout(BaseModel):
    """登出命令字"""

    # 长连接侧唯一id，uint64格式
    uid: int
    # 客户端操作平台枚举
    platform: int
    # 业务所在客户端应用标识，用于在同一个客户端隔离不同业务的长连接通道。
    app_id: int
    # 客户端设备唯一标识
    device_id: str
    # 区域划分字段，通过uid+app_id+platform+region四个字段唯一确定一条长连接
    ## region: str

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=1,
            biz_type=BizType.P_LOGOUT,
            body_data=Parse(self.json(), PLogout()).SerializeToString(),
        ).to_bytes()


class LogoutReply(BaseModel):
    """登出命令返回"""

    # 错误码 非0表示失败
    code: int = 0
    # 错误信息
    msg: str = ""
    # 连接id
    conn_id: int

    @classmethod
    def from_proto(cls, content: bytes) -> "LogoutReply":
        return cls.parse_obj(
            MessageToDict(
                PLogoutReply().FromString(content),
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            ),
        )


class KickOff(BaseModel):
    """踢出连接协议"""

    # 踢出原因状态码
    code: int = 0
    # 状态码对应的文案
    reason: str = ""

    @classmethod
    def from_proto(cls, content: bytes) -> "KickOff":
        return cls.parse_obj(
            MessageToDict(
                PKickOff().FromString(content),
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            ),
        )


class Shutdown(BaseModel):
    """服务关机"""


def proto_to_event_data(content: bytes):
    return MessageToDict(
        PRobotEvent().FromString(content),
        preserving_proto_field_name=True,
        use_integers_for_enums=True,
    )
