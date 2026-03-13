import discord
from discord import app_commands
from discord.ext import commands
from repository.product_repository import *
from commands.exchange import refresh_dashboard
from utils.views import error_view, success_view, warn_view, info_view


class ProductSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="상품_조회", description="등록된 상품들을 조회합니다.")
    @app_commands.default_permissions(administrator=True)
    async def get_product_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await fetch_product()
        if result is None or len(result) == 0:
            await interaction.followup.send(
                view=error_view("등록된 상품이 없어요."), ephemeral=True
            )
            return
        text = "## 📦 상품 목록\n\n"
        for name, cost, _image in result:
            text += f"**{name}** — {cost}P\n"
        await interaction.followup.send(view=info_view(text), ephemeral=True)

    @app_commands.command(name="상품_추가", description="상품을 추가합니다.")
    @app_commands.describe(name="상품 이름을 입력하세요.", price="상품 가격을 입력하세요.", image_url="상품 이미지 URL을 입력하세요.(선택사항)")
    @app_commands.default_permissions(administrator=True)
    async def add_product_cmd(self, interaction: discord.Interaction, name: str, price: int, image_url: str = None):
        await interaction.response.defer(ephemeral=True)
        if price < 0:
            await interaction.followup.send(
                view=warn_view("가격은 0 이상이어야 해요."), ephemeral=True
            )
            return
        try:
            result = await add_product(name, price, interaction.user.display_name, image_url)
            await interaction.followup.send(
                view=success_view(f"상품 **{name}**이(가) **{price}P**로 추가되었어요."),
                ephemeral=True,
            )
            await refresh_dashboard(self.bot)
        except Exception as e:
            if "23505" in str(e):
                await interaction.followup.send(
                    view=warn_view(f"이미 등록된 상품명이에요: **{name}**"), ephemeral=True
                )
            else:
                await interaction.followup.send(
                    view=error_view("상품 추가 중 오류가 발생했어요."), ephemeral=True
                )

    @app_commands.command(name="상품_삭제", description="상품을 삭제합니다.")
    @app_commands.describe(name="상품 이름을 입력하세요.")
    @app_commands.default_permissions(administrator=True)
    async def delete_product_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        result = await delete_product(name)
        if result is None:
            await interaction.followup.send(
                view=error_view("상품이 존재하지 않아요."), ephemeral=True
            )
            return
        await interaction.followup.send(
            view=success_view(f"상품 **{result}**이(가) 삭제되었어요."), ephemeral=True
        )
        await refresh_dashboard(self.bot)

    @app_commands.command(name="상품_구매", description="상품을 구매합니다.")
    @app_commands.describe(name="어떤 상품을 구매할지 입력하세요.")
    async def buy_product_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await buy_product(interaction.user.id, name)
        except Exception:
            await interaction.followup.send(
                view=error_view("구매 처리 중 오류가 발생했어요."), ephemeral=True
            )
            return
        if result is None:
            await interaction.followup.send(
                view=error_view("구매 처리 중 오류가 발생했어요."), ephemeral=True
            )
            return
        error_map = {
            "주문하신 상품은 존재하지 않습니다 관리자에게 문의 주세요":
                "상품을 찾을 수 없어요.\n관리자에게 문의해 주세요.",
            "포인트가 부족합니다.":
                "포인트가 부족해요.",
            "재고가 없습니다 관리자에게 문의 주세요":
                "재고가 없어요.\n관리자에게 문의해 주세요.",
        }
        if result[0] in error_map:
            await interaction.followup.send(
                view=error_view(error_map[result[0]]), ephemeral=True
            )
        else:
            coupon_code, point = result
            await interaction.followup.send(
                view=success_view(
                    f"**{name}** 구매가 완료되었어요.\n"
                    f"쿠폰: `{coupon_code}`\n"
                    f"잔여 포인트: **{point}P**"
                ),
                ephemeral=True,
            )
            await refresh_dashboard(self.bot)

    @app_commands.command(name="쿠폰_추출", description="상품의 쿠폰 코드를 추출합니다.")
    @app_commands.describe(name="어떤 상품의 쿠폰 코드를 추출할지 입력하세요.")
    @app_commands.default_permissions(administrator=True)
    async def extract_coupon_code_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await extract_coupon_code(interaction.user.id, name)
        except Exception:
            await interaction.followup.send(
                view=error_view("쿠폰 추출 중 오류가 발생했어요."), ephemeral=True
            )
            return
        if result is None or result == "재고가 없습니다":
            await interaction.followup.send(
                view=error_view("재고가 없어요."), ephemeral=True
            )
        else:
            await interaction.followup.send(
                view=success_view(f"쿠폰 코드: `{result}`"), ephemeral=True
            )
            await refresh_dashboard(self.bot)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProductSystem(bot))
