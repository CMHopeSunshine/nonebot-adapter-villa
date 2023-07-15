from typing import TYPE_CHECKING, Any

from nonebot.drivers import Request
from nonebot.utils import escape_tag

from .models import ApiResponse
from ..exception import (
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
    VillaAdapterException,
)
from ..utils import log

if TYPE_CHECKING:
    from ..adapter import Adapter
    from ..bot import Bot


async def _request(adapter: "Adapter", bot: "Bot", request: Request) -> Any:
    try:
        data = await adapter.request(request)
        log(
            "TRACE",
            f"API code: {data.status_code} response: {escape_tag(str(data.content))}",
        )
        resp = ApiResponse.parse_raw(data.content)  # type: ignore
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
        raise ActionFailed(data.status_code, resp)
    except VillaAdapterException:
        raise
    except Exception as e:
        raise NetworkError("API request failed") from e
