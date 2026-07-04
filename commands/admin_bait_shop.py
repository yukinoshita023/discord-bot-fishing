import discord
from config import ADMIN_ROLE_ID
from features.firebase_client import get_points, get_fishing_bait, buy_fishing_bait
from features.fish_data import FISHING_BAIT_SHOP

BAIT_SHOP_CHANNEL_ID = 1520343817239138375
IMAGE_PATH = "images/purchase_fish_bait.png"


class BaitShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _buy(self, interaction: discord.Interaction, bait_type: str):
        info = FISHING_BAIT_SHOP[bait_type]
        user_id = str(interaction.user.id)

        pts = get_points(user_id)
        if pts < info["cost"]:
            await interaction.response.send_message(
                f"WPが足りません。\n必要: **{info['cost']}WP** / 所持: **{pts}WP**",
                ephemeral=True,
            )
            return

        if not buy_fishing_bait(user_id, bait_type, info["cost"]):
            await interaction.response.send_message("購入に失敗しました。再度お試しください。", ephemeral=True)
            return

        bait = get_fishing_bait(user_id)
        await interaction.response.send_message(
            f"✅ **{info['name']}** を購入しました（−{info['cost']}WP）\n"
            f"現在の釣り餌: 青×{bait['blue']} / 緑×{bait['green']} / 赤×{bait['red']}",
            ephemeral=True,
        )

    @discord.ui.button(label="青餌 (50WP)", style=discord.ButtonStyle.primary, custom_id="fishing_bait_shop:blue")
    async def buy_blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "blue")

    @discord.ui.button(label="緑餌 (500WP)", style=discord.ButtonStyle.success, custom_id="fishing_bait_shop:green")
    async def buy_green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "green")

    @discord.ui.button(label="赤餌 (1000WP)", style=discord.ButtonStyle.danger, custom_id="fishing_bait_shop:red")
    async def buy_red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "red")


async def setup(bot):
    bot.add_view(BaitShopView())

    @bot.tree.command(name="admin_bait_shop", description="【管理課専用】釣り餌ショップのパネルを設置する")
    async def admin_bait_shop(interaction: discord.Interaction):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("このコマンドは管理課ロール専用です。", ephemeral=True)
            return

        channel = bot.get_channel(BAIT_SHOP_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("チャンネルが見つかりません。", ephemeral=True)
            return

        file = discord.File(IMAGE_PATH, filename="purchase_fish_bait.png")
        await channel.send(file=file, view=BaitShopView())
        await interaction.response.send_message("釣り餌ショップを設置しました。", ephemeral=True)
