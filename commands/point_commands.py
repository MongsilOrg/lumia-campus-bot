import discord
from discord import app_commands
from discord.ext import commands
from repository.point_repository import *
from utils.views import error_view, success_view, warn_view, info_view


class PointSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="포인트", description="내 포인트를 확인합니다.")
    async def get_point_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        result = await fetch_point(user_id)
        if result is None:
            await interaction.followup.send(
                view=error_view("등록되지 않은 사용자예요.\n관리자에게 문의해 주세요."),
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            view=info_view(
                f"## 📊 포인트 조회\n\n"
                f"현재 보유 포인트\n"
                f"# {result}P"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="포인트_조회", description="다른 유저의 포인트를 확인합니다.")
    @app_commands.describe(member="포인트를 조회할 유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def get_user_point_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        result = await fetch_point(member.id)
        if result is None:
            await interaction.followup.send(
                view=error_view("등록되지 않은 사용자예요."), ephemeral=True
            )
            return
        await interaction.followup.send(
            view=info_view(
                f"## 📊 포인트 조회\n\n"
                f"**{member.display_name}**님의 보유 포인트\n"
                f"# {result}P"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="포인트_추가", description="포인트를 추가합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="추가할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def add_point_cmd(self, interaction: discord.Interaction, member: discord.Member, points: int):
        await interaction.response.defer(ephemeral=True)
        if points <= 0:
            await interaction.followup.send(
                view=warn_view("추가할 포인트는 1 이상이어야 해요."), ephemeral=True
            )
            return
        try:
            result = await plus_point(member.id, points)
        except Exception:
            await interaction.followup.send(
                view=error_view("포인트 추가 중 오류가 발생했어요."), ephemeral=True
            )
            return
        if result is None:
            await interaction.followup.send(
                view=error_view("등록되지 않은 사용자예요."), ephemeral=True
            )
            return
        await interaction.followup.send(
            view=success_view(
                f"**{member.display_name}**님에게 **{points}P**가 추가되었어요.\n"
                f"현재 포인트: **{result}P**"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="포인트_감소", description="포인트를 감소합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="감소할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def remove_point_cmd(self, interaction: discord.Interaction, member: discord.Member, points: int):
        await interaction.response.defer(ephemeral=True)
        if points <= 0:
            await interaction.followup.send(
                view=warn_view("감소할 포인트는 1 이상이어야 해요."), ephemeral=True
            )
            return
        try:
            result = await minus_point(member.id, points)
            await interaction.followup.send(
                view=success_view(
                    f"**{member.display_name}**님에게 **{points}P**가 차감되었어요.\n"
                    f"현재 포인트: **{result}P**"
                ),
                ephemeral=True,
            )
        except Exception as e:
            if "23514" in str(e):
                await interaction.followup.send(
                    view=warn_view(f"**{member.display_name}**님의 포인트가 부족해요."),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=error_view("포인트 차감 중 오류가 발생했어요."), ephemeral=True
                )

    @app_commands.command(name="포인트_업데이트", description="포인트를 업데이트합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="업데이트할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def update_point_cmd(self, interaction: discord.Interaction, member: discord.Member, points: int):
        await interaction.response.defer(ephemeral=True)
        if points < 0:
            await interaction.followup.send(
                view=warn_view("포인트는 0 이상이어야 해요."), ephemeral=True
            )
            return
        try:
            prev = await fetch_point(member.id)
            if prev is None:
                await interaction.followup.send(
                    view=error_view("등록되지 않은 사용자예요."), ephemeral=True
                )
                return
            result = await update_point(member.id, points)
            if result is None:
                await interaction.followup.send(
                    view=error_view("포인트 업데이트에 실패했어요."), ephemeral=True
                )
                return
            await interaction.followup.send(
                view=success_view(
                    f"**{member.display_name}**님의 포인트가 업데이트되었어요.\n"
                    f"**{prev}P** → **{points}P**"
                ),
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                view=error_view("포인트 업데이트 중 오류가 발생했어요."), ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PointSystem(bot))
