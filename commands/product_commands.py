import logging
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
from repository.product_repository import *
from commands.exchange import (
    refresh_dashboard,
    _has_required_role,
    is_coupon_code,
    product_name_autocomplete,
    purchase_result_view,
)
from utils.views import error_view, success_view, warn_view, info_view

log = logging.getLogger("lumia-campus-bot.products")

class ProductSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="상품_조회", description="등록된 상품들을 조회합니다.")
    @app_commands.default_permissions(administrator=True)
    async def get_product_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result, stock = await fetch_products_with_stock()
        if not result:
            await interaction.followup.send(
                view=info_view("등록된 상품이 없습니다."), ephemeral=True
            )
            return
        text = "## 📦 상품 목록\n\n"
        for name, cost, _image in result:
            qty = stock.get(name, 0)
            stock_text = "품절" if qty == 0 else f"재고 {qty}개"
            text += f"**{name}** {cost}P, {stock_text}\n"
        await interaction.followup.send(view=info_view(text), ephemeral=True)

    @app_commands.command(name="상품_추가", description="상품을 추가합니다.")
    @app_commands.describe(name="상품 이름을 입력해주세요.", price="상품 가격을 입력해주세요.", image_url="상품 이미지 URL을 입력해주세요. 비워 둘 수 있습니다.")
    @app_commands.default_permissions(administrator=True)
    async def add_product_cmd(self, interaction: discord.Interaction, name: str, price: int, image_url: str = None):
        await interaction.response.defer(ephemeral=True)
        if price < 0:
            await interaction.followup.send(
                view=warn_view("가격은 0 이상이어야 해요."), ephemeral=True
            )
            return
        if image_url is not None:
            parsed = urlparse(image_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                await interaction.followup.send(
                    view=warn_view("이미지 URL은 http:// 또는 https://로 시작해야 합니다."), ephemeral=True
                )
                return
        try:
            await add_product(name, price, interaction.user.display_name, image_url)
        except Exception as e:
            if "23505" in str(e):
                log.warning("[상품 추가] 중복 상품명: %s", name)
                await interaction.followup.send(
                    view=warn_view(f"이미 등록된 상품명이에요: **{name}**"), ephemeral=True
                )
            else:
                log.exception("[상품 추가] 실패: %s", name)
                await interaction.followup.send(
                    view=error_view(f"상품 **{name}** 추가 중 오류가 발생했어요.\n다시 시도해 주세요."),
                    ephemeral=True,
                )
            return
        await interaction.followup.send(
            view=success_view(f"상품을 추가했습니다: **{name}**, **{price}P**"),
            ephemeral=True,
        )
        await refresh_dashboard(self.bot)

    @app_commands.command(name="상품_삭제", description="상품을 삭제합니다.")
    @app_commands.describe(name="상품 이름을 입력하세요.")
    @app_commands.autocomplete(name=product_name_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def delete_product_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        result = await delete_product(name)
        if result is None:
            await interaction.followup.send(
                view=error_view(f"존재하지 않는 상품이에요: **{name}**"), ephemeral=True
            )
            return
        await interaction.followup.send(
            view=success_view(f"상품을 삭제했습니다: **{result}**"), ephemeral=True
        )
        await refresh_dashboard(self.bot)

    @app_commands.command(name="상품_구매", description="상품을 구매합니다.")
    @app_commands.describe(name="어떤 상품을 구매할지 입력하세요.")
    @app_commands.autocomplete(name=product_name_autocomplete)
    async def buy_product_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        if not isinstance(member, discord.Member) or not _has_required_role(member):
            await interaction.followup.send(
                view=error_view(
                    "구매 권한이 없어요.\n"
                    "학생회, 학부생, 재학생, 신입생 역할이 필요해요."
                ),
                ephemeral=True,
            )
            return
        try:
            result = await buy_product(interaction.user.id, name)
        except Exception:
            log.exception("[구매] 실패: user=%s product=%s", interaction.user.id, name)
            await interaction.followup.send(
                view=error_view(f"**{name}** 구매 처리 중 오류가 발생했어요.\n다시 시도해 주세요."),
                ephemeral=True,
            )
            return
        result_view, purchased = await purchase_result_view(member, name, result)
        await interaction.followup.send(view=result_view, ephemeral=True)
        if purchased:
            await refresh_dashboard(self.bot)

    @app_commands.command(name="쿠폰_추출", description="상품의 쿠폰 코드를 추출합니다.")
    @app_commands.describe(name="어떤 상품의 쿠폰 코드를 추출할지 입력하세요.")
    @app_commands.autocomplete(name=product_name_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def extract_coupon_code_cmd(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        products = await fetch_product()
        if not any(p[0] == name for p in products):
            await interaction.followup.send(
                view=error_view(f"존재하지 않는 상품이에요: **{name}**"), ephemeral=True
            )
            return
        try:
            result = await extract_coupon_code(interaction.user.id, name)
        except Exception:
            log.exception("[쿠폰 추출] 실패: user=%s product=%s", interaction.user.id, name)
            await interaction.followup.send(
                view=error_view(f"**{name}** 쿠폰 추출 중 오류가 발생했어요.\n다시 시도해 주세요."),
                ephemeral=True,
            )
            return
        if result is None or result == "재고가 없습니다":
            await interaction.followup.send(
                view=error_view(f"**{name}**의 재고가 없어요."), ephemeral=True
            )
        elif not is_coupon_code(result):
            log.error("[쿠폰 추출] 예상치 못한 RPC 결과: user=%s product=%s result=%r", interaction.user.id, name, result)
            await interaction.followup.send(
                view=error_view(f"**{name}** 쿠폰 추출 결과를 확인하지 못했습니다.\n관리자에게 문의해주세요."),
                ephemeral=True,
            )
        else:
            log.info("[쿠폰 추출] 완료: user=%s product=%s", interaction.user.id, name)
            await interaction.followup.send(
                view=success_view(f"쿠폰 코드: `{result}`"), ephemeral=True
            )
            await refresh_dashboard(self.bot)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProductSystem(bot))
