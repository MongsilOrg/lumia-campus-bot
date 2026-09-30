import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import escape_markdown
from repository.log_repository import *
from view.pagination_view import *
from utils.views import info_view
from commands.exchange import product_name_autocomplete
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
                view=info_view("구매 이력이 없습니다."), ephemeral=True
            )
            return
        total_pages = (total_count + page_size - 1) // page_size
        pview = PaginationView(
            interaction.user.id,
            interaction.user.display_name,
            1,
            total_pages,
            build_purchase_lines(result, 1, page_size),
        )
        pview.message = await interaction.followup.send(view=pview, ephemeral=True)

    @app_commands.command(name="구매이력_조회", description="다른 유저의 구매 이력을 확인합니다.")
    @app_commands.describe(member="구매이력을 조회할 유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def get_user_log_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        page_size = 20
        result, total_count = await get_log(member.id, page=1, page_size=page_size)
        if not result:
            await interaction.followup.send(
                view=info_view(f"**{escape_markdown(member.display_name)}**님의 구매 이력이 없습니다."),
                ephemeral=True,
            )
            return
        total_pages = (total_count + page_size - 1) // page_size
        pview = PaginationView(
            member.id,
            member.display_name,
            1,
            total_pages,
            build_purchase_lines(result, 1, page_size),
        )
        pview.message = await interaction.followup.send(view=pview, ephemeral=True)

    @app_commands.command(name="상품별_이력조회", description="상품별 이력을 확인합니다.")
    @app_commands.describe(name="이력을 조회할 상품을 선택하세요.")
    @app_commands.autocomplete(name=product_name_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def get_product_log_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        page_size = 20
        result, total_count = await get_product_log(name, page=1, page_size=page_size)
        if not result:
            await interaction.followup.send(
                view=info_view(f"**{escape_markdown(name)}**의 구매 이력이 없습니다."),
                ephemeral=True,
            )
            return
        total_pages = (total_count + page_size - 1) // page_size
        pview = ProductPaginationView(name, 1, total_pages, build_buyer_lines(result, 1, page_size))
        pview.message = await interaction.followup.send(view=pview, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LogSystem(bot))
