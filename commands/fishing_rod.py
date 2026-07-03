import discord
from features.firebase_client import get_fishing_rods
from features.fish_data import FISHING_ROD_SHOP


async def setup(bot):
    @bot.tree.command(name="fishing_rod", description="保有している釣り竿（青・緑・赤）を確認する")
    async def fishing_rod(interaction: discord.Interaction):
        rods = get_fishing_rods(str(interaction.user.id))

        lines = ["**🎣 釣り竿の所持状況**\n"]
        for key, info in FISHING_ROD_SHOP.items():
            status = "所持済み" if rods[key] else "未所持"
            lines.append(f"{info['name']}: {status}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
