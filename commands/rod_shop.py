import discord
from features.firebase_client import get_points, buy_fishing_rod
from features.fish_data import FISHING_ROD_SHOP

ROD_SHOP_CHANNEL_ID = 1520343886826967070
IMAGE_PATH = "images/purchase_fish_rod.png"


class RodShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _buy(self, interaction: discord.Interaction, rod_type: str):
        info = FISHING_ROD_SHOP[rod_type]
        user_id = str(interaction.user.id)

        pts = get_points(user_id)
        if pts < info["cost"]:
            await interaction.response.send_message(
                f"WPが足りません。\n必要: **{info['cost']}WP** / 所持: **{pts}WP**",
                ephemeral=True,
            )
            return

        result = buy_fishing_rod(user_id, rod_type, info["cost"])
        if result == "already_owned":
            await interaction.response.send_message(
                f"**{info['name']}** は購入済みです。", ephemeral=True
            )
            return
        if result == "insufficient":
            await interaction.response.send_message(
                f"WPが足りません。\n必要: **{info['cost']}WP** / 所持: **{pts}WP**",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ **{info['name']}** を購入しました（−{info['cost']}WP）", ephemeral=True
        )

    @discord.ui.button(label="青釣り竿 (1000WP)", style=discord.ButtonStyle.primary, custom_id="fishing_rod_shop:blue")
    async def buy_blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "blue")

    @discord.ui.button(label="緑釣り竿 (10000WP)", style=discord.ButtonStyle.success, custom_id="fishing_rod_shop:green")
    async def buy_green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "green")

    @discord.ui.button(label="赤釣り竿 (30000WP)", style=discord.ButtonStyle.danger, custom_id="fishing_rod_shop:red")
    async def buy_red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "red")


async def setup(bot):
    bot.add_view(RodShopView())

    @bot.tree.command(name="rod_shop_setup", description="【管理者用】釣り竿ショップのパネルを設置する")
    @discord.app_commands.default_permissions(administrator=True)
    async def rod_shop_setup(interaction: discord.Interaction):
        channel = bot.get_channel(ROD_SHOP_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("チャンネルが見つかりません。", ephemeral=True)
            return

        file = discord.File(IMAGE_PATH, filename="purchase_fish_rod.png")
        await channel.send(file=file, view=RodShopView())
        await interaction.response.send_message("釣り竿ショップを設置しました。", ephemeral=True)
