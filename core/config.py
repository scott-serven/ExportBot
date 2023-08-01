from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from types_.config import Config


__all__ = ("config",)


with open("config.toml", "rb") as fp:
    config: Config = tomllib.load(fp)
