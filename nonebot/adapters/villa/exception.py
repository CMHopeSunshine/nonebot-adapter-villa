from typing import TYPE_CHECKING, Optional

from nonebot.exception import (
    ActionFailed as BaseActionFailed,
    AdapterException,
    ApiNotAvailable as BaseApiNotAvailable,
    NetworkError as BaseNetworkError,
    NoLogException as BaseNoLogException,
)

if TYPE_CHECKING:
    from .api import ApiResponse


class VillaAdapterException(AdapterException):
    def __init__(self):
        super().__init__("Villa")


class NoLogException(BaseNoLogException, VillaAdapterException):
    pass


class ActionFailed(BaseActionFailed, VillaAdapterException):
    def __init__(self, status_code: int, response: "ApiResponse"):
        self.status_code = status_code
        self.response = response

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {self.status_code}, "
            f"retcode={self.response.retcode}, "
            f"message={self.response.message}, "
            f"data={self.response.data}>"
        )

    def __str__(self):
        return self.__repr__()


class UnknownServerError(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(-502, response)


class InvalidRequest(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(-1, response)


class InsufficientPermission(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10318001, response)


class BotNotAdded(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10322002, response)


class PermissionDenied(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10322003, response)


class InvalidMemberBotAccessToken(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10322004, response)


class InvalidBotAuthInfo(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10322005, response)


class UnsupportedMsgType(ActionFailed):
    def __init__(self, response: "ApiResponse"):
        super().__init__(10322006, response)


class NetworkError(BaseNetworkError, VillaAdapterException):
    def __init__(self, msg: Optional[str] = None):
        super().__init__()
        self.msg: Optional[str] = msg
        """错误原因"""

    def __repr__(self):
        return f"<NetWorkError message={self.msg}>"

    def __str__(self):
        return self.__repr__()


class ApiNotAvailable(BaseApiNotAvailable, VillaAdapterException):
    def __init__(self, api: str):
        super().__init__()
        self.api = api

    def __repr__(self):
        return f"<ApiNotAvailable api={self.api}>"

    def __str__(self):
        return self.__repr__()
