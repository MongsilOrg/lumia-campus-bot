import discord


def view(text: str, colour: discord.Colour) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=colour)
    container.add_item(discord.ui.TextDisplay(text))
    v.add_item(container)
    return v


def error_view(text: str) -> discord.ui.LayoutView:
    return view(f"❌ {text}", discord.Colour.red())


def success_view(text: str) -> discord.ui.LayoutView:
    return view(f"✅ {text}", discord.Colour.green())


def warn_view(text: str) -> discord.ui.LayoutView:
    return view(f"⚠️ {text}", discord.Colour.yellow())


def info_view(text: str) -> discord.ui.LayoutView:
    return view(text, discord.Colour.blue())


def loading_view(text: str) -> discord.ui.LayoutView:
    return view(f"⏳ {text}", discord.Colour.light_grey())


async def send_error(
    interaction: discord.Interaction,
    text: str = "처리 중 오류가 발생했습니다.\n다시 시도해주세요.",
) -> None:
    v = error_view(text)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(view=v, ephemeral=True)
        else:
            await interaction.response.send_message(view=v, ephemeral=True)
    except discord.HTTPException:
        pass


class ExpiringLayoutView(discord.ui.LayoutView):
    """시간이 지나면 버튼을 비활성화하는 LayoutView. 보낸 뒤 message 지정 필요."""

    message: discord.Message | discord.WebhookMessage | None = None

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if hasattr(item, "disabled"):
                item.disabled = True
        if self.message is None:
            return
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
