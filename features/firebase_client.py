import firebase_admin
from firebase_admin import credentials, firestore

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


def spend_points(user_id: str, amount: int) -> bool:
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        pts = int(data.get("points", {}).get("わくせい", 0))
        if pts < amount:
            return False
        transaction.update(ref, {"points.わくせい": pts - amount})
        return True

    return _tx(db.transaction(), ref)


def get_fishing_rods(user_id: str) -> dict:
    doc = _user_ref(user_id).get()
    data = (doc.to_dict() or {}) if doc.exists else {}
    rods = data.get("fishing", {}).get("釣り竿", {})
    return {k: bool(rods.get(k, False)) for k in ("blue", "green", "red")}


def buy_fishing_rod(user_id: str, rod_type: str, cost: int) -> str:
    """Returns "bought", "already_owned", or "insufficient"."""
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        rods = data.get("fishing", {}).get("釣り竿", {})
        if rods.get(rod_type, False):
            return "already_owned"

        pts = int(data.get("points", {}).get("わくせい", 0))
        if pts < cost:
            return "insufficient"

        transaction.update(ref, {
            "points.わくせい": pts - cost,
            f"fishing.釣り竿.{rod_type}": True,
        })
        return "bought"

    return _tx(db.transaction(), ref)


def sell_fish(user_id: str, sell_price: int) -> int:
    """釣った魚をその場で売却し、更新後の所持ポイントを返す。"""
    ref = _user_ref(user_id)

    @firestore.transactional
    def _tx(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() if doc.exists else {}
        pts = int(data.get("points", {}).get("わくせい", 0)) + sell_price
        transaction.update(ref, {"points.わくせい": pts})
        return pts

    return _tx(db.transaction(), ref)
