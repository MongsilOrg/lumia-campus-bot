from __future__ import annotations

import logging

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

        # Cog 로드
        await bot.load_extension("commands.exchange")

        # 슬래시 커맨드 동기화 (특정 길드)
        guild = discord.Object(id=cfg.GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        log.info("슬래시 커맨드 %d개 동기화 완료 (guild=%s)", len(synced), cfg.GUILD_ID)

    bot.run(cfg.BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
