import discord
import asyncio
import random
from features.firebase_client import get_bait, use_bait, add_fish
from features.fish_data import BAIT_TYPES, ESCAPE_CHANCE, roll_fish

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
        piku: int,
        root: discord.Interaction,
    ):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.bait_type = bait_type
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
        fish = roll_fish(self.piku, self.bait_type, in_voice)

        success, err = add_fish(str(self.user_id), fish)
        if success:
            voice_bonus = " 🎤通話ボーナス中！" if in_voice else ""
            content = (
                f"🎉 釣り上げた！{voice_bonus}\n"
                f"{fish['star']} **{fish['name']}**\n"
                f"売値: **{fish['sell_price']}pt** | 保存期間: 7日間"
            )
        else:
            content = f"❌ {err}\n（魚は逃げてしまいました...）"

        await interaction.response.edit_message(content=content, view=None)

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
        view = FishingView(self.user_id, self.bait_type, new_piku, self.root)
        await interaction.response.edit_message(content=_PIKU_TEXT[new_piku], view=view)


async def setup(bot):
    @bot.tree.command(name="fish", description="釣りをする（餌が必要）")
    @discord.app_commands.describe(bait="使用する餌の種類")
    @discord.app_commands.choices(bait=[
        discord.app_commands.Choice(name="普通の餌  ( 50pt)", value="normal"),
        discord.app_commands.Choice(name="上等な餌 (150pt)", value="special"),
        discord.app_commands.Choice(name="高級な餌 (400pt)", value="premium"),
    ])
    async def fish(interaction: discord.Interaction, bait: str = "normal"):
        user_id = interaction.user.id

        if user_id in active_fishing:
            await interaction.response.send_message(
                "すでに釣り中です！先に結果を確認してください。", ephemeral=True
            )
            return

        bait_data = get_bait(str(user_id))
        if bait_data.get(bait, 0) <= 0:
            name = BAIT_TYPES[bait]["name"]
            await interaction.response.send_message(
                f"**{name}** がありません！`/bait` で購入してください。", ephemeral=True
            )
            return

        if not use_bait(str(user_id), bait):
            await interaction.response.send_message("餌の使用に失敗しました。", ephemeral=True)
            return

        active_fishing.add(user_id)
        await interaction.response.send_message("🎣 竿を投げた...", ephemeral=True)

        await asyncio.sleep(1.5)

        view = FishingView(user_id, bait, 1, interaction)
        await interaction.edit_original_response(content=_PIKU_TEXT[1], view=view)
