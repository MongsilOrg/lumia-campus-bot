from __future__ import annotations

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
            # 기존 슬래시 커맨드 정리 (서버에서 제거)
            guild = discord.Object(id=cfg.GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            log.info("슬래시 커맨드 동기화 완료")

    

    bot.run(cfg.BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
