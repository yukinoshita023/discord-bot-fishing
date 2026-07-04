import discord
from features.firebase_client import get_fishing_bait, get_fishing_rods
from features.fish_data import FISHING_BAIT_SHOP, FISHING_ROD_SHOP, ROD_DISPLAY_NAMES, STARTER_ROD


async def setup(bot):
    @bot.tree.command(name="fishing_gear", description="保有している釣り竿と釣り餌をまとめて確認する")
    async def fishing_gear(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        rods = get_fishing_rods(user_id)
        bait = get_fishing_bait(user_id)

        lines = ["**🎣 釣り竿の所持状況**", f"{ROD_DISPLAY_NAMES[STARTER_ROD]}: 所持済み（初期装備）"]
        for key, info in FISHING_ROD_SHOP.items():
            status = "所持済み" if rods[key] else "未所持"
            lines.append(f"{info['name']}: {status}")

        lines.append("")
        lines.append("**🐟 釣り餌の保有数**")
        for key, info in FISHING_BAIT_SHOP.items():
            lines.append(f"{info['name']}: {bait[key]}個")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
