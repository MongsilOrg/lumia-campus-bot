import discord
from discord import app_commands
from discord.ext import commands
from repository.log_repository import get_log
from view.pagination_view import PaginationView, build_table
from utils.views import error_view


class LogSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="구매이력", description="내 구매 이력을 확인합니다.")
    @app_commands.default_permissions(administrator=True)
    async def get_log_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        page_size = 20
        result, total_count = await get_log(interaction.user.id, page=1, page_size=page_size)
        if not result:
            await interaction.followup.send(
                view=error_view("구매 이력이 없어요."), ephemeral=True
            )
            return
        total_pages = (total_count + page_size - 1) // page_size
        table_text = build_table(result, 1, page_size)
        pview = PaginationView(interaction.user.id, 1, total_pages, table_text)
        await interaction.followup.send(view=pview, ephemeral=True)

    @app_commands.command(name="구매이력_조회", description="다른 유저의 구매 이력을 확인합니다.")
    @app_commands.describe(member="구매이력을 조회할 유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def get_user_log_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        page_size = 20
        result, total_count = await get_log(member.id, page=1, page_size=page_size)
        if not result:
            await interaction.followup.send(
                view=error_view(f"**{member.display_name}**님의 구매 이력이 없어요."),
                ephemeral=True,
            )
            return
        total_pages = (total_count + page_size - 1) // page_size
        table_text = build_table(result, 1, page_size)
        pview = PaginationView(member.id, 1, total_pages, table_text)
        await interaction.followup.send(view=pview, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LogSystem(bot))
