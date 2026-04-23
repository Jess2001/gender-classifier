from dotenv import load_dotenv
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
load_dotenv()
from fastapi import FastAPI, Query, Response, status, Body
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime, timezone
import os
import asyncio
import uuid6
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
import json
import re

# 1. Database Setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # This helps you debug if the variable is missing
    print("⚠️ WARNING: DATABASE_URL is not set. Check your .env file or Railway variables.")
    # For local testing only, you could hardcode it here (NOT recommended for GitHub)
    # DATABASE_URL = "your-url-here" 
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
# Now create the engine only if we have a URL
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///./test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 2. The Model
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    gender = Column(String)
    gender_probability = Column(Float)
    #sample_size = Column(Integer, nullable=True)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_name = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create tables immediately
Base.metadata.create_all(bind=engine)
def generate_uuid7():
    return str(uuid6.uuid7())
def seed_data():
    
    db = SessionLocal()
    try:
        existing_count = db.query(Profile).count()
        if existing_count >= 2026:
            print("✨ Database already seeded. Skipping...")
            return
        if not os.path.exists("seed_profiles.json"):
            return

        with open("seed_profiles.json", "r") as f:
            data = json.load(f)
            profiles_data = data.get("profiles", [])

        if not profiles_data:
            return

        print(f"📦 Starting optimized bulk seed of {len(profiles_data)} profiles...")

        # 1. Prepare all values into a list of dictionaries
        # We generate the UUIDs here in Python so we can send them in bulk
        values = []
        for p in profiles_data:
            p_copy = p.copy()
            p_copy['id'] = generate_uuid7()
            values.append(p_copy)

        # 2. Use a single bulk INSERT statement with ON CONFLICT
        stmt = insert(Profile).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=['name'])
        
        db.execute(stmt)
        db.commit()
        
        print("✅ Bulk seeding complete!")

    except Exception as e:
        print(f"❌ Seeding error: {e}")
        db.rollback()
    finally:
        db.close()

def get_age_group(age: int) -> str:
    if 0 <= age <= 12: return "child"
    if 13 <= age <= 19: return "teenager"
    if 20 <= age <= 59: return "adult"
    return "senior"
app = FastAPI()
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid query parameters"}
    )
# REQUIREMENT: CORS header Access-Control-Allow-Origin: *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Call this before app starts
@app.on_event("startup")
async def startup_event():
    # This runs as soon as the server starts, 
    # but doesn't block the actual code from loading
    seed_data()

@app.post("/api/profiles", status_code=201)
async def create_profile(payload: dict = Body(...)):
    name = payload.get("name")
    
    # 1. Validation (Requirement: 400 error)
    if not name or not str(name).strip():
        return Response(
            content='{"status": "error", "message": "Missing or empty name"}',
            status_code=400, media_type="application/json"
        )

    db = SessionLocal()
    try:
        # 2. Idempotency Check (Does it exist?)
        existing = db.query(Profile).filter(Profile.name == name.lower()).first()
        if existing:
            return {
                "status": "success",
                "message": "Profile already exists",
                "data": serialize_profile(existing)
            }

        # 3. Call 3 APIs in Parallel (Requirement: Multi-API Integration)
        async with httpx.AsyncClient() as client:
            # We fire all three at once!
            g_req, a_req, n_req = await asyncio.gather(
                client.get(f"https://api.genderize.io?name={name}"),
                client.get(f"https://api.agify.io?name={name}"),
                client.get(f"https://api.nationalize.io?name={name}")
            )

        # 4. Error Handling for External APIs (Requirement: 502)
        g_data = g_req.json()
        a_data = a_req.json()
        n_data = n_req.json()

        if not g_data.get("gender") or g_data.get("count") == 0:
            return Response(status_code=502, content='{"status": "error", "message": "Genderize returned an invalid response"}', media_type="application/json")
        
        if a_data.get("age") is None:
            return Response(status_code=502, content='{"status": "error", "message": "Agify returned an invalid response"}', media_type="application/json")

        if not n_data.get("country"):
            return Response(status_code=502, content='{"status": "error", "message": "Nationalize returned an invalid response"}', media_type="application/json")

        # 5. Extract Top Country (Nationality Logic)
        top_country = max(n_data["country"], key=lambda x: x["probability"])

        # 6. Create the Database Record (Persistence)
        new_profile = Profile(
            id=generate_uuid7(),
            name=name.lower(),
            gender=g_data["gender"],
            gender_probability=g_data["probability"],
            #sample_size=g_data["count"],
            age=a_data["age"],
            age_group=get_age_group(a_data["age"]),
            country_id=top_country["country_id"],
            country_probability=top_country["probability"]
        )
        
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        return {
            "status": "success",
            "data": serialize_profile(new_profile)
        }

    finally:
        db.close()

def serialize_profile(profile: Profile):
    return {
        "id": profile.id,
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        #"sample_size": profile.sample_size,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_name": profile.country_name,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
async def fetch_profiles_from_db(
    db, gender=None, age_group=None, country_id=None, 
    min_age=None, max_age=None, sort_by="created_at", 
    order="desc", page=1, limit=10,min_gender_probability=None, min_country_probability=None,
):
    query = db.query(Profile)

    # Apply Filters
    if gender: query = query.filter(Profile.gender == gender.lower())
    if age_group: query = query.filter(Profile.age_group == age_group.lower())
    if country_id: query = query.filter(Profile.country_id == country_id.upper())
    if min_age is not None: query = query.filter(Profile.age >= min_age)
    if max_age is not None: query = query.filter(Profile.age <= max_age)
    if min_gender_probability: query = query.filter(Profile.gender_probability >= min_gender_probability)
    if min_country_probability: query = query.filter(Profile.country_probability >= min_country_probability)

    # Sorting - We ensure sort_by is a string here
    column = getattr(Profile, str(sort_by), Profile.created_at)
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    total = query.count()
    results = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize_profile(p) for p in results]
    }
@app.get("/api/profiles/search")
async def nl_search(q: str = Query(...), page: int = 1, limit: int = 10):
    if not q.strip():
        return Response(status_code=400, content='{"status": "error", "message": "Query cannot be empty"}')

    params = {"page": page, "limit": limit}
    q = q.lower()
    filters = {
        "gender": None,
        "min_age": None,
        "max_age": None,
        "country_id": None,
        "age_group": None
    }
    # Rule-based mapping examples
    mentions_female = any(w in q for w in ["female", "woman", "women"])
    mentions_male = any(w in q for w in ["male", "man", "men"])
    
    if mentions_female and not mentions_male:
        filters["gender"] = "female"
    elif mentions_male and not mentions_female:
        filters["gender"] = "male"
    
    if "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24
    for group in ["child", "teenager", "adult", "senior"]:
        if group in q:
            filters["age_group"] = group
    # Extracting "above 30" using regex
    above_match = re.search(r"(?:above|older than|over|greater than)\s*(\d+)", q)
    if above_match:
        filters["min_age"] = int(above_match.group(1))
        
    # Optional: Add below logic to be safe
    below_match = re.search(r"(?:below|under|younger than|less than)\s*(\d+)", q)
    if below_match:
        filters["max_age"] = int(below_match.group(1))

    # Country mapping (Simplified example)
    countries = {"nigeria": "NG", "kenya": "KE", "angola": "AO", "ghana": "GH"}
    for name, code in countries.items():
        if name in q:
            filters["country_id"] = code

    # Check if we successfully interpreted anything
    if not any(v is not None for v in filters.values()):
         return Response(status_code=400, content='{"status": "error", "message": "Unable to interpret query"}', media_type="application/json")
    # Reuse the logic from get_profiles
    db = SessionLocal()
    try:
        # Call the helper function directly
        return await fetch_profiles_from_db(
            db, page=page, limit=limit, **filters
        )
    finally:
        db.close()

@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return Response(
                content='{"status": "error", "message": "Profile not found"}',
                status_code=404, media_type="application/json"
            )
        return {"status": "success", "data": serialize_profile(profile)}
    finally:
        db.close()


@app.get("/api/profiles")
async def get_profiles(
    gender: str = Query(None),
    age_group: str = Query(None),
    country_id: str = Query(None),
    min_age: int = Query(None),
    max_age: int = Query(None),
    min_gender_probability: float = Query(None),
    min_country_probability: float = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    db = SessionLocal()
    try:
        return await fetch_profiles_from_db(
            db, gender, age_group, country_id, 
            min_age, max_age, sort_by, order, page, limit,
            min_gender_probability, min_country_probability
        )
    finally:
        db.close()


@app.delete("/api/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: str):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return Response(
                content='{"status": "error", "message": "Profile not found"}',
                status_code=404, media_type="application/json"
            )
        
        db.delete(profile)
        db.commit()
        return Response(status_code=204)
    finally:
        db.close()