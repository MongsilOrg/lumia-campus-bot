import logging

import discord
from discord.utils import escape_markdown

from repository.log_repository import get_log, get_product_log
from utils.views import ExpiringLayoutView, send_error

log = logging.getLogger("lumia-campus-bot.pagination")


def build_purchase_lines(result, page, page_size=20):
    start = (page - 1) * page_size + 1
    return "\n".join(
        f"{i}. **{escape_markdown(name)}** `{code}`"
        for i, (name, code) in enumerate(result, start=start)
    )


def build_buyer_lines(result, page, page_size=20):
    start = (page - 1) * page_size + 1
    return "\n".join(
        f"{i}. {escape_markdown(item[0])}" for i, item in enumerate(result, start=start)
    )


def _page_buttons(current_page, total_pages, on_prev, on_next) -> discord.ui.ActionRow:
    row = discord.ui.ActionRow()
    prev_btn = discord.ui.Button(
        label="이전",
        style=discord.ButtonStyle.primary,
        disabled=(current_page <= 1),
    )
    next_btn = discord.ui.Button(
        label="다음",
        style=discord.ButtonStyle.primary,
        disabled=(current_page >= total_pages),
    )
    prev_btn.callback = on_prev
    next_btn.callback = on_next
    row.add_item(prev_btn)
    row.add_item(next_btn)
    return row


class PaginationView(ExpiringLayoutView):
    def __init__(self, user_id, owner_name, current_page, total_pages, lines=""):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.owner_name = owner_name
        self.page = current_page
        self.total = total_pages

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        container.add_item(discord.ui.TextDisplay(
            f"## 📋 {escape_markdown(owner_name)}님의 구매 이력\n"
            f"{lines}\n"
            f"-# 페이지 {current_page} / {total_pages}"
        ))

        async def on_prev(interaction: discord.Interaction):
            if self.page > 1:
                self.page -= 1
                await self._update(interaction)

        async def on_next(interaction: discord.Interaction):
            if self.page < self.total:
                self.page += 1
                await self._update(interaction)

        container.add_item(_page_buttons(current_page, total_pages, on_prev, on_next))
        self.add_item(container)

    async def _update(self, interaction: discord.Interaction):
        result, _ = await get_log(self.user_id, page=self.page)
        new_view = PaginationView(
            self.user_id, self.owner_name, self.page, self.total, build_purchase_lines(result, self.page)
        )
        new_view.message = self.message
        self.stop()
        await interaction.response.edit_message(view=new_view)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        log.error("[구매이력] 페이지 이동 실패: user=%s", self.user_id, exc_info=error)
        await send_error(interaction)


class ProductPaginationView(ExpiringLayoutView):
    def __init__(self, product_name, current_page, total_pages, lines=""):
        super().__init__(timeout=60)
        self.product_name = product_name
        self.page = current_page
        self.total = total_pages
        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        container.add_item(discord.ui.TextDisplay(
            f"## 📋 {escape_markdown(product_name)} 구매자 목록\n"
            f"{lines}\n"
            f"-# 페이지 {current_page} / {total_pages}"
        ))

        async def on_prev(interaction: discord.Interaction):
            if self.page > 1:
                self.page -= 1
                await self._update(interaction)

        async def on_next(interaction: discord.Interaction):
            if self.page < self.total:
                self.page += 1
                await self._update(interaction)

        container.add_item(_page_buttons(current_page, total_pages, on_prev, on_next))
        self.add_item(container)

    async def _update(self, interaction: discord.Interaction):
        result, count = await get_product_log(self.product_name, page=self.page)
        total_pages = max(1, (count + 19) // 20)
        new_view = ProductPaginationView(
            self.product_name, self.page, total_pages, build_buyer_lines(result, self.page)
        )
        new_view.message = self.message
        self.stop()
        await interaction.response.edit_message(view=new_view)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        log.error("[상품별 이력] 페이지 이동 실패: product=%s", self.product_name, exc_info=error)
        await send_error(interaction)
