import random

# 釣り餌ショップ（チャンネル設置パネル）で購入できる釣り餌
FISHING_BAIT_SHOP = {
    "blue":  {"name": "青餌", "cost": 50},
    "green": {"name": "緑餌", "cost": 500},
    "red":   {"name": "赤餌", "cost": 1000},
}

# 釣り竿ショップ（チャンネル設置パネル）で購入できる釣り竿（一度買うと永久所持）
FISHING_ROD_SHOP = {
    "blue":  {"name": "青釣り竿", "cost": 1000},
    "green": {"name": "緑釣り竿", "cost": 10000},
    "red":   {"name": "赤釣り竿", "cost": 30000},
}

# 何も購入していない全員が最初から使える初期釣り竿（Firebase上には保存しない）
STARTER_ROD = "wood"

# 表示名（ショップで買えない木の釣り竿も含む）
ROD_DISPLAY_NAMES = {
    "wood":  "木の釣り竿",
    "blue":  FISHING_ROD_SHOP["blue"]["name"],
    "green": FISHING_ROD_SHOP["green"]["name"],
    "red":   FISHING_ROD_SHOP["red"]["name"],
}

# 確率テーブル [ごみ, 小魚, 中魚, 大魚, リヴァイアサン] ピク数ごと
# ピクが進むほど中魚・大魚に大きく偏る（5回目が一番おいしい）
_BASE_PROBS = {
    1: [0.55, 0.37, 0.07, 0.01, 0.00],
    2: [0.40, 0.40, 0.15, 0.05, 0.00],
    3: [0.25, 0.38, 0.24, 0.12, 0.01],
    4: [0.12, 0.30, 0.32, 0.24, 0.02],
    5: [0.04, 0.18, 0.33, 0.38, 0.07],
}

# 釣り餌ごとの各レアリティ倍率 [ごみ, 小魚, 中魚, 大魚, リヴァイアサン]
_BAIT_MULT = {
    "blue":  [1.0, 1.0, 1.0, 1.0, 1.0],
    "green": [0.75, 1.0, 1.3, 1.7, 1.7],
    "red":   [0.5, 0.8, 1.8, 3.0, 5.0],
}

# 釣り竿ごとの各レアリティ倍率 [ごみ, 小魚, 中魚, 大魚, リヴァイアサン]（餌の倍率とは別軸で乗算）
# wood（木の釣り竿）は全員が持っている無料の初期竿で、これが基準（倍率なし）
_ROD_MULT = {
    "wood":  [1.0, 1.0, 1.0, 1.0, 1.0],
    "blue":  [0.92, 1.0, 1.1, 1.3, 1.3],
    "green": [0.8, 0.95, 1.3, 1.7, 1.7],
    "red":   [0.6, 0.85, 1.8, 3.0, 5.0],
}

VOICE_TOP_TIER_BOOST = 0.05  # 通話中、その時点で狙える最高レアリティの確率加算

ESCAPE_CHANCE = 0.20  # 「もっと待つ」ごとに20%で逃げる

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
        {"name": "ブーツ", "sell_price": 0, "image": "boots.png"},
        {"name": "タイヤ", "sell_price": 0, "image": "tire.png"},
    ],
    "small": [
        {"name": "ホーンフィッシュ",       "sell_price": 100, "image": "horn_fish.png"},
        {"name": "ポイズナー",             "sell_price": 130, "image": "poisner.png"},
        {"name": "カトラリーシュリンプ",   "sell_price": 150, "image": "cutlery_shrimp.png"},
        {"name": "ギルフラッグ",           "sell_price": 180, "image": "gill_flag.png"},
    ],
    "medium": [
        {"name": "マンボウモドキ",   "sell_price": 750,  "image": "manbow_modoki.png"},
        {"name": "インスタアロワナ", "sell_price": 1000, "image": "insta_arowana.png"},
    ],
    "large": [
        {"name": "サメクジラ",         "sell_price": 3000, "image": "samekujira.png"},
        {"name": "サンタマンダー",     "sell_price": 3500, "image": "santa_mander.png"},
        {"name": "ジャイアントイール", "sell_price": 4000, "image": "giant_eel.png"},
    ],
    "leviathan": [
        {"name": "？？？", "sell_price": 50000, "image": "???.png"},
    ],
}


def roll_fish(piku: int, bait_type: str, rod_type: str, in_voice: bool) -> dict:
    probs = list(_BASE_PROBS[piku])
    probs = [p * m for p, m in zip(probs, _BAIT_MULT[bait_type])]
    probs = [p * m for p, m in zip(probs, _ROD_MULT[rod_type])]

    is_leviathan_ready = bait_type == "red" and rod_type == "red"
    if not is_leviathan_ready:
        probs[4] = 0.0

    if in_voice:
        boost_index = 4 if is_leviathan_ready else 3
        probs[boost_index] += VOICE_TOP_TIER_BOOST

    total = sum(probs)
    probs = [p / total for p in probs]

    rarity = random.choices(RARITIES, weights=probs, k=1)[0]
    fish = random.choice(FISH_TABLE[rarity])

    return {
        "name":       fish["name"],
        "sell_price": fish["sell_price"],
        "rarity":     rarity,
        "star":       RARITY_DISPLAY[rarity]["star"],
        "image":      fish["image"],
    }
