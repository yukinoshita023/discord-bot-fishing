import discord
from features.firebase_client import get_fishing_bait
from features.fish_data import FISHING_BAIT_SHOP


async def setup(bot):
    @bot.tree.command(name="fishing_bait", description="保有している釣り餌（青・緑・赤）を確認する")
    async def fishing_bait(interaction: discord.Interaction):
        bait = get_fishing_bait(str(interaction.user.id))

        lines = ["**🎣 釣り餌の保有数**\n"]
        for key, info in FISHING_BAIT_SHOP.items():
            lines.append(f"{info['name']}: {bait[key]}個")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
