from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any

from utils.repository import (
    AvailableCoupon,
    CouponRow,
    DataRepository,
    NicknameMismatchError,
    PointRow,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
STORE_FILE = os.path.join(DATA_DIR, "store.json")

KST = timezone(timedelta(hours=9))


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


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
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def _to_kst_string() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


class JsonRepository(DataRepository):
    # ── 포인트 (users.json) ──

    def _find_user_pk_by_discord_id(self, discord_id: str) -> int | None:
        """Discord user ID → users.id (PK) 변환"""
        data = _read_json(USERS_FILE)
        for row in data:
            if row.get("user_id") == discord_id:
                return int(row["id"])
        return None

    def get_point_by_user(self, nickname: str, user_id: str) -> PointRow | None:
        data = _read_json(USERS_FILE)
        for i, row in enumerate(data):
            if row.get("user_id") == user_id:
                row_name = (row.get("user_name") or "").strip()
                if row_name != nickname:
                    raise NicknameMismatchError(row_name, nickname)
                return PointRow(
                    row_index=i,
                    nickname=row_name,
                    points=int(row.get("user_point") or 0),
                )
        return None

    def deduct_points(self, row_index: int, current_points: int, amount: int) -> None:
        data = _read_json(USERS_FILE)
        if row_index < 0 or row_index >= len(data):
            raise IndexError(f"유효하지 않은 사용자 인덱스: {row_index}")
        actual = int(data[row_index].get("user_point", 0))
        if actual != current_points:
            raise ValueError(
                f"포인트 불일치: expected={current_points}, actual={actual}"
            )
        if actual < amount:
            raise ValueError(f"포인트 부족: have={actual}, need={amount}")
        data[row_index]["user_point"] = actual - amount
        data[row_index]["updated_at"] = _to_kst_string()
        _write_json(USERS_FILE, data)

    def restore_points(self, row_index: int, current_points: int, amount: int) -> None:
        data = _read_json(USERS_FILE)
        if row_index < 0 or row_index >= len(data):
            raise IndexError(f"유효하지 않은 사용자 인덱스: {row_index}")
        data[row_index]["user_point"] = current_points + amount
        data[row_index]["updated_at"] = _to_kst_string()
        _write_json(USERS_FILE, data)

    # ── 쿠폰 (store.json — user_id는 users.id FK) ──

    def get_coupon_by_user_id(self, discord_user_id: str) -> CouponRow | None:
        pk = self._find_user_pk_by_discord_id(discord_user_id)
        if pk is None:
            return None
        data = _read_json(STORE_FILE)
        for row in data:
            if row.get("user_id") == pk:
                return CouponRow(
                    coupon_code=row.get("store_product") or "",
                    assigned_at=row.get("updated_at") or "",
                )
        return None

    def find_available_coupon(self) -> AvailableCoupon | None:
        data = _read_json(STORE_FILE)
        for row in data:
            if row.get("user_id") is None:
                return AvailableCoupon(
                    coupon_code=row.get("store_product") or "",
                )
        return None

    def assign_coupon(self, coupon_code: str, discord_user_id: str) -> None:
        pk = self._find_user_pk_by_discord_id(discord_user_id)
        if pk is None:
            raise ValueError(f"사용자를 찾을 수 없음: discord_user_id={discord_user_id}")
        data = _read_json(STORE_FILE)
        now = _to_kst_string()
        for row in data:
            if row.get("store_product") == coupon_code and row.get("user_id") is None:
                row["user_id"] = pk
                row["updated_at"] = now
                _write_json(STORE_FILE, data)
                return
        raise ValueError(f"할당 가능한 쿠폰을 찾을 수 없음: {coupon_code}")
