from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple


# ── 데이터 타입 ──


class PointRow(NamedTuple):
    row_index: int
    nickname: str
    points: int


class CouponRow(NamedTuple):
    coupon_code: str
    assigned_at: str


class AvailableCoupon(NamedTuple):
    coupon_code: str


# ── 예외 ──


class NicknameMismatchError(Exception):
    def __init__(self, registered_nickname: str, discord_nickname: str):
        self.registered_nickname = registered_nickname
        self.discord_nickname = discord_nickname
        super().__init__(
            f"닉네임 불일치: 등록=\"{registered_nickname}\", 디스코드=\"{discord_nickname}\""
        )


# ── 추상 리포지토리 ──


class DataRepository(ABC):
    @abstractmethod
    def get_point_by_user(self, nickname: str, user_id: str) -> PointRow | None: ...

    @abstractmethod
    def deduct_points(self, row_index: int, current_points: int, amount: int) -> None: ...

    @abstractmethod
    def restore_points(self, row_index: int, current_points: int, amount: int) -> None: ...

    @abstractmethod
    def get_coupon_by_user_id(self, user_id: str) -> CouponRow | None: ...

    @abstractmethod
    def find_available_coupon(self) -> AvailableCoupon | None: ...

    @abstractmethod
    def assign_coupon(self, coupon_code: str, user_id: str) -> None: ...
