from typing import Optional

from nonebot.exception import AdapterException
from nonebot.exception import ActionFailed as BaseActionFailed
from nonebot.exception import NetworkError as BaseNetworkError
from nonebot.exception import NoLogException as BaseNoLogException
from nonebot.exception import ApiNotAvailable as BaseApiNotAvailable

from .api import ApiResponse


class VillaAdapterException(AdapterException):
    def __init__(self):
        super().__init__("Villa")


class NoLogException(BaseNoLogException, VillaAdapterException):
    pass


class ActionFailed(BaseActionFailed, VillaAdapterException):
    def __init__(self, status_code: int, response: ApiResponse):
        self.status_code = status_code
        self.response = response

    def __repr__(self) -> str:
        return (
            f"<ActionFailed: {self.status_code}, retcode={self.response.retcode}, "
            f"message={self.response.message}, data={self.response.data}>"
        )

    def __str__(self):
        return self.__repr__()


class UnauthorizedException(ActionFailed):
    pass


# class RateLimitException(ActionFailed):
#     pass


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
