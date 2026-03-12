import discord
from discord import app_commands
from discord.ext import commands
from repository.log_repository import *

class LogSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="구매이력", description="내 구매 이력을 확인합니다.")
    @app_commands.default_permissions(administrator=True)
    async def get_log_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = get_log(interaction.user.id)
        if result is None:
            await interaction.followup.send("구매 이력 조회 중 오류가 발생했습니다.", ephemeral=True)
            return 
        if not result:
            await interaction.followup.send("구매 이력이 없습니다.", ephemeral=True)
            return
        table = f"{'번호':<5} | {'상품명':<10} | {'쿠폰번호':<15}\n"
        table += "-" * 35 + "\n"
        for i, item in enumerate(result, start=1):
            store_name, product_code = item
            table += f"{i:<6} | {store_name:<11} | {product_code:<15}\n"
        await interaction.followup.send(f"```\n{table}```", ephemeral=True)


    @app_commands.command(name="구매이력_조회", description="다른 유저의 구매 이력을 확인합니다.")
    @app_commands.describe(member="구매이력을 조회할 유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def get_user_log_cmd(self, interaction: discord.Interaction , member : discord.Member ):
        await interaction.response.defer(ephemeral=True)
        result = get_log(member.id)
        if result is None:
            await interaction.followup.send("구매 이력 조회 중 오류가 발생했습니다.", ephemeral=True)
            return 
        if not result:
            await interaction.followup.send("구매 이력이 없습니다.", ephemeral=True)
            return
        table = f"{'번호':<5} | {'상품명':<10} | {'쿠폰번호':<15}\n"
        table += "-" * 35 + "\n"
        for i, item in enumerate(result, start=1):
            store_name, product_code = item
            table += f"{i:<6} | {store_name:<11} | {product_code:<15}\n"
        await interaction.followup.send(f"```\n{table}```", ephemeral=True)
    

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LogSystem(bot))