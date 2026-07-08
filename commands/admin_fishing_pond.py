import discord
import asyncio
import random
from config import ADMIN_ROLE_ID
from features.firebase_client import get_points, spend_points, get_fishing_rods, sell_fish
from features.fish_data import ROD_DISPLAY_NAMES, best_owned_rod, ESCAPE_CHANCE, RARITY_PAYOUT_MULT, roll_fish

FISHING_POND_CHANNEL_ID = 1523703402289303643
FISHING_LOG_CHANNEL_ID = 1523703443125043341

active_fishing: set[int] = set()

_PIKU_TEXT = {
    1: "🐟 ピクっ！",
    2: "🐟 ピクピクっ！！",
    3: "🐟 ピクピクピクっ！！！",
    4: "🐟 ピクピクピクピクっ！！！！",
    5: "🐟 ピクピクピクピクピクっ！！！！！\n⚠️ これが最後のチャンス！",
}


FISHING_TIMEOUT_SECONDS = 600  # 放置された釣りセッションの自動終了（ロック解放）までの時間

# 掛け金の上限。赤竿の期待値1.22倍×上限1000で、やり込む人が約半月で10万WPに到達するペース
# （リヴァイアサン一撃は最大50,000WP）
MAX_WAGER = 1000

PANEL_TITLE = "🎣 わくせいフィッシング"

# パネルを常にチャンネル最下部に保つための再投稿管理
_panel_message: discord.Message | None = None
_panel_lock = asyncio.Lock()


def _build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title=PANEL_TITLE,
        description=(
            "わくせいポイント（WP）を賭けて魚を釣ろう！\n"
            "下の **「🎣 釣りをする」** ボタンから掛け金を入力してスタート！\n"
            "​"
        ),
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="🐟 遊び方",
        value=(
            "1. ボタンを押して掛け金（WP）を入力\n"
            "\n"
            "2. 「ピクっ！」ときたら選択：\n"
            "　🎣 **釣り上げる** → その場で魚が確定\n"
            "　⏳ **もっと待つ** → 大物のチャンス！ただし逃げられるかも…\n"
            "\n"
            "3. 釣れた魚に応じて配当WPをゲット！\n"
            "​"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎣 釣り竿",
        value=(
            "竿が良いほどレアな魚が釣れる！\n"
            "（所持している一番良い竿を自動で使用）\n"
            "購入は釣り竿ショップへ🛒\n"
            "​"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎤 通話ボーナス",
        value="通話に参加しながら釣ると、レアな魚が釣れやすくなる！",
        inline=False,
    )
    embed.set_footer(text="釣果は釣りログチャンネルでみんなに公開されます")
    return embed


def _is_panel_message(client: discord.Client, message: discord.Message) -> bool:
    return (
        message.author.id == client.user.id
        and bool(message.embeds)
        and message.embeds[0].title == PANEL_TITLE
    )


async def refresh_panel(client: discord.Client):
    """パネルを設置し直す（新規投稿→古いパネルを削除）。/admin_fishing_pondからのみ使用。"""
    global _panel_message

    async with _panel_lock:
        channel = client.get_channel(FISHING_POND_CHANNEL_ID)
        if channel is None:
            return

        try:
            new_panel = await channel.send(embed=_build_panel_embed(), view=FishingPondView())
        except discord.HTTPException:
            return

        old_panel = _panel_message
        _panel_message = new_panel

        if old_panel is not None:
            try:
                await old_panel.delete()
            except discord.HTTPException:
                pass
        else:
            # Bot再起動直後などで古いパネルの参照がない場合は履歴から探して掃除する
            try:
                async for message in channel.history(limit=30):
                    if message.id != new_panel.id and _is_panel_message(client, message):
                        await message.delete()
            except discord.HTTPException:
                pass


# ユーザーごとの直前セッションのephemeralメッセージ参照。
# 本人のephemeralが溜まるとその人の画面でパネルが上に流れてしまうため、
# 次のキャスト開始時（ボタン操作前の安全なタイミング）に前回分を片付ける。
# タイマーで消すとボタンを押す瞬間にレイアウトがずれて誤クリックを招くため、この方式にしている。
_last_session_interaction: dict[int, discord.Interaction] = {}


def remember_session_message(user_id: int, interaction: discord.Interaction):
    _last_session_interaction[user_id] = interaction


async def cleanup_previous_session_message(user_id: int):
    prev = _last_session_interaction.pop(user_id, None)
    if prev is None:
        return
    try:
        await prev.delete_original_response()
    except discord.HTTPException:
        # インタラクショントークンの期限（15分）切れなどは無視する
        pass


class FishingView(discord.ui.View):
    def __init__(self, user_id: int, rod_type: str, wager: int, piku: int, origin: discord.Interaction):
        super().__init__(timeout=FISHING_TIMEOUT_SECONDS)
        self.user_id = user_id
        self.rod_type = rod_type
        self.wager = wager
        self.piku = piku
        self.origin = origin

        if piku >= 5:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and "待つ" in (item.label or ""):
                    item.disabled = True

    async def on_timeout(self):
        # メッセージを閉じた・放置した場合でもロックを解放する（掛け金は没収）
        active_fishing.discard(self.user_id)
        try:
            await self.origin.edit_original_response(
                content="⌛ 長時間反応がなかったため、魚は逃げてしまいました...", view=None
            )
        except discord.HTTPException:
            pass
        remember_session_message(self.user_id, self.origin)

    @discord.ui.button(label="🎣 釣り上げる！", style=discord.ButtonStyle.success)
    async def pull(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたの釣りではありません！", ephemeral=True)
            return

        self.stop()
        active_fishing.discard(self.user_id)

        # Firestoreへの書き込みが3秒の応答制限を超えることがある（特に起動直後の初回接続）ため、
        # 先にdeferで応答猶予を確保してから重い処理を行う
        await interaction.response.defer()

        in_voice = interaction.user.voice is not None
        fish = roll_fish(self.piku, self.rod_type, in_voice)
        payout = int(self.wager * RARITY_PAYOUT_MULT[fish["rarity"]])

        new_total = sell_fish(str(self.user_id), payout)
        voice_bonus = " 🎤通話ボーナス中！" if in_voice else ""
        content = (
            f"🎉 釣り上げた！{voice_bonus}\n"
            f"{fish['star']} **{fish['name']}**\n"
            f"獲得 **+{payout}pt**（所持: {new_total}pt）"
        )
        # discord.Fileは使い回せないため、本人向けとログ向けで別々に生成する
        ephemeral_image = discord.File(f"images/{fish['image']}", filename=fish["image"])
        await interaction.edit_original_response(content=content, attachments=[ephemeral_image], view=None)

        log_channel = interaction.client.get_channel(FISHING_LOG_CHANNEL_ID)
        if log_channel is not None:
            profit = payout - self.wager
            rod_name = ROD_DISPLAY_NAMES[self.rod_type]
            public_image = discord.File(f"images/{fish['image']}", filename=fish["image"])
            await log_channel.send(
                content=(
                    f"🎉 {interaction.user.mention} が釣り上げた！{voice_bonus}\n"
                    f"{fish['star']} **{fish['name']}**（{rod_name}）\n"
                    f"💰 掛け金 **{self.wager}WP** → 獲得 **{payout}WP**（収支 **{profit:+d}WP**）"
                ),
                file=public_image,
            )

        remember_session_message(self.user_id, interaction)

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
            remember_session_message(self.user_id, interaction)
            return

        new_piku = self.piku + 1
        view = FishingView(self.user_id, self.rod_type, self.wager, new_piku, interaction)
        await interaction.response.edit_message(content=_PIKU_TEXT[new_piku], view=view)


class WagerModal(discord.ui.Modal, title="釣りの掛け金"):
    amount = discord.ui.TextInput(
        label=f"掛け金 (1〜{MAX_WAGER}WP)", placeholder="例: 100", max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # ボタン押下時にもチェックしているが、モーダルを複数開いて同時送信する
        # 二重掛け金を防ぐため、送信時点でも再チェックする
        if user_id in active_fishing:
            await interaction.response.send_message(
                "すでに釣り中です！先に結果を確認してください。", ephemeral=True
            )
            return

        try:
            wager = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message("半角数字で入力してください。", ephemeral=True)
            return

        if not 1 <= wager <= MAX_WAGER:
            await interaction.response.send_message(
                f"掛け金は1〜{MAX_WAGER}WPの間で指定してください。", ephemeral=True
            )
            return

        # ここから先はFirestore呼び出しで3秒の応答制限を超えることがあるため、先にdeferする
        await interaction.response.defer(ephemeral=True, thinking=True)

        # まだボタン操作が始まっていない今のうちに、前回セッションのメッセージを片付ける
        await cleanup_previous_session_message(user_id)

        rod = best_owned_rod(get_fishing_rods(str(user_id)))
        if rod is None:
            await interaction.edit_original_response(
                content="釣り竿を持っていません！釣り竿ショップで青竿を購入してください。"
            )
            remember_session_message(user_id, interaction)
            return

        pts = get_points(str(user_id))
        if pts < wager:
            await interaction.edit_original_response(
                content=f"WPが足りません。\n指定: **{wager}WP** / 所持: **{pts}WP**"
            )
            remember_session_message(user_id, interaction)
            return

        if not spend_points(str(user_id), wager):
            await interaction.edit_original_response(content="処理に失敗しました。再度お試しください。")
            remember_session_message(user_id, interaction)
            return

        active_fishing.add(user_id)
        rod_name = ROD_DISPLAY_NAMES[rod]
        await interaction.edit_original_response(
            content=f"🎣 竿を投げた...（{rod_name} / 掛け金: {wager}WP）"
        )

        await asyncio.sleep(1.5)

        view = FishingView(user_id, rod, wager, 1, interaction)
        await interaction.edit_original_response(content=_PIKU_TEXT[1], view=view)


class FishingPondView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎣 釣りをする", style=discord.ButtonStyle.success, custom_id="fishing_pond:start")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id in active_fishing:
            await interaction.response.send_message(
                "すでに釣り中です！先に結果を確認してください。", ephemeral=True
            )
            return

        # モーダル表示はdeferできず3秒制限が厳しいため、Firestoreを触る
        # 竿の所持チェックはモーダル送信後（WagerModal.on_submit）に行う
        await interaction.response.send_modal(WagerModal())


async def setup(bot):
    bot.add_view(FishingPondView())

    @bot.tree.command(name="admin_fishing_pond", description="【管理課専用】釣り堀のパネルを設置する")
    async def admin_fishing_pond(interaction: discord.Interaction):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("このコマンドは管理課ロール専用です。", ephemeral=True)
            return

        channel = bot.get_channel(FISHING_POND_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("チャンネルが見つかりません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await refresh_panel(bot)
        await interaction.edit_original_response(content="釣り堀のパネルを設置しました。")
