import discord
from discord import app_commands
from discord.ext import commands
from repository.point_repository import *

class PointSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="포인트", description="내 포인트를 확인합니다.")
    @app_commands.default_permissions(administrator=True)
    async def get_point_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        result = await fetch_point(user_id)
        if result is None:
            await interaction.followup.send("포인트 조회 중 오류가 발생했습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"현재 포인트는 {result}점입니다.", ephemeral=True)


    @app_commands.command(name="포인트_조회", description="다른 유저의 포인트를 확인합니다.")
    @app_commands.describe(member="포인트를 조회할 유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def get_user_point_cmd(self, interaction: discord.Interaction , member : discord.Member ):
        await interaction.response.defer(ephemeral=True)
        result = await fetch_point(member.id)
        if result is None:
            await interaction.followup.send("포인트 조회 중 오류가 발생했습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"{member.display_name}님의 현재 포인트는 {result}P입니다.", ephemeral=True)

    @app_commands.command(name="포인트_추가", description="포인트를 추가합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="추가할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def add_point_cmd(self, interaction: discord.Interaction, member : discord.Member , points: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
            return
        result = await plus_point(member.id, points)
        if result is None:
            await interaction.followup.send("사용자가 존재하지 않습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"{member.display_name}에게 {points}점이 추가되었습니다.", ephemeral=True)

    @app_commands.command(name="포인트_감소", description="포인트를 감소합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="감소할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def remove_point_cmd(self, interaction: discord.Interaction, member : discord.Member , points: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
            return
        result = await minus_point(member.id, points)
        if result is None:
            await interaction.followup.send("사용자가 존재하지 않습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"{member.display_name}에게 {points}점이 차감되었습니다.", ephemeral=True)

    @app_commands.command(name="포인트_업데이트", description="포인트를 업데이트합니다.")
    @app_commands.describe(member="유저를 선택하세요.", points="업데이트할 포인트 양")
    @app_commands.default_permissions(administrator=True)
    async def update_point_cmd(self, interaction: discord.Interaction, member : discord.Member , points: int):
        await interaction.response.defer(ephemeral=True)
        prev = await fetch_point(member.id)
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
            return
        result = await update_point(member.id, points)
        if result is None:
            await interaction.followup.send("사용자가 존재하지 않습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"{member.display_name}의 포인트가 {prev}에서 {points}점으로 업데이트되었습니다.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PointSystem(bot))