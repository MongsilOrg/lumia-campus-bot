from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    BOT_TOKEN: str
    GUILD_ID: int
    DASHBOARD_CHANNEL_ID: int
    GOOGLE_SHEETS_CLIENT_EMAIL: str
    GOOGLE_SHEETS_PRIVATE_KEY: str
    POINT_SPREADSHEET_ID: str
    COUPON_SPREADSHEET_ID: str

    @classmethod
    def from_env(cls) -> BotConfig:
        load_dotenv()

        def _require(key: str) -> str:
            val = os.getenv(key)
            if not val:
                raise RuntimeError(f"환경변수 {key}가 설정되지 않았습니다.")
            return val

        return cls(
            BOT_TOKEN=_require("BOT_TOKEN"),
            GUILD_ID=int(_require("GUILD_ID")),
            DASHBOARD_CHANNEL_ID=int(_require("DASHBOARD_CHANNEL_ID")),
            GOOGLE_SHEETS_CLIENT_EMAIL=_require("GOOGLE_SHEETS_CLIENT_EMAIL"),
            GOOGLE_SHEETS_PRIVATE_KEY=_require("GOOGLE_SHEETS_PRIVATE_KEY"),
            POINT_SPREADSHEET_ID=_require("POINT_SPREADSHEET_ID"),
            COUPON_SPREADSHEET_ID=_require("COUPON_SPREADSHEET_ID"),
        )


config: BotConfig | None = None


def get_config() -> BotConfig:
    global config
    if config is None:
        config = BotConfig.from_env()
    return config
