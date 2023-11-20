from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import Dict, Literal

import betterproto
from pydantic import BaseModel


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
    # magic: Literal[0xBABEFACE] = 0xBABEFACE
    # data_len: int
    # header_len: int
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


@dataclass
class HeartBeat(betterproto.Message):
    """心跳请求命令字"""

    # 客户端时间戳，精确到ms
    client_timestamp: str = betterproto.string_field(1)

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=2,
            biz_type=BizType.P_HEARTBEAT,
            body_data=self.SerializeToString(),
        ).to_bytes()


@dataclass
class HeartBeatReply(betterproto.Message):
    """心跳返回"""

    # 错误码 非0表示失败
    code: int = betterproto.int32_field(1)
    # 服务端时间戳，精确到ms
    server_timestamp: int = betterproto.uint64_field(2)


@dataclass
class Login(betterproto.Message):
    """登录命令"""

    # 长连接侧唯一id，uint64格式
    uid: int = betterproto.uint64_field(1)
    # 用于业务后端验证的token
    token: str = betterproto.string_field(2)
    # 客户端操作平台枚举
    platform: int = betterproto.int32_field(3)
    # 业务所在客户端应用标识，用于在同一个客户端隔离不同业务的长连接通道。
    app_id: int = betterproto.int32_field(4)
    device_id: str = betterproto.string_field(5)
    # 区域划分字段，通过uid+app_id+platform+region四个字段唯一确定一条长连接
    region: str = betterproto.string_field(6)
    # 长连内部的扩展字段，是个map
    meta: Dict[str, str] = betterproto.map_field(
        7,
        betterproto.TYPE_STRING,
        betterproto.TYPE_STRING,
    )

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=2,
            biz_type=BizType.P_LOGIN,
            body_data=self.SerializeToString(),
        ).to_bytes()


@dataclass
class LoginReply(betterproto.Message):
    """登录命令返回"""

    # 错误码 非0表示失败
    code: int = betterproto.int32_field(1)
    # 错误信息
    msg: str = betterproto.string_field(2)
    # 服务端时间戳，精确到ms
    server_timestamp: int = betterproto.uint64_field(3)
    # 唯一连接ID
    conn_id: int = betterproto.uint64_field(4)


@dataclass
class Logout(betterproto.Message):
    """登出命令字"""

    # 长连接侧唯一id，uint64格式
    uid: int = betterproto.uint64_field(1)
    # 客户端操作平台枚举
    platform: int = betterproto.int32_field(2)
    # 业务所在客户端应用标识，用于在同一个客户端隔离不同业务的长连接通道。
    app_id: int = betterproto.int32_field(3)
    # 客户端设备唯一标识
    device_id: str = betterproto.string_field(4)
    # 区域划分字段，通过uid+app_id+platform+region四个字段唯一确定一条长连接
    region: str = betterproto.string_field(5)

    def to_bytes_package(self, id: int) -> bytes:
        return Payload(
            id=id,
            flag=2,
            biz_type=BizType.P_LOGOUT,
            body_data=self.SerializeToString(),
        ).to_bytes()


@dataclass
class LogoutReply(betterproto.Message):
    """登出命令返回"""

    # 错误码 非0表示失败
    code: int = betterproto.int32_field(1)
    # 错误信息
    msg: str = betterproto.string_field(2)
    # 连接id
    conn_id: int = betterproto.uint64_field(3)


@dataclass
class CommonReply(betterproto.Message):
    """通用返回"""

    # 错误码 非0表示失败
    code: int = betterproto.int32_field(1)
    # 错误信息
    msg: str = betterproto.string_field(2)


@dataclass
class KickOff(betterproto.Message):
    """踢出连接协议"""

    # 踢出原因状态码
    code: int = betterproto.int32_field(1)
    # 状态码对应的文案
    reason: str = betterproto.string_field(2)


@dataclass
class Shutdown(betterproto.Message):
    """服务关机"""
