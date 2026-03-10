from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands

from utils.config import get_config
from utils.data import (
    NicknameMismatchError,
    UserIdNotRegisteredError,
    assign_coupon,
    deduct_points,
    find_available_coupon,
    get_coupon_by_user_id,
    get_point_by_user,
    log_coupon_claim,
    restore_points,
)

log = logging.getLogger(__name__)

COUPON_COST = 100
REQUIRED_ROLES = {"학생회", "학부생", "재학생", "신입생"}

_exchange_lock = asyncio.Lock()

ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "profile-icon.webp"
)


# ── 유틸 ──


def _get_nickname(member: discord.Member) -> str:
    return member.nick or member.global_name or member.name


def _has_required_role(member: discord.Member) -> bool:
    return any(role.name in REQUIRED_ROLES for role in member.roles)


def _loading_view(text: str) -> discord.ui.LayoutView:
    """즉시 표시할 로딩 상태 뷰"""
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.TextDisplay(f"⏳ {text}"))
    return view


def _error_view(text: str) -> discord.ui.LayoutView:
    """에러 메시지 뷰"""
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=discord.Colour.red())
    container.add_item(discord.ui.TextDisplay(f"❌ {text}"))
    view.add_item(container)
    return view


# ── 대시보드 (채널 상주, 영구) ──


class DashboardView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    container = discord.ui.Container["DashboardView"](
        discord.ui.Section["DashboardView"](
            discord.ui.TextDisplay["DashboardView"](
                "# 🎓 프로필 아이콘 교환\n"
                "-# 2025 루미아 캠퍼스\n\n"
                "프로필 아이콘을 **100P**로 교환할 수 있습니다.\n"
                "아래 버튼을 눌러 포인트 조회 또는 교환을 시작하세요."
            ),
            accessory=discord.ui.Thumbnail["DashboardView"](
                "attachment://profile-icon.webp"
            ),
        ),
        accent_colour=discord.Colour.blurple(),
    )

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
        label="🎁 교환하기",
        custom_id="dashboard:exchange",
        style=discord.ButtonStyle.primary,
    )
    async def exchange_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await _handle_exchange_start(interaction)


# ── 포인트 조회 ──


async def _handle_point_check(interaction: discord.Interaction) -> None:
    # 즉시 로딩 메시지
    await interaction.response.send_message(
        view=_loading_view("포인트를 조회하고 있어요..."), ephemeral=True
    )

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.edit_original_response(
            view=_error_view("서버 멤버 정보를 가져올 수 없습니다.")
        )
        return

    nickname = _get_nickname(member)

    try:
        point_row = get_point_by_user(nickname, str(member.id))
    except NicknameMismatchError:
        await interaction.edit_original_response(
            view=_error_view("닉네임이 일치하지 않습니다.\n관리자에게 문의하세요.")
        )
        return
    except UserIdNotRegisteredError:
        await interaction.edit_original_response(
            view=_error_view(
                "Discord User ID가 등록되지 않았습니다.\n관리자에게 문의하세요."
            )
        )
        return
    except Exception:
        log.exception("[포인트 조회] 데이터 조회 실패")
        await interaction.edit_original_response(
            view=_error_view("포인트 조회 중 오류가 발생했습니다.")
        )
        return

    if not point_row:
        await interaction.edit_original_response(
            view=_error_view(
                "등록되지 않은 사용자입니다.\n관리자에게 문의하세요."
            )
        )
        return

    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=discord.Colour.blue())
    container.add_item(
        discord.ui.TextDisplay(
            f"## 📊 포인트 조회\n\n"
            f"**{point_row.nickname}**님의 보유 포인트\n"
            f"# {point_row.points}P"
        )
    )
    view.add_item(container)
    await interaction.edit_original_response(view=view)


# ── 교환 시작 ──


async def _handle_exchange_start(interaction: discord.Interaction) -> None:
    # 즉시 로딩 메시지
    await interaction.response.send_message(
        view=_loading_view("정보를 확인하고 있어요..."), ephemeral=True
    )

    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.edit_original_response(
            view=_error_view("서버 멤버 정보를 가져올 수 없습니다.")
        )
        return

    if not _has_required_role(member):
        await interaction.edit_original_response(
            view=_error_view(
                "교환 권한이 없습니다.\n(학생회/학부생/재학생/신입생 역할 필요)"
            )
        )
        return

    nickname = _get_nickname(member)
    user_id = str(member.id)

    try:
        existing = get_coupon_by_user_id(user_id)
    except Exception:
        log.exception("[교환] 기존 쿠폰 조회 실패")
        await interaction.edit_original_response(
            view=_error_view("쿠폰 조회 중 오류가 발생했습니다.")
        )
        return

    if existing:
        view = discord.ui.LayoutView()
        container = discord.ui.Container(accent_colour=discord.Colour.gold())
        container.add_item(
            discord.ui.TextDisplay(
                f"## 🎫 이미 발급된 쿠폰\n\n"
                f"쿠폰 코드: **{existing.coupon_code}**\n"
                f"발급 일시: {existing.assigned_at}"
            )
        )
        view.add_item(container)
        await interaction.edit_original_response(view=view)
        return

    try:
        point_row = get_point_by_user(nickname, user_id)
    except NicknameMismatchError:
        await interaction.edit_original_response(
            view=_error_view("닉네임이 일치하지 않습니다.\n관리자에게 문의하세요.")
        )
        return
    except UserIdNotRegisteredError:
        await interaction.edit_original_response(
            view=_error_view(
                "Discord User ID가 등록되지 않았습니다.\n관리자에게 문의하세요."
            )
        )
        return
    except Exception:
        log.exception("[교환] 포인트 조회 실패")
        await interaction.edit_original_response(
            view=_error_view("포인트 조회 중 오류가 발생했습니다.")
        )
        return

    if not point_row:
        await interaction.edit_original_response(
            view=_error_view(
                "등록되지 않은 사용자입니다.\n관리자에게 문의하세요."
            )
        )
        return

    if point_row.points < COUPON_COST:
        await interaction.edit_original_response(
            view=_error_view(
                f"포인트가 부족합니다.\n"
                f"필요: **{COUPON_COST}P** · 보유: **{point_row.points}P**"
            )
        )
        return

    # 확인 화면 표시
    confirm_view = _make_confirm_view(
        member, nickname, point_row.points, COUPON_COST
    )
    await interaction.edit_original_response(view=confirm_view)


# ── 교환 확인 View (동적 생성) ──


def _make_confirm_view(
    member: discord.Member, nickname: str, points: int, cost: int
) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=180)
    member_id = member.id

    # 안내 텍스트
    container = discord.ui.Container(accent_colour=discord.Colour.blurple())
    container.add_item(
        discord.ui.TextDisplay(
            f"## 🎁 프로필 아이콘 교환\n\n"
            f"**{nickname}**님, 프로필 아이콘을 교환하시겠습니까?\n\n"
            f"차감 포인트: **-{cost}P**\n"
            f"보유 → 잔여: **{points}P** → **{points - cost}P**"
        )
    )
    view.add_item(container)

    # 버튼
    row = discord.ui.ActionRow()
    confirm_btn = discord.ui.Button(
        label="✅ 교환하기", style=discord.ButtonStyle.success
    )
    cancel_btn = discord.ui.Button(
        label="취소", style=discord.ButtonStyle.secondary
    )

    async def on_confirm(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        # 즉시 처리 중 상태로 전환
        await btn_interaction.response.edit_message(
            view=_loading_view("교환 처리 중...")
        )
        await _handle_exchange_confirm(btn_interaction, member, nickname)

    async def on_cancel(btn_interaction: discord.Interaction):
        if btn_interaction.user.id != member_id:
            return
        view.stop()
        done = discord.ui.LayoutView()
        c = discord.ui.Container(accent_colour=discord.Colour.greyple())
        c.add_item(discord.ui.TextDisplay("교환이 취소되었습니다."))
        done.add_item(c)
        await btn_interaction.response.edit_message(view=done)

    confirm_btn.callback = on_confirm
    cancel_btn.callback = on_cancel
    row.add_item(confirm_btn)
    row.add_item(cancel_btn)
    view.add_item(row)

    return view


# ── 교환 실행 ──


async def _handle_exchange_confirm(
    interaction: discord.Interaction,
    member: discord.Member,
    nickname: str,
) -> None:
    user_id = str(member.id)

    try:
        async with _exchange_lock:
            existing = get_coupon_by_user_id(user_id)
            if existing:
                await interaction.edit_original_response(
                    view=_error_view("이미 쿠폰을 발급받았습니다.")
                )
                return

            if not _has_required_role(member):
                await interaction.edit_original_response(
                    view=_error_view("교환 권한이 없습니다.")
                )
                return

            try:
                point_row = get_point_by_user(nickname, user_id)
            except (NicknameMismatchError, UserIdNotRegisteredError) as e:
                await interaction.edit_original_response(
                    view=_error_view(str(e))
                )
                return

            if not point_row:
                await interaction.edit_original_response(
                    view=_error_view("등록되지 않은 사용자입니다.")
                )
                return

            if point_row.points < COUPON_COST:
                await interaction.edit_original_response(
                    view=_error_view(
                        f"포인트가 부족합니다.\n"
                        f"필요: **{COUPON_COST}P** · 보유: **{point_row.points}P**"
                    )
                )
                return

            available = find_available_coupon()
            if not available:
                await interaction.edit_original_response(
                    view=_error_view("발급 가능한 쿠폰이 없습니다.")
                )
                return

            # 포인트 차감
            deduct_points(
                point_row.row_index, point_row.points, COUPON_COST
            )

            # 쿠폰 할당
            try:
                assign_coupon(available.row_index, user_id, nickname)
            except Exception:
                log.exception("[교환] 쿠폰 할당 실패, 포인트 복구 시도")
                try:
                    restore_points(
                        point_row.row_index,
                        point_row.points - COUPON_COST,
                        COUPON_COST,
                    )
                except Exception:
                    log.exception(
                        "[교환] 포인트 복구 실패 — userId=%s, row=%d",
                        user_id,
                        point_row.row_index,
                    )
                await interaction.edit_original_response(
                    view=_error_view(
                        "쿠폰 발급 중 오류가 발생했습니다.\n다시 시도해주세요."
                    )
                )
                return

            # 로그 기록 (실패해도 교환은 완료)
            try:
                log_coupon_claim(
                    user_id, nickname, available.coupon_code, COUPON_COST
                )
            except Exception:
                log.exception("[교환] 사용 내역 로그 실패")

    except Exception:
        log.exception("[교환] 예상치 못한 오류")
        await interaction.edit_original_response(
            view=_error_view(
                "교환 처리 중 오류가 발생했습니다.\n다시 시도해주세요."
            )
        )
        return

    # 성공
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=discord.Colour.green())
    container.add_item(
        discord.ui.TextDisplay(
            f"## ✅ 교환 완료!\n\n"
            f"**{nickname}**님의 프로필 아이콘 쿠폰\n"
            f"# {available.coupon_code}\n\n"
            f"차감: **-{COUPON_COST}P** · 잔여: **{point_row.points - COUPON_COST}P**"
        )
    )
    view.add_item(container)
    await interaction.edit_original_response(view=view)


# ── 대시보드 자동 전송 ──


class _DashboardManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._dashboard_sent = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._dashboard_sent:
            return
        self._dashboard_sent = True
        await self._ensure_dashboard()

    async def _ensure_dashboard(self) -> None:
        cfg = get_config()
        channel = self.bot.get_channel(cfg.DASHBOARD_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            log.warning("대시보드 채널을 찾을 수 없습니다 (ID: %s)", cfg.DASHBOARD_CHANNEL_ID)
            return

        # 채널에 봇이 보낸 대시보드가 이미 있으면 생략
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                log.info("기존 대시보드 발견, 전송 생략")
                return

        view = DashboardView()
        file = discord.File(ICON_PATH, filename="profile-icon.webp")
        await channel.send(view=view, file=file)
        log.info("대시보드 자동 전송 완료")


async def setup(bot: commands.Bot) -> None:
    bot.add_view(DashboardView())
    await bot.add_cog(_DashboardManager(bot))
