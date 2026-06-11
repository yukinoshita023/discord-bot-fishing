import discord
from features.firebase_client import get_points, get_bait, buy_bait
from features.fish_data import BAIT_TYPES


async def setup(bot):
    @bot.tree.command(name="bait", description="餌を購入する")
    @discord.app_commands.describe(type="購入する餌の種類", amount="個数（デフォルト: 1）")
    @discord.app_commands.choices(type=[
        discord.app_commands.Choice(name="普通の餌  ( 50pt)",  value="normal"),
        discord.app_commands.Choice(name="上等な餌 (150pt)", value="special"),
        discord.app_commands.Choice(name="高級な餌 (400pt)", value="premium"),
    ])
    async def bait(interaction: discord.Interaction, type: str, amount: int = 1):
        if not 1 <= amount <= 99:
            await interaction.response.send_message("1〜99個の間で指定してください。", ephemeral=True)
            return

        info = BAIT_TYPES[type]
        cost = info["cost"] * amount
        user_id = str(interaction.user.id)

        pts = get_points(user_id)
        if pts < cost:
            await interaction.response.send_message(
                f"ポイントが足りません。\n必要: **{cost}pt** / 所持: **{pts}pt**",
                ephemeral=True,
            )
            return

        if not buy_bait(user_id, type, amount, cost):
            await interaction.response.send_message("購入に失敗しました。再度お試しください。", ephemeral=True)
            return

        b = get_bait(user_id)
        await interaction.response.send_message(
            f"✅ **{info['name']}** × {amount} を購入しました（−{cost}pt）\n"
            f"現在の餌: 普通×{b['normal']} / 上等×{b['special']} / 高級×{b['premium']}",
            ephemeral=True,
        )
