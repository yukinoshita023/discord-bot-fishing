import discord
from datetime import datetime, timedelta, timezone
from features.firebase_client import get_inventory, sell_fish

_RARITY_ORDER = {"legendary": 0, "rare": 1, "uncommon": 2, "common": 3}


def _remaining_days(caught_at: str) -> float:
    dt = datetime.fromisoformat(caught_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (dt + timedelta(days=7) - datetime.now(timezone.utc)).total_seconds() / 86400
    return max(0.0, delta)


def _expiry_label(days: float) -> str:
    if days <= 0:
        return "⚠️腐敗"
    if days < 1:
        return f"残り{int(days * 24)}時間"
    return f"残り{int(days)}日"


def _build_content(inventory: list, selected: set = None, total: int = 0) -> str:
    if not inventory:
        return "🎣 在庫に魚がいません"

    lines = ["**🐟 魚の在庫**\n"]
    for i, fish in enumerate(inventory):
        days = _remaining_days(fish["caught_at"])
        check = "☑" if selected and i in selected else "□"
        line = f"`{check}` {fish['star']} **{fish['name']}** — {fish['sell_price']}pt　{_expiry_label(days)}"
        lines.append(line)

    if selected:
        lines.append(f"\n選択中の合計: **{total}pt**")

    return "\n".join(lines)


class InventoryView(discord.ui.View):
    def __init__(self, user_id: int, inventory: list):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.inventory = inventory
        self.selected: set[int] = set()

        sellable = [
            (i, fish) for i, fish in enumerate(inventory)
            if _remaining_days(fish["caught_at"]) > 0
        ]

        if sellable:
            options = [
                discord.SelectOption(
                    label=f"{fish['star']} {fish['name']} ({fish['sell_price']}pt)",
                    value=str(i),
                    description=_expiry_label(_remaining_days(fish["caught_at"])),
                )
                for i, fish in sellable
            ]
            self.fish_select.options = options
            self.fish_select.max_values = len(options)
        else:
            self.remove_item(self.fish_select)
            self.remove_item(self.sell_btn)

    @discord.ui.select(
        placeholder="売りたい魚を選択...",
        min_values=0,
        max_values=1,
        options=[discord.SelectOption(label="placeholder", value="0")],
    )
    async def fish_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのインベントリではありません！", ephemeral=True)
            return

        self.selected = {int(v) for v in select.values}
        total = sum(self.inventory[i]["sell_price"] for i in self.selected)
        await interaction.response.edit_message(
            content=_build_content(self.inventory, self.selected, total), view=self
        )

    @discord.ui.button(label="💰 売る", style=discord.ButtonStyle.danger)
    async def sell_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのインベントリではありません！", ephemeral=True)
            return

        if not self.selected:
            await interaction.response.send_message("魚が選択されていません！", ephemeral=True)
            return

        self.stop()
        earned, count = sell_fish(str(self.user_id), list(self.selected))
        await interaction.response.edit_message(
            content=f"✅ {count}匹を売りました！ **+{earned}pt** 獲得！", view=None
        )


async def setup(bot):
    @bot.tree.command(name="inventory", description="釣った魚の在庫を確認・売却")
    async def inventory(interaction: discord.Interaction):
        inv = get_inventory(str(interaction.user.id))

        inv.sort(key=lambda f: (
            _RARITY_ORDER.get(f.get("rarity", "common"), 99),
            -_remaining_days(f["caught_at"]),
        ))

        view = InventoryView(interaction.user.id, inv)
        await interaction.response.send_message(
            _build_content(inv), view=view, ephemeral=True
        )
