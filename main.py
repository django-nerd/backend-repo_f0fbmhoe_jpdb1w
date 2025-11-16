import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Fragrance, Review, UserProfile, CartItem, Order, QuizAnswer

app = FastAPI(title="Luxe Perfume API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Helpers
# -------------------------

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc


# -------------------------
# Health
# -------------------------
@app.get("/")
def read_root():
    return {"message": "Luxe Perfume Backend Ready"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------------------------
# Catalog Endpoints
# -------------------------

@app.post("/api/fragrances", response_model=dict)
def create_fragrance(fragrance: Fragrance):
    fid = create_document("fragrance", fragrance)
    return {"id": fid}


@app.get("/api/fragrances", response_model=List[dict])
def list_fragrances(
    q: Optional[str] = None,
    family: Optional[str] = Query(None, description="floral|woody|citrus|oriental"),
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    gender: Optional[str] = None,
    featured: Optional[bool] = None,
    new_arrival: Optional[bool] = None,
    limit: int = 24
):
    filt: Dict[str, Any] = {}
    if q:
        filt["name"] = {"$regex": q, "$options": "i"}
    if family:
        filt["families"] = family
    if occasion:
        filt["occasion"] = occasion
    if season:
        filt["season"] = season
    if gender:
        filt["gender"] = gender
    if featured is not None:
        filt["featured"] = featured
    if new_arrival is not None:
        filt["new_arrival"] = new_arrival

    docs = get_documents("fragrance", filt, limit)
    return [serialize(d) for d in docs]


@app.get("/api/fragrances/{fid}", response_model=dict)
def get_fragrance(fid: str):
    doc = db["fragrance"].find_one({"_id": oid(fid)})
    if not doc:
        raise HTTPException(404, "Fragrance not found")
    return serialize(doc)


@app.get("/api/fragrances/{fid}/similar", response_model=List[dict])
def similar_fragrances(fid: str, limit: int = 8):
    doc = db["fragrance"].find_one({"_id": oid(fid)})
    if not doc:
        raise HTTPException(404, "Fragrance not found")
    fam = doc.get("families", [])
    query = {"families": {"$in": fam}, "_id": {"$ne": doc["_id"]}}
    sims = db["fragrance"].find(query).limit(limit)
    return [serialize(d) for d in sims]


# -------------------------
# Reviews
# -------------------------

@app.post("/api/reviews", response_model=dict)
def add_review(review: Review):
    rid = create_document("review", review)
    # update aggregate rating
    fr_id = review.fragrance_id
    cursor = db["review"].find({"fragrance_id": fr_id})
    ratings = [r.get("rating", 0) for r in cursor]
    if ratings:
        avg = sum(ratings) / len(ratings)
        db["fragrance"].update_one({"_id": oid(fr_id)}, {"$set": {"rating_average": avg, "rating_count": len(ratings)}})
    return {"id": rid}


@app.get("/api/reviews/{fragrance_id}", response_model=List[dict])
def get_reviews(fragrance_id: str):
    docs = get_documents("review", {"fragrance_id": fragrance_id}, None)
    return [serialize(d) for d in docs]


# -------------------------
# Quiz & Recommendations
# -------------------------

@app.post("/api/quiz/recommendations", response_model=List[dict])
def quiz_recommendations(answers: QuizAnswer):
    filt: Dict[str, Any] = {}
    if answers.gender:
        filt["gender"] = answers.gender
    if answers.season:
        filt["season"] = answers.season
    if answers.occasion:
        filt["occasion"] = answers.occasion
    if answers.preferences:
        filt["families"] = {"$in": answers.preferences}
    docs = get_documents("fragrance", filt, 12)
    return [serialize(d) for d in docs]


# -------------------------
# User, Favorites, Cart (basic)
# -------------------------

@app.post("/api/users", response_model=dict)
def upsert_user(profile: UserProfile):
    existing = db["userprofile"].find_one({"email": profile.email})
    if existing:
        db["userprofile"].update_one({"_id": existing["_id"]}, {"$set": profile.model_dump()})
        return {"id": str(existing["_id"])}
    uid = create_document("userprofile", profile)
    return {"id": uid}


@app.post("/api/favorites/{user_email}/{fragrance_id}")
def toggle_favorite(user_email: str, fragrance_id: str):
    prof = db["userprofile"].find_one({"email": user_email})
    if not prof:
        raise HTTPException(404, "User not found")
    favs = prof.get("favorites", [])
    if fragrance_id in favs:
        favs.remove(fragrance_id)
    else:
        favs.append(fragrance_id)
    db["userprofile"].update_one({"_id": prof["_id"]}, {"$set": {"favorites": favs}})
    return {"favorites": favs}


@app.get("/api/favorites/{user_email}", response_model=List[str])
def get_favorites(user_email: str):
    prof = db["userprofile"].find_one({"email": user_email})
    if not prof:
        return []
    return prof.get("favorites", [])


# -------------------------
# Search with autocomplete
# -------------------------

@app.get("/api/search", response_model=List[dict])
def search(q: str, limit: int = 8):
    docs = db["fragrance"].find({"name": {"$regex": q, "$options": "i"}}).limit(limit)
    return [serialize(d) for d in docs]


# -------------------------
# Seed minimal sample data if empty (to demo UI)
# -------------------------
@app.post("/api/seed")
def seed():
    count = db["fragrance"].count_documents({})
    if count > 0:
        return {"inserted": 0}
    samples = [
        Fragrance(
            name="Noir Élite",
            brand="Maison Éclat",
            price=289,
            gender="unisex",
            season=["fall", "winter"],
            occasion=["evening", "date"],
            notes_top=["bergamot", "pink pepper"],
            notes_heart=["rose", "saffron"],
            notes_base=["oud", "sandalwood", "amber"],
            families=["oriental", "woody"],
            images=[],
            thumbnail="https://images.unsplash.com/photo-1556228578-8ea1fc0f8b2e?w=800&auto=format&fit=crop",
            featured=True,
            new_arrival=True,
            profile={"floral": 0.5, "woody": 0.9, "citrus": 0.2, "spicy": 0.7, "sweet": 0.3}
        ),
        Fragrance(
            name="Lumière Blanche",
            brand="Atelier de Paris",
            price=210,
            gender="female",
            season=["spring", "summer"],
            occasion=["daytime", "office"],
            notes_top=["pear", "mandarin"],
            notes_heart=["jasmine", "orange blossom"],
            notes_base=["musk", "cedar"],
            families=["floral", "citrus"],
            thumbnail="https://images.unsplash.com/photo-1585386959984-a41552231605?w=800&auto=format&fit=crop",
            featured=True
        ),
        Fragrance(
            name="Verde Sera",
            brand="Casa Botanica",
            price=185,
            gender="male",
            season=["summer"],
            occasion=["casual"],
            notes_top=["lime", "mint"],
            notes_heart=["green tea", "neroli"],
            notes_base=["vetiver"],
            families=["citrus", "fresh"],
            thumbnail="https://images.unsplash.com/photo-1541643600914-78b084683601?w=800&auto=format&fit=crop",
            new_arrival=True
        )
    ]
    inserted = 0
    for s in samples:
        create_document("fragrance", s)
        inserted += 1
    return {"inserted": inserted}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
