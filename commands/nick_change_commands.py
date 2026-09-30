import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import escape_markdown
from utils.views import error_view , success_view, warn_view
from repository.nick_repository import nick_change

log = logging.getLogger("lumia-campus-bot.nick")

NICK_MAX_LENGTH = 32

class NickChangeSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="닉변", description="유저의 닉네임을 변경합니다.")
    @app_commands.describe(member="닉네임을 변경할 유저를 선택해주세요.", new_nick="새 닉네임을 입력해주세요.")
    @app_commands.default_permissions(administrator=True)
    async def change_nick_cmd(self, interaction: discord.Interaction, member: discord.Member, new_nick: str):
        await interaction.response.defer(ephemeral=True)
        new_nick = new_nick.strip()
        if not new_nick or len(new_nick) > NICK_MAX_LENGTH:
            await interaction.followup.send(
                view=warn_view(f"닉네임은 1자 이상 {NICK_MAX_LENGTH}자 이하로 입력해주세요."),
                ephemeral=True,
            )
            return

        name = escape_markdown(member.display_name)
        old_nick = member.nick
        try:
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            await interaction.followup.send(
                view=error_view(
                    f"**{name}**님의 닉네임 변경 권한이 없습니다.\n봇의 역할 순서를 확인해주세요."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            log.exception("[닉변] 디스코드 닉네임 변경 실패: user=%s", member.id)
            await interaction.followup.send(
                view=error_view(
                    f"**{name}**님의 디스코드 닉네임을 바꾸지 못했습니다.\n다시 시도해주세요."
                ),
                ephemeral=True,
            )
            return

        try:
            await nick_change(member.id, new_nick)
        except Exception:
            log.exception("[닉변] DB 반영 실패: user=%s", member.id)
            try:
                await member.edit(nick=old_nick)
                text = "DB 반영에 실패해서 디스코드 닉네임을 원래대로 되돌렸습니다.\n다시 시도해주세요."
            except discord.HTTPException:
                log.exception("[닉변] 디스코드 닉네임 복구 실패: user=%s", member.id)
                text = "DB 반영에 실패했고 디스코드 닉네임도 되돌리지 못했습니다.\n닉네임을 직접 확인해주세요."
            await interaction.followup.send(view=error_view(text), ephemeral=True)
            return

        await interaction.followup.send(
            view=success_view(f"**{name}**님의 닉네임을 변경했습니다: **{escape_markdown(new_nick)}**"),
            ephemeral=True,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NickChangeSystem(bot))
