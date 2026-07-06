import random

# 釣り竿ショップ（チャンネル設置パネル）で購入できる釣り竿（一度買うと永久所持）
# 何も持っていないと釣り自体ができない（青竿が実質の入場料）
FISHING_ROD_SHOP = {
    "blue":  {"name": "青釣り竿", "cost": 7},
    "green": {"name": "緑釣り竿", "cost": 3000},
    "red":   {"name": "赤釣り竿", "cost": 15000},
}

ROD_DISPLAY_NAMES = {
    "blue":  FISHING_ROD_SHOP["blue"]["name"],
    "green": FISHING_ROD_SHOP["green"]["name"],
    "red":   FISHING_ROD_SHOP["red"]["name"],
}

# 竿の強い順（自動選択に使う）
ROD_RANK_BEST_FIRST = ["red", "green", "blue"]


def best_owned_rod(owned_rods: dict) -> str | None:
    for rod_type in ROD_RANK_BEST_FIRST:
        if owned_rods.get(rod_type):
            return rod_type
    return None


# 確率テーブル [ごみ, 小魚, 中魚, 大魚, リヴァイアサン] ピク数ごと
_BASE_PROBS = {
    1: [0.55, 0.37, 0.07, 0.01, 0.00],
    2: [0.40, 0.40, 0.15, 0.05, 0.00],
    3: [0.25, 0.38, 0.24, 0.12, 0.01],
    4: [0.12, 0.30, 0.32, 0.24, 0.02],
    5: [0.04, 0.18, 0.33, 0.38, 0.07],
}

# 竿ごとの各レアリティ倍率 [ごみ, 小魚, 中魚, 大魚, リヴァイアサン]
# 掛け金は確率に一切影響しない（単なる毎回のコスト）。竿だけが確率を左右する。
_ROD_MULT = {
    "blue":  [1.0, 1.0, 1.0, 1.0, 1.0],
    "green": [1.0, 1.0, 1.0, 0.6, 1.0],
    "red":   [1.0, 1.0, 1.0, 1.3, 1.0],
}

# 竿・ピク数ごとに釣れる最大レアリティ（RARITIESのインデックス）。
# 各竿の最上位レアリティは終盤のピクでしか解禁されない。
def _max_rarity_index(rod_type: str, piku: int) -> int:
    if rod_type == "blue":
        return 2 if piku >= 4 else 1   # 中魚はピク4-5のみ
    if rod_type == "green":
        return 3 if piku >= 4 else 2   # 大魚はピク4-5のみ
    if rod_type == "red":
        return 4 if piku == 5 else 3   # リヴァイアサンはピク5のみ
    raise ValueError(f"unknown rod_type: {rod_type}")


VOICE_TOP_TIER_BOOST = 0.05  # 通話中、その時点で狙える最高レアリティの確率加算

ESCAPE_CHANCE = 0.20  # 「もっと待つ」ごとに20%で逃げる

# レアリティごとの配当倍率。獲得pt = 掛け金 × この倍率（確率には影響しない）
# ピク5まで粘る戦略の期待値が 青竿≒1.0倍 / 緑竿≒1.2倍 / 赤竿≒1.5倍 になるよう調整済み
# （渋め→実際のプレイ感を見て緩める方針。インフレは戻すのが難しいため）
RARITY_PAYOUT_MULT = {
    "trash":     0,
    "small":     1.2,
    "medium":    3.5,
    "large":     4,
    "leviathan": 12,
}

RARITIES = ["trash", "small", "medium", "large", "leviathan"]

RARITY_DISPLAY = {
    "trash":     {"star": "☆",     "label": "ごみ"},
    "small":     {"star": "★",     "label": "小魚"},
    "medium":    {"star": "★★",    "label": "中魚"},
    "large":     {"star": "★★★",   "label": "大魚"},
    "leviathan": {"star": "★★★★",  "label": "リヴァイアサン"},
}

FISH_TABLE = {
    "trash": [
        {"name": "ブーツ", "image": "boots.png"},
        {"name": "タイヤ", "image": "tire.png"},
    ],
    "small": [
        {"name": "ホーンフィッシュ",       "image": "horn_fish.png"},
        {"name": "ポイズナー",             "image": "poisner.png"},
        {"name": "カトラリーシュリンプ",   "image": "cutlery_shrimp.png"},
        {"name": "ギルフラッグ",           "image": "gill_flag.png"},
    ],
    "medium": [
        {"name": "マンボウモドキ",   "image": "manbow_modoki.png"},
        {"name": "インスタアロワナ", "image": "insta_arowana.png"},
    ],
    "large": [
        {"name": "サメクジラ",         "image": "samekujira.png"},
        {"name": "サンタマンダー",     "image": "santa_mander.png"},
        {"name": "ジャイアントイール", "image": "giant_eel.png"},
    ],
    "leviathan": [
        {"name": "？？？", "image": "???.png"},
    ],
}


def roll_fish(piku: int, rod_type: str, in_voice: bool) -> dict:
    probs = list(_BASE_PROBS[piku])
    probs = [p * m for p, m in zip(probs, _ROD_MULT[rod_type])]

    max_index = _max_rarity_index(rod_type, piku)
    for i in range(max_index + 1, len(probs)):
        probs[i] = 0.0

    if in_voice:
        probs[max_index] += VOICE_TOP_TIER_BOOST

    total = sum(probs)
    probs = [p / total for p in probs]

    rarity = random.choices(RARITIES, weights=probs, k=1)[0]
    fish = random.choice(FISH_TABLE[rarity])

    return {
        "name":   fish["name"],
        "rarity": rarity,
        "star":   RARITY_DISPLAY[rarity]["star"],
        "image":  fish["image"],
    }
