from __future__ import annotations

import logging

import discord
from discord.ext import commands

from utils.config import get_config
from repository.point_repository import fetch_point
from repository.product_repository import fetch_product, buy_product

log = logging.getLogger(__name__)

REQUIRED_ROLES = {"학생회", "학부생", "재학생", "신입생"}


# ── 공통 뷰 빌더 ──


def _view(
    text: str,
    colour: discord.Colour,
) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=colour)
    container.add_item(discord.ui.TextDisplay(text))
    view.add_item(container)
    return view


def _loading_view(text: str) -> discord.ui.LayoutView:
    return _view(f"⏳ {text}", discord.Colour.light_grey())


def _error_view(text: str) -> discord.ui.LayoutView:
    return _view(f"❌ {text}", discord.Colour.red())


# ── 유틸 ──


def _get_nickname(member: discord.Member) -> str:
    return member.nick or member.global_name or member.name


def _has_required_role(member: discord.Member) -> bool:
    return any(role.name in REQUIRED_ROLES for role in member.roles)


# ── 대시보드 (채널 상주, 영구) ──


class DashboardView(discord.ui.LayoutView):
    def __init__(self, products=None):
        super().__init__(timeout=None)
        if products is not None:
            existing = list(self.children)
            self.clear_items()

            container = discord.ui.Container(accent_colour=discord.Colour.blurple())
            container.add_item(
                discord.ui.TextDisplay(
                    "# 🏪 루미아 상점\n"
                    "-# 루미아 캠퍼스"
                )
            )
            for name, cost, image in products:
                text = discord.ui.TextDisplay(f"**{name}** — {cost}P")
                if image:
                    container.add_item(
                        discord.ui.Section(
                            text,
                            accessory=discord.ui.Thumbnail(image),
                        )
                    )
                else:
                    container.add_item(text)
            container.add_item(
                discord.ui.TextDisplay(
                    "\n아래 버튼을 눌러 포인트 조회 또는 상품 구매를 시작해 보세요."
                )
            )
            self.add_item(container)
            for child in existing:
                self.add_item(child)

    row: discord.ui.ActionRow[DashboardView] = discord.ui.ActionRow()

    @row.button(
        label="📊 포인트 조회",
        custom_id="dashboard:point_check",
        style=discord.ButtonStyle.secondary,
    )
    async def point_check_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await _handle_point_check(interaction)

    @row.button(
        label="🛒 상품 구매",
        custom_id="dashboard:exchange",
        style=discord.ButtonStyle.primary,
    )
    async def buy_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await _handle_buy_start(interaction)


# ── 포인트 조회 ──


async def _handle_point_check(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        view=_loading_view("포인트를 조회하고 있어요..."), ephemeral=True
    )

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.edit_original_response(
            view=_error_view("서버 멤버 정보를 확인할 수 없어요.")
        )
        return

    try:
        points = await fetch_point(member.id)
    except Exception:
        log.exception("[포인트 조회] 데이터 조회 실패")
        await interaction.edit_original_response(
            view=_error_view("포인트 조회 중 오류가 발생했어요.")
        )
        return

    if points is None:
        await interaction.edit_original_response(
            view=_error_view(
                "등록되지 않은 사용자예요.\n관리자에게 문의해 주세요."
            )
        )
        return

    nickname = _get_nickname(member)
    await interaction.edit_original_response(
        view=_view(
            f"## 📊 포인트 조회\n\n"
            f"**{nickname}**님의 보유 포인트\n"
            f"# {points}P",
            discord.Colour.blue(),
        )
    )


# ── 상품 구매 시작 ──


async def _handle_buy_start(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        view=_loading_view("정보를 확인하고 있어요..."), ephemeral=True
    )

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.edit_original_response(
            view=_error_view("서버 멤버 정보를 확인할 수 없어요.")
        )
        return

    if not _has_required_role(member):
        await interaction.edit_original_response(
            view=_error_view(
                "구매 권한이 없어요.\n"
                "학생회·학부생·재학생·신입생 역할이 필요해요."
            )
        )
        return

    try:
        products = await fetch_product()
        points = await fetch_point(member.id)
    except Exception:
        log.exception("[구매] 데이터 조회 실패")
        await interaction.edit_original_response(
            view=_error_view("데이터 조회 중 오류가 발생했어요.")
        )
        return

    if points is None:
        await interaction.edit_original_response(
            view=_error_view(
                "등록되지 않은 사용자예요.\n관리자에게 문의해 주세요."
            )
        )
        return

    if not products:
        await interaction.edit_original_response(
            view=_error_view("현재 구매 가능한 상품이 없어요.")
        )
        return

    select_view = _make_product_select_view(member, products, points)
    await interaction.edit_original_response(view=select_view)


# ── 상품 선택 View ──


def _make_product_select_view(
    member: discord.Member, products: list, points: int
) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=180)
    member_id = member.id
    nickname = _get_nickname(member)

    container = discord.ui.Container(accent_colour=discord.Colour.blurple())
    container.add_item(
        discord.ui.TextDisplay(
            f"## 🛒 상품 구매\n\n"
            f"**{nickname}**님, 구매할 상품을 선택해 주세요.\n"
            f"보유 포인트: **{points}P**"
        )
    )
    view.add_item(container)

    row = discord.ui.ActionRow()
    select = discord.ui.Select(
        placeholder="상품을 선택해 주세요",
        options=[
            discord.SelectOption(
                label=name,
                description=f"{cost}P",
                value=name,
            )
            for name, cost, _image in products
        ],
    )

    async def on_select(select_interaction: discord.Interaction):
        if select_interaction.user.id != member_id:
            return
        selected_name = select.values[0]
        selected_cost = next(
            cost for name, cost, _img in products if name == selected_name
        )
        view.stop()
        confirm_view = _make_buy_confirm_view(
            member, nickname, selected_name, selected_cost, points
        )
        await select_interaction.response.edit_message(view=confirm_view)

    select.callback = on_select
    row.add_item(select)
    view.add_item(row)

    return view


# ── 구매 확인 View ──


def _make_buy_confirm_view(
    member: discord.Member,
    nickname: str,
    product_name: str,
    product_cost: int,
    points: int,
) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=180)
    member_id = member.id

    container = discord.ui.Container(accent_colour=discord.Colour.blurple())
    container.add_item(
        discord.ui.TextDisplay(
            f"## 🛒 구매 확인\n\n"
            f"**{nickname}**님, **{product_name}**을(를) 구매할까요?\n\n"
            f"상품 가격: **{product_cost}P**\n"
            f"보유 포인트: **{points}P**"
        )
    )
    view.add_item(container)

    row = discord.ui.ActionRow()
    confirm_btn = discord.ui.Button(
        label="구매하기", style=discord.ButtonStyle.success
    )
    cancel_btn = discord.ui.Button(
        label="취소", style=discord.ButtonStyle.secondary
    )

    async def on_confirm(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        await btn_interaction.response.edit_message(
            view=_loading_view("구매를 처리하고 있어요...")
        )
        await _handle_buy_confirm(btn_interaction, member, product_name)

    async def on_cancel(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        await btn_interaction.response.edit_message(
            view=_view("🚫 구매가 취소되었어요.", discord.Colour.greyple())
        )

    confirm_btn.callback = on_confirm
    cancel_btn.callback = on_cancel
    row.add_item(confirm_btn)
    row.add_item(cancel_btn)
    view.add_item(row)

    return view


# ── 구매 실행 ──


async def _handle_buy_confirm(
    interaction: discord.Interaction,
    member: discord.Member,
    product_name: str,
) -> None:
    nickname = _get_nickname(member)

    try:
        result = await buy_product(member.id, product_name)
    except Exception:
        log.exception("[구매] 예상치 못한 오류")
        await interaction.edit_original_response(
            view=_error_view("구매 처리 중 오류가 발생했어요.\n다시 시도해 주세요.")
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

    if result is None or result[0] in error_map:
        error_msg = error_map.get(result[0], "알 수 없는 오류가 발생했어요.") if result else "알 수 없는 오류가 발생했어요."
        await interaction.edit_original_response(
            view=_error_view(error_msg)
        )
        return

    coupon_code, remaining_points = result
    await interaction.edit_original_response(
        view=_view(
            f"## ✅ 구매 완료\n\n"
            f"**{nickname}**님의 **{product_name}** 쿠폰이 발급되었어요.\n"
            f"# {coupon_code}\n\n"
            f"잔여 포인트: **{remaining_points}P**",
            discord.Colour.green(),
        )
    )


# ── 대시보드 자동 전송 ──


class _DashboardManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ensure_dashboard(self) -> None:
        cfg = get_config()
        channel = self.bot.get_channel(cfg.DASHBOARD_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            log.warning("대시보드 채널을 찾을 수 없습니다 (ID: %s)", cfg.DASHBOARD_CHANNEL_ID)
            return

        try:
            products = await fetch_product()
        except Exception:
            log.exception("상품 목록 조회 실패")
            return

        view = DashboardView(products=products)

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.edit(view=view)
                log.info("기존 대시보드 갱신 완료")
                return

        await channel.send(view=view)
        log.info("대시보드 자동 전송 완료")


async def setup(bot: commands.Bot) -> None:
    bot.add_view(DashboardView())
    cog = _DashboardManager(bot)
    await bot.add_cog(cog)
    await cog.ensure_dashboard()
