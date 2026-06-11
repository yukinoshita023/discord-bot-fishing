import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def _user_ref(user_id: str):
    return db.collection("users").document(user_id)


def get_points(user_id: str) -> int:
    doc = _user_ref(user_id).get()
    if not doc.exists:
        return 0
    return int((doc.to_dict() or {}).get("points", {}).get("わくせい", 0))


def get_bait(user_id: str) -> dict:
    doc = _user_ref(user_id).get()
    bait = (doc.to_dict() or {}).get("bait", {}) if doc.exists else {}
    return {k: bait.get(k, 0) for k in ("normal", "special", "premium")}


def use_bait(user_id: str, bait_type: str) -> bool:
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        count = data.get("bait", {}).get(bait_type, 0)
        if count <= 0:
            return False
        transaction.update(ref, {f"bait.{bait_type}": count - 1})
        return True

    return _tx(db.transaction(), ref)


def buy_bait(user_id: str, bait_type: str, amount: int, cost: int) -> bool:
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        pts = int(data.get("points", {}).get("わくせい", 0))
        if pts < cost:
            return False
        current_bait = data.get("bait", {}).get(bait_type, 0)
        transaction.update(ref, {
            "points.わくせい": pts - cost,
            f"bait.{bait_type}": current_bait + amount,
        })
        return True

    return _tx(db.transaction(), ref)


def get_inventory(user_id: str) -> list:
    doc = _user_ref(user_id).get()
    return (doc.to_dict() or {}).get("fish_inventory", []) if doc.exists else []


def add_fish(user_id: str, fish: dict) -> tuple[bool, str]:
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        inventory = data.get("fish_inventory", [])

        now = datetime.now(timezone.utc)
        inventory = [
            f for f in inventory
            if _parse_dt(f["caught_at"]) + timedelta(days=7) > now
        ]

        if len(inventory) >= 10:
            return False, "在庫が満杯です（最大10匹）。先に売ってください。"

        inventory.append({**fish, "caught_at": now.isoformat()})
        transaction.update(ref, {"fish_inventory": inventory})
        return True, ""

    return _tx(db.transaction(), ref)


def sell_fish(user_id: str, indices: list[int]) -> tuple[int, int]:
    """Returns (earned_points, count_sold)."""
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        inventory = data.get("fish_inventory", [])
        now = datetime.now(timezone.utc)
        idx_set = set(indices)

        earned = 0
        new_inventory = []
        sold = 0
        for i, fish in enumerate(inventory):
            expired = _parse_dt(fish["caught_at"]) + timedelta(days=7) <= now
            if i in idx_set and not expired:
                earned += fish["sell_price"]
                sold += 1
            else:
                new_inventory.append(fish)

        pts = int(data.get("points", {}).get("わくせい", 0))
        transaction.update(ref, {
            "fish_inventory": new_inventory,
            "points.わくせい": pts + earned,
        })
        return earned, sold

    return _tx(db.transaction(), ref)


def _parse_dt(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
