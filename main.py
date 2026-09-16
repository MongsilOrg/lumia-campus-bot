from __future__ import annotations

import sentry_sdk, os
from dotenv import load_dotenv

# utils.config 를 import 하기 전이라 여기서 .env 를 읽어야 DSN 이 빈 문자열로 안 들어간다
load_dotenv()


def _sentry_before_send(event, hint):
    """일시적 네트워크 에러는 Sentry로 보내지 않는다."""
    exc_info = hint.get("exc_info")
    if exc_info:
        name = getattr(exc_info[0], "__name__", "")
        msg = str(exc_info[1])
        if name in ("TimeoutError", "ConnectTimeoutError", "ReadTimeout", "ConnectionError", "ClientConnectorError", "ClientOSError", "ServerDisconnectedError", "WSServerHandshakeError", "ConnectionClosed", "ConnectionResetError"):
            return None
        for _t in ("Connection timeout", "Cannot connect to host", "Temporary failure in name resolution", "네트워크 오류", "연결 중 오류"):
            if _t in msg:
                return None
    return event


sentry_sdk.init(dsn=os.getenv("SENTRY_DSN", ""), traces_sample_rate=0.1, environment="production", before_send=_sentry_before_send)

import logging
from service.superbase import init_supabase
import discord
from discord.ext import commands

from utils.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> None:
    cfg = get_config()

    intents = discord.Intents.default()
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        log.info("봇 로그인: %s (ID: %s)", bot.user, bot.user.id)

        if not hasattr(bot, "_setup_done"):
            bot._setup_done = True
            await init_supabase()
            await bot.load_extension("commands.exchange")
            await bot.load_extension("commands.point_commands")
            await bot.load_extension("commands.user_commands")
            await bot.load_extension("commands.log_commands")
            await bot.load_extension("commands.product_commands")
            await bot.load_extension("commands.nick_change_commands")
            # 기존 슬래시 커맨드 정리 (서버에서 제거)
            guild = discord.Object(id=cfg.GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            log.info("슬래시 커맨드 동기화 완료")

    

    bot.run(cfg.BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
