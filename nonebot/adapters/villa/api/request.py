from typing import TYPE_CHECKING, Any

from nonebot.drivers import Request
from nonebot.utils import escape_tag

from ..utils import log
from .models import ApiResponse
from ..exception import (  # RateLimitException,
    ActionFailed,
    NetworkError,
    ApiNotAvailable,
    UnauthorizedException,
    VillaAdapterException,
)

if TYPE_CHECKING:
    from ..bot import Bot
    from ..adapter import Adapter


async def _request(adapter: "Adapter", bot: "Bot", request: Request) -> Any:
    try:
        # 目前好像无论正常还是错误的状态码都是200，只是retcode有所不同，所以暂时不检查状态码
        data = await adapter.request(request)
        log(
            "TRACE",
            f"API code: {data.status_code} response: {escape_tag(str(data.content))}",
        )
        resp = ApiResponse.parse_raw(data.content)  # type: ignore
        if resp.retcode == 0:
            return resp.data
        # if data.status_code in (200, 201, 204):
        #     return_data = data.content and json.loads(data.content)

        # elif data.status_code in (401, 403):
        #     raise UnauthorizedException(data)
        # elif data.status_code in (404, 405):
        #     raise ApiNotAvailable
        # elif data.status_code == 429:
        #     raise RateLimitException(data)
        else:
            raise ActionFailed(data.status_code, resp)
    except VillaAdapterException:
        raise
    except Exception as e:
        raise NetworkError("API request failed") from e
