"""
Database Schemas for Luxury Perfume E‑commerce

Each Pydantic model below maps to a MongoDB collection (collection name is the lowercase of the class name).
Define schemas here BEFORE creating/using collections in routes.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# ----------------------------
# Core Domain Schemas
# ----------------------------

class Fragrance(BaseModel):
    name: str = Field(..., description="Fragrance display name")
    brand: str = Field(..., description="Brand name")
    price: float = Field(..., ge=0, description="Price in USD")
    gender: Optional[str] = Field(None, description="male | female | unisex")
    season: Optional[List[str]] = Field(default=None, description="seasons e.g. spring, summer, fall, winter")
    occasion: Optional[List[str]] = Field(default=None, description="e.g. casual, office, date, evening")
    notes_top: List[str] = Field(default_factory=list, description="Top notes")
    notes_heart: List[str] = Field(default_factory=list, description="Heart/Middle notes")
    notes_base: List[str] = Field(default_factory=list, description="Base notes")
    families: List[str] = Field(default_factory=list, description="e.g. floral, woody, citrus, oriental")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    thumbnail: Optional[str] = Field(None, description="Primary image URL")
    rating_average: float = Field(0.0, ge=0, le=5)
    rating_count: int = Field(0, ge=0)
    stock: int = Field(50, ge=0)
    featured: bool = Field(False)
    new_arrival: bool = Field(False)
    pyramid: Optional[Dict[str, List[str]]] = Field(default=None, description="Optional explicit notes map")
    profile: Optional[Dict[str, float]] = Field(default=None, description="Radar profile map, keys: fresh, floral, woody, spicy, citrus, sweet, resinous, powdery")

class Review(BaseModel):
    fragrance_id: str = Field(...)
    user_name: str = Field("Anonymous")
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class UserProfile(BaseModel):
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    favorites: List[str] = Field(default_factory=list)

class CartItem(BaseModel):
    user_id: str
    fragrance_id: str
    quantity: int = Field(1, ge=1, le=10)

class Order(BaseModel):
    user_id: str
    items: List[Dict]  # {fragrance_id, price, quantity}
    total_amount: float
    status: str = Field("pending")
    payment_provider: Optional[str] = None
    payment_intent_id: Optional[str] = None

class QuizAnswer(BaseModel):
    gender: Optional[str] = None
    season: Optional[str] = None
    occasion: Optional[str] = None
    preferences: List[str] = Field(default_factory=list, description="note families preferred e.g. floral, woody")
