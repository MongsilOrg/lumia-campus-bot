import re

import discord
from discord import app_commands
from discord.ext import commands
from repository.user_repository import *
from utils.views import error_view, success_view, warn_view


class UserSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="유저_정보등록", description="유저 정보를 등록합니다.")
    @app_commands.describe(member="유저를 선택하세요.", email="이메일을 입력하세요.(선택사항)", point="포인트를 입력하세요.(기본값: 0)")
    @app_commands.default_permissions(administrator=True)
    async def add_user_cmd(self, interaction: discord.Interaction, member: discord.Member, email: str = None, point: int = 0):
        await interaction.response.defer(ephemeral=True)
        if email is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            await interaction.followup.send(
                view=warn_view("올바른 이메일 형식이 아니에요. (예: user@example.com)"), ephemeral=True
            )
            return
        if point < 0:
            await interaction.followup.send(
                view=warn_view("포인트는 0 이상이어야 해요."), ephemeral=True
            )
            return
        try:
            result = await add_user(member.id, member.display_name, email, point)
            if result is None:
                await interaction.followup.send(
                    view=error_view(
                        f"**{member.display_name}**님의 등록에 실패했어요.\n다시 시도해 주세요."
                    ),
                    ephemeral=True,
                )
                return
            await interaction.followup.send(
                view=success_view(f"**{member.display_name}**님이 등록되었어요."),
                ephemeral=True,
            )
        except Exception as e:
            if "23505" in str(e):
                await interaction.followup.send(
                    view=warn_view(f"이미 등록된 유저예요: **{member.display_name}**"),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=error_view(
                        f"**{member.display_name}**님의 등록 중 오류가 발생했어요.\n다시 시도해 주세요."
                    ),
                    ephemeral=True,
                )

    @app_commands.command(name="유저_정보삭제", description="유저 정보를 삭제합니다.")
    @app_commands.describe(member="유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def delete_user_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await delete_user(member.id)
            if result is None:
                await interaction.followup.send(
                    view=error_view(f"등록되지 않은 유저예요: **{member.display_name}**"),
                    ephemeral=True,
                )
                return
            await interaction.followup.send(
                view=success_view(f"**{result}**님이 삭제되었어요."), ephemeral=True
            )
        except Exception as e:
            if "23503" in str(e):
                await interaction.followup.send(
                    view=warn_view("구매 이력이 있는 유저는 삭제할 수 없어요."), ephemeral=True
                )
            else:
                await interaction.followup.send(
                    view=error_view(
                        f"**{member.display_name}**님의 삭제 중 오류가 발생했어요.\n다시 시도해 주세요."
                    ),
                    ephemeral=True,
                )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserSystem(bot))
