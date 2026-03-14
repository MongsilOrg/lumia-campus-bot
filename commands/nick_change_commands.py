import discord
from discord import app_commands
from discord.ext import commands
from utils.views import error_view , success_view
from repository.nick_repository import nick_change

class NickChangeSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="닉변", description="유저의 닉네임을 변경합니다.")
    @app_commands.describe(member="닉네임을 변경할 유저를 선택하세요.", new_nick="새 닉네임을 입력하세요.")
    @app_commands.default_permissions(administrator=True)
    async def change_nick_cmd(self, interaction: discord.Interaction, member: discord.Member, new_nick: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.edit(nick=new_nick)
            await nick_change(member.id, new_nick)
            await interaction.followup.send(
                view=success_view(f"**{member.display_name}**님의 닉네임이 **{new_nick}**(으)로 변경되었어요."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                view=error_view(
                    f"**{member.display_name}**님의 닉네임 변경 권한이 없어요.\n봇의 역할 순서를 확인해 주세요."
                ),
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                view=error_view(
                    f"**{member.display_name}**님의 닉네임 변경 중 오류가 발생했어요.\n다시 시도해 주세요."
                ),
                ephemeral=True,
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NickChangeSystem(bot))