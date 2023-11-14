from warnings import warn

warn(
    "nonebot.adapters.villa.api is DEPRECATED! "
    "Please use nonebot.adapters.villa.models instead.",
    DeprecationWarning,
    stacklevel=2,
)
from .models import *
