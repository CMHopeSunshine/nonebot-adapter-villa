from functools import partial
import hashlib
import imghdr
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    overload,
)
from typing_extensions import Concatenate, ParamSpec

from nonebot.utils import logger_wrapper

if TYPE_CHECKING:
    from .bot import Bot

B = TypeVar("B", bound="Bot")
R = TypeVar("R")
P = ParamSpec("P")


log = logger_wrapper("Villa")


def exclude_none(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


class API(Generic[B, P, R]):
    def __init__(self, func: Callable[Concatenate[B, P], Awaitable[R]]) -> None:
        self.func = func

    def __set_name__(self, owner: Type[B], name: str) -> None:
        self.name = name

    @overload
    def __get__(self, obj: None, objtype: Type[B]) -> "API[B, P, R]":
        ...

    @overload
    def __get__(self, obj: B, objtype: Optional[Type[B]]) -> Callable[P, Awaitable[R]]:
        ...

    def __get__(
        self,
        obj: Optional[B],
        objtype: Optional[Type[B]] = None,
    ) -> "API[B, P, R] | Callable[P, Awaitable[R]]":
        if obj is None:
            return self

        return partial(obj.call_api, self.name)  # type: ignore

    async def __call__(self, inst: B, *args: P.args, **kwds: P.kwargs) -> R:
        return await self.func(inst, *args, **kwds)


def get_img_extenion(img_bytes: bytes) -> Optional[str]:
    return imghdr.what(None, h=img_bytes)


def get_img_md5(img_bytes: bytes) -> str:
    return hashlib.md5(img_bytes).hexdigest()
