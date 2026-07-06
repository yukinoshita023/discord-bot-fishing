import discord
from features.firebase_client import get_fishing_rods
from features.fish_data import FISHING_ROD_SHOP


async def setup(bot):
    @bot.tree.command(name="fishing_gear", description="保有している釣り竿を確認する")
    async def fishing_gear(interaction: discord.Interaction):
        rods = get_fishing_rods(str(interaction.user.id))

        lines = ["**🎣 釣り竿の所持状況**"]
        for key, info in FISHING_ROD_SHOP.items():
            status = "所持済み" if rods[key] else "未所持"
            lines.append(f"{info['name']}: {status}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
