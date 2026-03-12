import discord
from discord import app_commands
from discord.ext import commands
from repository.user_repository import *

class UserSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="유저_정보등록", description="유저 정보를 등록합니다.")
    @app_commands.describe(member="유저를 선택하세요.", email="이메일을 입력하세요.",point="포인트를 입력하세요.(기본값: 0)")
    @app_commands.default_permissions(administrator=True)
    async def add_user_cmd(self, interaction: discord.Interaction , member : discord.Member , email : str , point : int = 0):
        await interaction.response.defer(ephemeral=True)
        result = add_user(member.id, member.display_name, email , point)
        if result is None:
            await interaction.followup.send("유저 등록에 실패 했습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"정상적으로 {member.display_name}님이 등록되었습니다.", ephemeral=True)
    
    @app_commands.command(name="유저_정보삭제", description="유저 정보를 삭제합니다.")
    @app_commands.describe(member="유저를 선택하세요.")
    @app_commands.default_permissions(administrator=True)
    async def delete_user_cmd(self, interaction: discord.Interaction , member : discord.Member):
        await interaction.response.defer(ephemeral=True)
        result = delete_user(member.id)
        if result is None:
            await interaction.followup.send("유저 삭제에 실패 했습니다.", ephemeral=True)
            return
        await interaction.followup.send(f"정상적으로 {result}님이 삭제되었습니다.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserSystem(bot))