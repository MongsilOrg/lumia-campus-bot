from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
POINTS_FILE = os.path.join(DATA_DIR, "points.json")
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.json")
USAGE_LOG_FILE = os.path.join(DATA_DIR, "usage_log.json")

KST = timezone(timedelta(hours=9))


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


# ── JSON 읽기/쓰기 (atomic write) ──


def _read_json(path: str) -> list[dict[str, Any]]:
    _ensure_data_dir()
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: list[dict[str, Any]]) -> None:
    _ensure_data_dir()
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


# ── 데이터 타입 ──


class PointRow(NamedTuple):
    row_index: int  # JSON 배열 인덱스
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


# ── 예외 ──


class NicknameMismatchError(Exception):
    def __init__(self, registered_nickname: str, discord_nickname: str):
        self.registered_nickname = registered_nickname
        self.discord_nickname = discord_nickname
        super().__init__(
            f"닉네임 불일치: 등록=\"{registered_nickname}\", 디스코드=\"{discord_nickname}\""
        )


class UserIdNotRegisteredError(Exception):
    def __init__(self, registered_nickname: str):
        self.registered_nickname = registered_nickname
        super().__init__(f"User ID 미등록: 닉네임=\"{registered_nickname}\"")


# ── 포인트 관리 ──


def get_point_by_user(nickname: str, user_id: str) -> PointRow | None:
    """포인트 조회 (userId 우선, 닉네임 2차)"""
    data = _read_json(POINTS_FILE)

    # 1차: userId로 검색
    if user_id:
        for i, row in enumerate(data):
            if row.get("user_id") == user_id:
                row_nickname = row.get("nickname", "").strip()
                if row_nickname != nickname:
                    raise NicknameMismatchError(row_nickname, nickname)
                return PointRow(
                    row_index=i,
                    user_id=row["user_id"],
                    nickname=row_nickname,
                    points=int(row.get("points", 0)),
                )

    # 2차: 닉네임으로 검색
    for i, row in enumerate(data):
        row_nickname = row.get("nickname", "").strip()
        if row_nickname == nickname:
            row_user_id = row.get("user_id", "").strip()
            if not row_user_id:
                raise UserIdNotRegisteredError(row_nickname)
            if user_id and row_user_id != user_id:
                continue
            return PointRow(
                row_index=i,
                user_id=row_user_id,
                nickname=row_nickname,
                points=int(row.get("points", 0)),
            )

    return None


def deduct_points(row_index: int, current_points: int, amount: int) -> None:
    """포인트 차감"""
    data = _read_json(POINTS_FILE)
    data[row_index]["points"] = current_points - amount
    _write_json(POINTS_FILE, data)


def restore_points(row_index: int, current_points: int, amount: int) -> None:
    """포인트 복구 (쿠폰 할당 실패 시)"""
    data = _read_json(POINTS_FILE)
    data[row_index]["points"] = current_points + amount
    _write_json(POINTS_FILE, data)


# ── 쿠폰 관리 ──


def get_coupon_by_user_id(user_id: str) -> CouponRow | None:
    """기존 쿠폰 조회"""
    data = _read_json(COUPONS_FILE)
    for i, row in enumerate(data):
        if row.get("user_id") == user_id:
            return CouponRow(
                row_index=i,
                coupon_code=row.get("code", ""),
                assigned_user_id=row.get("user_id", ""),
                assigned_nickname=row.get("nickname", ""),
                assigned_at=row.get("assigned_at", ""),
            )
    return None


def find_available_coupon() -> AvailableCoupon | None:
    """미할당 쿠폰 찾기"""
    data = _read_json(COUPONS_FILE)
    for i, row in enumerate(data):
        if row.get("code") and not row.get("user_id"):
            return AvailableCoupon(row_index=i, coupon_code=row["code"])
    return None


def assign_coupon(row_index: int, user_id: str, nickname: str) -> None:
    """쿠폰 할당"""
    data = _read_json(COUPONS_FILE)
    now = _to_kst_string()
    data[row_index].update(
        {
            "assigned_at": now,
            "user_id": user_id,
            "nickname": nickname,
            "manager": "시스템",
            "reason": "유키 프로필 교환",
        }
    )
    _write_json(COUPONS_FILE, data)


def log_coupon_claim(
    user_id: str, nickname: str, coupon_code: str, cost: int
) -> None:
    """포인트 사용 내역 기록"""
    data = _read_json(USAGE_LOG_FILE)
    now = _to_kst_string()
    data.append(
        {
            "timestamp": now,
            "user_id": user_id,
            "nickname": nickname,
            "points": cost,
            "item": "유키 프로필",
            "manager": "시스템",
        }
    )
    _write_json(USAGE_LOG_FILE, data)


# ── 유틸 ──


def _to_kst_string() -> str:
    now = datetime.now(KST)
    return now.strftime("%Y-%m-%d %H:%M:%S")
