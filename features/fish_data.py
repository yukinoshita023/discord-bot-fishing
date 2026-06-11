import random

BAIT_TYPES = {
    "normal":  {"name": "普通の餌",  "cost": 50},
    "special": {"name": "上等な餌",  "cost": 150},
    "premium": {"name": "高級な餌",  "cost": 400},
}

# 確率テーブル [コモン, アンコモン, レア, 伝説] ピク数ごと
_BASE_PROBS = {
    1: [0.70, 0.22, 0.07, 0.01],
    2: [0.60, 0.25, 0.12, 0.03],
    3: [0.45, 0.28, 0.20, 0.07],
    4: [0.30, 0.28, 0.28, 0.14],
    5: [0.15, 0.25, 0.35, 0.25],
}

# 餌ごとの各レアリティ倍率 [コモン, アンコモン, レア, 伝説]
_BAIT_MULT = {
    "normal":  [1.0, 1.0, 1.0, 1.0],
    "special": [0.7, 0.9, 1.5, 2.0],
    "premium": [0.4, 0.7, 2.0, 3.5],
}

VOICE_LEGENDARY_BOOST = 0.05  # 通話中の伝説確率加算

ESCAPE_CHANCE = 0.20  # 「もっと待つ」ごとに20%で逃げる

RARITIES = ["common", "uncommon", "rare", "legendary"]

RARITY_DISPLAY = {
    "common":    {"star": "★",    "label": "コモン"},
    "uncommon":  {"star": "★★",   "label": "アンコモン"},
    "rare":      {"star": "★★★",  "label": "レア"},
    "legendary": {"star": "★★★★", "label": "伝説"},
}

# モック魚データ（名前・画像は後で差し替え）
FISH_TABLE = {
    "common": [
        {"name": "フナ",   "sell_price": 30},
        {"name": "コイ",   "sell_price": 45},
        {"name": "モロコ", "sell_price": 35},
    ],
    "uncommon": [
        {"name": "サーモン", "sell_price": 130},
        {"name": "マス",     "sell_price": 150},
    ],
    "rare": [
        {"name": "マグロ", "sell_price": 420},
        {"name": "ヒラメ", "sell_price": 450},
    ],
    "legendary": [
        {"name": "龍魚",     "sell_price": 1200},
        {"name": "伝説の鯛", "sell_price": 1500},
    ],
}


def roll_fish(piku: int, bait_type: str, in_voice: bool) -> dict:
    probs = [b * m for b, m in zip(_BASE_PROBS[piku], _BAIT_MULT[bait_type])]

    if in_voice:
        probs[3] += VOICE_LEGENDARY_BOOST

    total = sum(probs)
    probs = [p / total for p in probs]

    rarity = random.choices(RARITIES, weights=probs, k=1)[0]
    fish = random.choice(FISH_TABLE[rarity])

    return {
        "name":       fish["name"],
        "sell_price": fish["sell_price"],
        "rarity":     rarity,
        "star":       RARITY_DISPLAY[rarity]["star"],
    }
