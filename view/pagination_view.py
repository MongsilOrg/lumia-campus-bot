import discord
from repository.log_repository import get_log


def build_table(result, page, page_size=20):
    table = f"{'번호':<5} | {'상품명':<10} | {'쿠폰번호':<15}\n"
    table += "-" * 35 + "\n"
    for i, item in enumerate(result, start=(page - 1) * page_size + 1):
        table += f"{i:<6} | {item[0]:<11} | {item[1]:<15}\n"
    return table


class PaginationView(discord.ui.LayoutView):
    def __init__(self, user_id, current_page, total_pages, table_text=""):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.page = current_page
        self.total = total_pages

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        container.add_item(discord.ui.TextDisplay(
            f"## 📋 구매 이력\n"
            f"```\n{table_text}```\n"
            f"-# 페이지 {current_page} / {total_pages}"
        ))
        self.add_item(container)

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

        async def on_prev(interaction: discord.Interaction):
            if self.page > 1:
                self.page -= 1
                await self._update(interaction)

        async def on_next(interaction: discord.Interaction):
            if self.page < self.total:
                self.page += 1
                await self._update(interaction)

        prev_btn.callback = on_prev
        next_btn.callback = on_next
        row.add_item(prev_btn)
        row.add_item(next_btn)
        self.add_item(row)

    async def _update(self, interaction: discord.Interaction):
        result, _ = await get_log(self.user_id, page=self.page)
        table_text = build_table(result, self.page)
        new_view = PaginationView(self.user_id, self.page, self.total, table_text)
        await interaction.response.edit_message(view=new_view)
