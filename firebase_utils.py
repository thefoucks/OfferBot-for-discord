import firebase_admin
from firebase_admin import credentials, firestore

# טען מפתח שירות JSON
cred = credentials.Certificate("C:/Users/segev/OneDrive/שולחן העבודה/VS/OfferBot/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def save_channel(guild_id: int, channel_id: int):
    db.collection("settings").document(str(guild_id)).set({"channel_id": channel_id}, merge=True)

def get_channel(guild_id: int):
    doc = db.collection("settings").document(str(guild_id)).get()
    return doc.to_dict().get("channel_id") if doc.exists else None

def save_crew_roles(guild_id: int, roles: list[int]):
    db.collection("settings").document(str(guild_id)).set({"crew_roles": roles}, merge=True)

def get_crew_roles(guild_id: int):
    doc = db.collection("settings").document(str(guild_id)).get()
    return doc.to_dict().get("crew_roles", []) if doc.exists else []

def save_thresholds(guild_id: int, v: dict, x: dict):
    db.collection("settings").document(str(guild_id)).set({
        "v_thresholds": v,
        "x_thresholds": x
    }, merge=True)

def get_thresholds(guild_id: int):
    doc = db.collection("settings").document(str(guild_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("v_thresholds", {}), data.get("x_thresholds", {})
    return {}, {}

def save_ticket(guild_id: int, ticket_channel_id: int, ticket_data: dict):
    db.collection("tickets").document(f"{guild_id}_{ticket_channel_id}").set(ticket_data)

def get_ticket(guild_id: int, ticket_channel_id: int):
    doc = db.collection("tickets").document(f"{guild_id}_{ticket_channel_id}").get()
    return doc.to_dict() if doc.exists else None

def delete_ticket(guild_id: int, ticket_channel_id: int):
    db.collection("tickets").document(f"{guild_id}_{ticket_channel_id}").delete()

def increment_accepted_count(user_id: int):
    ref = db.collection("users").document(str(user_id))
    ref.set({"accepted": firestore.Increment(1)}, merge=True)

def get_accepted_count(user_id: int):
    doc = db.collection("users").document(str(user_id)).get()
    return doc.to_dict().get("accepted", 0) if doc.exists else 0
