from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import NamedTuple

import gspread
from google.oauth2.service_account import Credentials

from utils.config import get_config

# --- 시트 상수 ---

POINT_SHEET = "루미아 캠퍼스 포인트"
POINT_USAGE_SHEET = "포인트 사용 내역"
POINT_DATA_START = 7  # 0-indexed: row 0-5 = 설명, row 6 = 헤더, row 7+ = 데이터

COUPON_SHEET = "루미아캠퍼스 전용"

KST = timezone(timedelta(hours=9))

# --- 인증 ---

_gc: gspread.Client | None = None


def _get_client() -> gspread.Client:
    global _gc
    if _gc is None:
        cfg = get_config()
        creds = Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": cfg.GOOGLE_SHEETS_CLIENT_EMAIL,
                "private_key": cfg.GOOGLE_SHEETS_PRIVATE_KEY.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _gc = gspread.authorize(creds)
    return _gc


def _point_sheet() -> gspread.Spreadsheet:
    return _get_client().open_by_key(get_config().POINT_SPREADSHEET_ID)


def _coupon_sheet() -> gspread.Spreadsheet:
    return _get_client().open_by_key(get_config().COUPON_SPREADSHEET_ID)


# --- 데이터 타입 ---


class PointRow(NamedTuple):
    row_index: int  # 1-based (Google Sheets 행 번호)
    user_id: str
    nickname: str
    points: int


class CouponRow(NamedTuple):
    row_index: int
    coupon_code: str
    assigned_user_id: str
    assigned_nickname: str
    assigned_at: str


class AvailableCoupon(NamedTuple):
    row_index: int
    coupon_code: str


# --- 예외 ---


class NicknameMismatchError(Exception):
    def __init__(self, sheet_nickname: str, discord_nickname: str):
        self.sheet_nickname = sheet_nickname
        self.discord_nickname = discord_nickname
        super().__init__(
            f"닉네임 불일치: 시트=\"{sheet_nickname}\", 디스코드=\"{discord_nickname}\""
        )


class UserIdNotRegisteredError(Exception):
    def __init__(self, sheet_nickname: str):
        self.sheet_nickname = sheet_nickname
        super().__init__(f"User ID 미등록: 닉네임=\"{sheet_nickname}\"")


# --- 포인트 관리 ---
# 컬럼: A=빈칸, B=닉네임, C=Discord User ID, D=누적 포인트


async def get_point_by_user(nickname: str, user_id: str) -> PointRow | None:
    """포인트 시트에서 사용자 조회 (userId 우선, 닉네임 2차)"""
    ws = await asyncio.to_thread(
        lambda: _point_sheet().worksheet(POINT_SHEET)
    )
    rows = await asyncio.to_thread(ws.get_all_values)

    # 1차: userId로 검색
    if user_id:
        for i in range(POINT_DATA_START, len(rows)):
            row = rows[i]
            row_user_id = (row[2] if len(row) > 2 else "").strip()
            if row_user_id == user_id:
                row_nickname = (row[1] if len(row) > 1 else "").strip()
                if row_nickname != nickname:
                    raise NicknameMismatchError(row_nickname, nickname)
                points = int(row[3]) if len(row) > 3 and row[3] else 0
                return PointRow(
                    row_index=i + 1,
                    user_id=row_user_id,
                    nickname=row_nickname,
                    points=points,
                )

    # 2차: 닉네임으로 검색
    for i in range(POINT_DATA_START, len(rows)):
        row = rows[i]
        row_nickname = (row[1] if len(row) > 1 else "").strip()
        if row_nickname == nickname:
            row_user_id = (row[2] if len(row) > 2 else "").strip()
            if not row_user_id:
                raise UserIdNotRegisteredError(row_nickname)
            if user_id and row_user_id != user_id:
                continue
            points = int(row[3]) if len(row) > 3 and row[3] else 0
            return PointRow(
                row_index=i + 1,
                user_id=row_user_id,
                nickname=row_nickname,
                points=points,
            )

    return None


async def deduct_points(row_index: int, current_points: int, amount: int) -> None:
    """포인트 차감"""
    ws = await asyncio.to_thread(
        lambda: _point_sheet().worksheet(POINT_SHEET)
    )
    await asyncio.to_thread(
        ws.update_acell, f"D{row_index}", current_points - amount
    )


async def restore_points(row_index: int, current_points: int, amount: int) -> None:
    """포인트 복구 (쿠폰 할당 실패 시)"""
    ws = await asyncio.to_thread(
        lambda: _point_sheet().worksheet(POINT_SHEET)
    )
    await asyncio.to_thread(
        ws.update_acell, f"D{row_index}", current_points + amount
    )


# --- 쿠폰 관리 ---
# 컬럼: A=쿠폰 코드, B=일시, C=Discord User ID, D=닉네임, E=담당자, F=사유, G=비고


async def get_coupon_by_user_id(user_id: str) -> CouponRow | None:
    """기존 쿠폰 조회"""
    ws = await asyncio.to_thread(
        lambda: _coupon_sheet().worksheet(COUPON_SHEET)
    )
    rows = await asyncio.to_thread(ws.get_all_values)

    for i in range(1, len(rows)):  # row 0 = 헤더
        row = rows[i]
        if len(row) > 2 and row[2] == user_id:
            return CouponRow(
                row_index=i + 1,
                coupon_code=row[0] if row else "",
                assigned_user_id=row[2] if len(row) > 2 else "",
                assigned_nickname=row[3] if len(row) > 3 else "",
                assigned_at=row[1] if len(row) > 1 else "",
            )

    return None


async def find_available_coupon() -> AvailableCoupon | None:
    """미할당 쿠폰 찾기"""
    ws = await asyncio.to_thread(
        lambda: _coupon_sheet().worksheet(COUPON_SHEET)
    )
    rows = await asyncio.to_thread(ws.get_all_values)

    for i in range(1, len(rows)):
        row = rows[i]
        coupon_code = row[0] if row else ""
        user_id_cell = row[2] if len(row) > 2 else ""
        if coupon_code and not user_id_cell:
            return AvailableCoupon(row_index=i + 1, coupon_code=coupon_code)

    return None


async def assign_coupon(row_index: int, user_id: str, nickname: str) -> bool:
    """쿠폰 할당 + write-then-verify"""
    ws = await asyncio.to_thread(
        lambda: _coupon_sheet().worksheet(COUPON_SHEET)
    )
    now = _to_kst_string()

    # B=일시, C=Discord User ID, D=닉네임, E=담당자, F=사유
    await asyncio.to_thread(
        ws.update,
        f"B{row_index}:F{row_index}",
        [[now, user_id, nickname, "시스템", "유키 프로필 교환"]],
        raw=True,
    )

    # 검증: C열 재확인
    verify = await asyncio.to_thread(ws.acell, f"C{row_index}")
    return verify.value == user_id


async def log_coupon_claim(
    user_id: str, nickname: str, coupon_code: str, cost: int
) -> None:
    """포인트 사용 내역 시트에 기록"""
    ws = await asyncio.to_thread(
        lambda: _point_sheet().worksheet(POINT_USAGE_SHEET)
    )
    now = _to_kst_string()
    await asyncio.to_thread(
        ws.append_row,
        [now, user_id, nickname, str(cost), "유키 프로필", "시스템"],
        value_input_option="RAW",
        insert_data_option="INSERT_ROWS",
    )


# --- 유틸 ---


def _to_kst_string() -> str:
    now = datetime.now(KST)
    return now.strftime("%Y-%m-%d %H:%M:%S")
