import discord
from repository.log_repository import get_log

class PaginationView(discord.ui.View):
    def __init__(self, user_id, current_page, total_pages):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.page = current_page
        self.total = total_pages
        self.update_button_states()

    def update_button_states(self):
        self.prev.disabled = (self.page <= 1)
        self.next.disabled = (self.page >= self.total)
        
    async def update_view(self, interaction: discord.Interaction):
        result, _ = await get_log(self.user_id, page=self.page)
        self.update_button_states()
        
        table = f"{'번호':<5} | {'상품명':<10} | {'쿠폰번호':<15}\n" + "-" * 35 + "\n"
        for i, item in enumerate(result, start=(self.page - 1) * 20 + 1):
            table += f"{i:<6} | {item[0]:<11} | {item[1]:<15}\n"
        await interaction.response.edit_message(
            content=f"```\n{table}```\n페이지: {self.page} / {self.total}", 
            view=self
        )

    @discord.ui.button(label="이전", style=discord.ButtonStyle.primary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 1:
            self.page -= 1
            await self.update_view(interaction)
        else:
            self.update_button_states()
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="다음", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.total:
            self.page += 1
            await self.update_view(interaction)
        else:
            self.update_button_states()
            await interaction.response.edit_message(view=self)