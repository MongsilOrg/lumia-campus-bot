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
