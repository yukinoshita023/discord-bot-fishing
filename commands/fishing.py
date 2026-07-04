import discord
import asyncio
import random
from features.firebase_client import get_fishing_bait, use_fishing_bait, get_fishing_rods, sell_fish
from features.fish_data import FISHING_BAIT_SHOP, ROD_DISPLAY_NAMES, STARTER_ROD, ESCAPE_CHANCE, roll_fish

FISH_CHANNEL_ID = 1522867297365131304

active_fishing: set[int] = set()

_PIKU_TEXT = {
    1: "🐟 ピクっ！",
    2: "🐟 ピクピクっ！！",
    3: "🐟 ピクピクピクっ！！！",
    4: "🐟 ピクピクピクピクっ！！！！",
    5: "🐟 ピクピクピクピクピクっ！！！！！\n⚠️ これが最後のチャンス！",
}


class FishingView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        bait_type: str,
        rod_type: str,
        piku: int,
        root: discord.Interaction,
    ):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.bait_type = bait_type
        self.rod_type = rod_type
        self.piku = piku
        self.root = root

        if piku >= 5:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and "待つ" in (item.label or ""):
                    item.disabled = True

    @discord.ui.button(label="🎣 釣り上げる！", style=discord.ButtonStyle.success)
    async def pull(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたの釣りではありません！", ephemeral=True)
            return

        self.stop()
        active_fishing.discard(self.user_id)

        in_voice = interaction.user.voice is not None
        fish = roll_fish(self.piku, self.bait_type, self.rod_type, in_voice)

        new_total = sell_fish(str(self.user_id), fish["sell_price"])
        voice_bonus = " 🎤通話ボーナス中！" if in_voice else ""
        content = (
            f"🎉 釣り上げた！{voice_bonus}\n"
            f"{fish['star']} **{fish['name']}**\n"
            f"売却して **+{fish['sell_price']}pt**（所持: {new_total}pt）"
        )
        await interaction.response.edit_message(content=content, view=None)

        public_image = discord.File(f"images/{fish['image']}", filename=fish["image"])
        await interaction.channel.send(
            content=(
                f"🎉 {interaction.user.mention} が釣り上げた！{voice_bonus}\n"
                f"{fish['star']} **{fish['name']}**（**{fish['sell_price']}pt**）"
            ),
            file=public_image,
        )

    @discord.ui.button(label="⏳ もっと待つ...", style=discord.ButtonStyle.secondary)
    async def wait(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたの釣りではありません！", ephemeral=True)
            return

        self.stop()

        if random.random() < ESCAPE_CHANCE:
            active_fishing.discard(self.user_id)
            await interaction.response.edit_message(
                content="💨 惜しい！もう少しのところで逃げられてしまった...", view=None
            )
            return

        new_piku = self.piku + 1
        view = FishingView(self.user_id, self.bait_type, self.rod_type, new_piku, self.root)
        await interaction.response.edit_message(content=_PIKU_TEXT[new_piku], view=view)


async def setup(bot):
    @bot.tree.command(name="fishing", description="釣りをする（餌と釣り竿が必要）")
    @discord.app_commands.describe(bait="使用する釣り餌", rod="使用する釣り竿")
    @discord.app_commands.choices(bait=[
        discord.app_commands.Choice(name="青餌", value="blue"),
        discord.app_commands.Choice(name="緑餌", value="green"),
        discord.app_commands.Choice(name="赤餌", value="red"),
    ])
    @discord.app_commands.choices(rod=[
        discord.app_commands.Choice(name="木の釣り竿", value="wood"),
        discord.app_commands.Choice(name="青釣り竿", value="blue"),
        discord.app_commands.Choice(name="緑釣り竿", value="green"),
        discord.app_commands.Choice(name="赤釣り竿", value="red"),
    ])
    async def fish(interaction: discord.Interaction, bait: str, rod: str = STARTER_ROD):
        if interaction.channel_id != FISH_CHANNEL_ID:
            await interaction.response.send_message(
                f"このコマンドは<#{FISH_CHANNEL_ID}>でのみ使用できます。", ephemeral=True
            )
            return

        user_id = interaction.user.id

        if user_id in active_fishing:
            await interaction.response.send_message(
                "すでに釣り中です！先に結果を確認してください。", ephemeral=True
            )
            return

        if rod != STARTER_ROD:
            rods = get_fishing_rods(str(user_id))
            if not rods.get(rod, False):
                name = ROD_DISPLAY_NAMES[rod]
                await interaction.response.send_message(
                    f"**{name}** を所持していません！釣り竿ショップで購入してください。", ephemeral=True
                )
                return

        bait_data = get_fishing_bait(str(user_id))
        if bait_data.get(bait, 0) <= 0:
            name = FISHING_BAIT_SHOP[bait]["name"]
            await interaction.response.send_message(
                f"**{name}** がありません！釣り餌ショップで購入してください。", ephemeral=True
            )
            return

        if not use_fishing_bait(str(user_id), bait):
            await interaction.response.send_message("餌の使用に失敗しました。", ephemeral=True)
            return

        bait_name = FISHING_BAIT_SHOP[bait]["name"]
        remaining = bait_data[bait] - 1

        active_fishing.add(user_id)
        await interaction.response.send_message(
            f"🎣 竿を投げた...（{bait_name} 残り: {remaining}個）", ephemeral=True
        )

        await asyncio.sleep(1.5)

        view = FishingView(user_id, bait, rod, 1, interaction)
        await interaction.edit_original_response(content=_PIKU_TEXT[1], view=view)
