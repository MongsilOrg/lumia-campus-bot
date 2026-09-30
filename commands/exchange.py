from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import escape_markdown

from utils.config import get_config
from utils.views import (
    ExpiringLayoutView,
    view as _view,
    loading_view as _loading_view,
    error_view as _error_view,
    info_view as _info_view,
)
from repository.point_repository import fetch_point
from repository.product_repository import (
    fetch_product,
    fetch_products_with_stock,
    buy_product,
    fetch_user_coupon,
)
from repository.log_repository import get_log
from view.pagination_view import PaginationView, build_purchase_lines

log = logging.getLogger("lumia-campus-bot.exchange")

REQUIRED_ROLES = {"학생회", "학부생", "재학생", "신입생"}

_DASHBOARD_ID_PATH = Path(__file__).resolve().parent.parent / "data" / "dashboard_message.json"

# RPC 오류는 한글 문장, 쿠폰 코드는 공백 없는 영숫자
_COUPON_CODE = re.compile(r"[A-Za-z0-9_-]{4,64}")

_BUY_ERRORS = {
    "주문하신 상품은 존재하지 않습니다 관리자에게 문의 주세요":
        "상품을 찾을 수 없습니다.\n관리자에게 문의해주세요.",
    "포인트가 부족합니다.":
        "포인트가 부족합니다.",
    "재고가 없습니다 관리자에게 문의 주세요":
        "재고가 없습니다.\n관리자에게 문의해주세요.",
}
_ALREADY_BOUGHT = "이미 구매하신 상품입니다."


# ── 유틸 ──


def _get_nickname(member: discord.Member) -> str:
    return member.nick or member.global_name or member.name


def _has_required_role(member: discord.Member) -> bool:
    return any(role.name in REQUIRED_ROLES for role in member.roles)


def is_coupon_code(value) -> bool:
    return isinstance(value, str) and _COUPON_CODE.fullmatch(value) is not None


async def product_name_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    try:
        products = await fetch_product()
    except Exception:
        log.exception("[자동완성] 상품 목록 조회 실패")
        return []
    keyword = current.strip().lower()
    return [
        app_commands.Choice(name=name, value=name)
        for name, _cost, _image in products
        if keyword in name.lower()
    ][:25]


def _coupon_view(
    heading: str, message: str, code: str, points, colour: discord.Colour
) -> discord.ui.LayoutView:
    return _view(
        f"## {heading}\n\n{message}\n# {code}\n\n잔여 포인트: **{points}P**",
        colour,
    )


async def purchase_result_view(
    member: discord.Member, product_name: str, result
) -> tuple[discord.ui.LayoutView, bool]:
    """buy_product 결과를 화면으로 바꾼다. 두 번째 값은 새로 구매했는지 여부."""
    nickname = escape_markdown(_get_nickname(member))
    product = escape_markdown(product_name)
    status = result[0] if result else None
    points = result[1] if result else None

    if status == _ALREADY_BOUGHT:
        try:
            code = await fetch_user_coupon(member.id, product_name)
        except Exception:
            log.exception("[구매] 기존 쿠폰 조회 실패: user=%s product=%s", member.id, product_name)
            code = None
        if not code:
            return _error_view(
                "이미 구매한 상품이지만 쿠폰을 불러오지 못했습니다.\n구매내역에서 확인해주세요."
            ), False
        return _coupon_view(
            "🎟️ 쿠폰 확인",
            f"**{nickname}**님, 이미 구매한 **{product}** 쿠폰입니다.",
            code,
            points,
            discord.Colour.blue(),
        ), False

    if status in _BUY_ERRORS:
        return _error_view(_BUY_ERRORS[status]), False

    if not is_coupon_code(status):
        log.error("[구매] 예상치 못한 RPC 결과: user=%s product=%s result=%r", member.id, product_name, result)
        return _error_view(
            "구매 결과를 확인하지 못했습니다.\n구매내역을 확인하고 관리자에게 문의해주세요."
        ), False

    log.info("[구매] 완료: user=%s product=%s 잔여=%sP", member.id, product_name, points)
    return _coupon_view(
        "✅ 구매 완료",
        f"**{nickname}**님의 **{product}** 쿠폰이 발급되었습니다.",
        status,
        points,
        discord.Colour.green(),
    ), True


# ── 대시보드 (채널 상주, 영구) ──


class DashboardView(discord.ui.LayoutView):
    def __init__(self, products=None, stock=None):
        super().__init__(timeout=None)
        if products is not None:
            stock = stock or {}
            existing = list(self.children)
            self.clear_items()

            container = discord.ui.Container(accent_colour=discord.Colour.blurple())
            container.add_item(
                discord.ui.TextDisplay(
                    "# 🏪 루미아 교환소\n"
                    "-# 루미아 캠퍼스"
                )
            )
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, visible=True))
            for name, cost, image in products:
                qty = stock.get(name, 0)
                if qty == 0:
                    stock_text = "-# ⚠️ 품절"
                    text = discord.ui.TextDisplay(f"~~**{name}**~~ ~~{cost}P~~\n{stock_text}")
                else:
                    stock_text = f"-# 재고 {qty}개"
                    text = discord.ui.TextDisplay(f"**{name}** {cost}P\n{stock_text}")
                if image:
                    container.add_item(
                        discord.ui.Section(
                            text,
                            accessory=discord.ui.Thumbnail(image),
                        )
                    )
                else:
                    container.add_item(text)
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small, visible=True))
            container.add_item(
                discord.ui.TextDisplay(
                    "아래 버튼을 눌러 포인트 조회 또는 상품 구매를 시작해 보세요."
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

    @row.button(
        label="🎟️ 구매내역",
        custom_id="dashboard:my_purchases",
        style=discord.ButtonStyle.secondary,
    )
    async def my_purchases_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await _handle_my_purchases(interaction)


# ── 포인트 조회 ──


async def _handle_point_check(interaction: discord.Interaction) -> None:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.followup.send(
            view=_error_view("서버 멤버 정보를 확인할 수 없어요."), ephemeral=True
        )
        return

    try:
        points = await fetch_point(member.id)
    except Exception:
        log.exception("[포인트 조회] 데이터 조회 실패")
        await interaction.followup.send(
            view=_error_view("포인트 조회 중 오류가 발생했어요.\n다시 시도해 주세요."), ephemeral=True
        )
        return

    if points is None:
        await interaction.followup.send(
            view=_error_view(
                "등록되지 않은 유저입니다.\n관리자에게 문의해주세요."
            ),
            ephemeral=True,
        )
        return

    nickname = escape_markdown(_get_nickname(member))
    await interaction.followup.send(
        view=_view(
            f"## 📊 포인트 조회\n\n"
            f"**{nickname}**님의 보유 포인트\n"
            f"# {points}P",
            discord.Colour.blue(),
        ),
        ephemeral=True,
    )


# ── 구매내역 조회 ──


async def _handle_my_purchases(interaction: discord.Interaction) -> None:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.followup.send(
            view=_error_view("서버 멤버 정보를 확인할 수 없어요."), ephemeral=True
        )
        return

    try:
        result, count = await get_log(member.id)
    except Exception:
        log.exception("[구매내역] 데이터 조회 실패")
        await interaction.followup.send(
            view=_error_view("구매내역 조회 중 오류가 발생했어요.\n다시 시도해 주세요."), ephemeral=True
        )
        return

    if not result:
        await interaction.followup.send(
            view=_info_view("구매내역이 없습니다."), ephemeral=True
        )
        return

    total_pages = max(1, (count + 19) // 20)
    pagination_view = PaginationView(
        member.id, _get_nickname(member), 1, total_pages, build_purchase_lines(result, 1)
    )
    pagination_view.message = await interaction.followup.send(view=pagination_view, ephemeral=True)


# ── 상품 구매 시작 ──


async def _handle_buy_start(interaction: discord.Interaction) -> None:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
    except discord.NotFound:
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.followup.send(
            view=_error_view("서버 멤버 정보를 확인할 수 없어요."), ephemeral=True
        )
        return

    if not _has_required_role(member):
        await interaction.followup.send(
            view=_error_view(
                "구매 권한이 없어요.\n"
                "학생회, 학부생, 재학생, 신입생 역할이 필요해요."
            ),
            ephemeral=True,
        )
        return

    try:
        (products, stock), points = await asyncio.gather(
            fetch_products_with_stock(), fetch_point(member.id)
        )
    except Exception:
        log.exception("[구매] 데이터 조회 실패")
        await interaction.followup.send(
            view=_error_view("상품 및 포인트 조회 중 오류가 발생했어요.\n다시 시도해 주세요."), ephemeral=True
        )
        return

    if points is None:
        await interaction.followup.send(
            view=_error_view(
                "등록되지 않은 유저입니다.\n관리자에게 문의해주세요."
            ),
            ephemeral=True,
        )
        return

    if not products:
        await interaction.followup.send(
            view=_error_view("현재 구매 가능한 상품이 없어요."), ephemeral=True
        )
        return

    select_view = _make_product_select_view(member, products, points, stock)
    select_view.message = await interaction.followup.send(view=select_view, ephemeral=True)


# ── 상품 선택 View ──


def _make_product_select_view(
    member: discord.Member, products: list, points: int, stock: dict
) -> discord.ui.LayoutView:
    view = ExpiringLayoutView(timeout=180)
    member_id = member.id
    nickname = escape_markdown(_get_nickname(member))

    container = discord.ui.Container(accent_colour=discord.Colour.blurple())
    container.add_item(
        discord.ui.TextDisplay(
            f"## 🛒 상품 구매\n\n"
            f"**{nickname}**님, 구매할 상품을 선택해 주세요.\n"
            f"보유 포인트: **{points}P**"
        )
    )

    row = discord.ui.ActionRow()
    options = []
    for name, cost, _image in products:
        qty = stock.get(name, 0)
        desc = f"{cost}P, 품절" if qty == 0 else f"{cost}P, 재고 {qty}개"
        options.append(discord.SelectOption(label=name, description=desc, value=name))
    select = discord.ui.Select(placeholder="상품을 선택해 주세요", options=options)

    async def on_select(select_interaction: discord.Interaction):
        if select_interaction.user.id != member_id:
            return
        selected_name = select.values[0]
        selected_qty = stock.get(selected_name, 0)
        if selected_qty == 0:
            await select_interaction.response.send_message(
                view=_error_view("품절된 상품이에요. 다른 상품을 선택해 주세요."),
                ephemeral=True,
            )
            return
        selected_cost = next(
            cost for name, cost, _img in products if name == selected_name
        )
        view.stop()
        confirm_view = _make_buy_confirm_view(
            member, nickname, selected_name, selected_cost, points
        )
        confirm_view.message = view.message
        if not select_interaction.response.is_done():
            await select_interaction.response.edit_message(view=confirm_view)
        else:
            await select_interaction.edit_original_response(view=confirm_view)

    select.callback = on_select
    row.add_item(select)
    container.add_item(row)
    view.add_item(container)

    return view


# ── 구매 확인 View ──


def _make_buy_confirm_view(
    member: discord.Member,
    nickname: str,
    product_name: str,
    product_cost: int,
    points: int,
) -> discord.ui.LayoutView:
    view = ExpiringLayoutView(timeout=180)
    member_id = member.id
    insufficient = points < product_cost

    text = (
        f"## 🛒 구매 확인\n\n"
        f"**{nickname}**님, 아래 상품을 구매할까요?\n\n"
        f"상품: **{escape_markdown(product_name)}**\n"
        f"상품 가격: **{product_cost}P**\n"
        f"보유 포인트: **{points}P**"
    )
    if insufficient:
        text += "\n-# ⚠️ 포인트가 부족해요"

    container = discord.ui.Container(accent_colour=discord.Colour.blurple())
    container.add_item(discord.ui.TextDisplay(text))

    row = discord.ui.ActionRow()
    confirm_btn = discord.ui.Button(
        label="구매하기", style=discord.ButtonStyle.success, disabled=insufficient
    )
    cancel_btn = discord.ui.Button(
        label="취소", style=discord.ButtonStyle.secondary
    )

    async def on_confirm(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        if not btn_interaction.response.is_done():
            await btn_interaction.response.edit_message(
                view=_loading_view("구매를 처리하고 있습니다.")
            )
        else:
            await btn_interaction.edit_original_response(
                view=_loading_view("구매를 처리하고 있습니다.")
            )
        await _handle_buy_confirm(btn_interaction, member, product_name)

    async def on_cancel(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        if not btn_interaction.response.is_done():
            await btn_interaction.response.edit_message(
                view=_view("🚫 구매가 취소되었어요.", discord.Colour.greyple())
            )
        else:
            await btn_interaction.edit_original_response(
                view=_view("🚫 구매가 취소되었어요.", discord.Colour.greyple())
            )

    confirm_btn.callback = on_confirm
    cancel_btn.callback = on_cancel
    row.add_item(confirm_btn)
    row.add_item(cancel_btn)
    container.add_item(row)
    view.add_item(container)

    return view


# ── 구매 실행 ──


async def _handle_buy_confirm(
    interaction: discord.Interaction,
    member: discord.Member,
    product_name: str,
) -> None:
    try:
        result = await buy_product(member.id, product_name)
    except Exception:
        log.exception("[구매] 예상치 못한 오류")
        await interaction.edit_original_response(
            view=_error_view("구매 처리 중 오류가 발생했어요.\n다시 시도해 주세요.")
        )
        return

    result_view, purchased = await purchase_result_view(member, product_name, result)
    await interaction.edit_original_response(view=result_view)
    if purchased:
        await refresh_dashboard(interaction.client)


# ── 대시보드 갱신 헬퍼 (다른 Cog에서 import 가능) ──


async def refresh_dashboard(bot: commands.Bot) -> None:
    cog = bot.get_cog("_DashboardManager")
    if cog is not None:
        await cog.ensure_dashboard()


# ── 대시보드 자동 전송 ──


def _load_dashboard_id() -> int | None:
    try:
        return int(json.loads(_DASHBOARD_ID_PATH.read_text(encoding="utf-8"))["message_id"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _save_dashboard_id(message_id: int) -> None:
    try:
        _DASHBOARD_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DASHBOARD_ID_PATH.write_text(json.dumps({"message_id": message_id}), encoding="utf-8")
    except OSError:
        log.warning("대시보드 메시지 ID 저장 실패", exc_info=True)


class _DashboardManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        self._pending = False

    async def ensure_dashboard(self) -> None:
        """대시보드를 갱신한다. 갱신 중에 들어온 요청은 끝난 뒤 한 번으로 합친다."""
        if self._lock.locked():
            self._pending = True
            return
        async with self._lock:
            self._pending = True
            while self._pending:
                self._pending = False
                try:
                    await self._render()
                except Exception:
                    log.exception("대시보드 갱신 실패")

    async def _render(self) -> None:
        cfg = get_config()
        channel = self.bot.get_channel(cfg.DASHBOARD_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            log.warning("대시보드 채널을 찾을 수 없습니다 (ID: %s)", cfg.DASHBOARD_CHANNEL_ID)
            return

        products, stock = await fetch_products_with_stock()
        view = DashboardView(products=products, stock=stock)

        message_id = _load_dashboard_id()
        if message_id:
            try:
                await channel.get_partial_message(message_id).edit(view=view)
                log.info("기존 대시보드 갱신 완료")
                return
            except discord.NotFound:
                log.warning("저장된 대시보드 메시지가 없어 채널에서 다시 찾음")

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.edit(view=view)
                _save_dashboard_id(msg.id)
                log.info("기존 대시보드 갱신 완료")
                return

        msg = await channel.send(view=view)
        _save_dashboard_id(msg.id)
        log.info("대시보드 자동 전송 완료")


async def setup(bot: commands.Bot) -> None:
    bot.add_view(DashboardView())
    cog = _DashboardManager(bot)
    await bot.add_cog(cog)
    await cog.ensure_dashboard()
