from dotenv import load_dotenv
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
from sqlalchemy.ext.declarative import declarative_base

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
    # This avoids the "got None" error by providing a dummy sqlite URL
    # so the app can at least start (though DB features won't work)
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
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create tables immediately
Base.metadata.create_all(bind=engine)
def generate_uuid7():
    return str(uuid6.uuid7())
def get_age_group(age: int) -> str:
    if 0 <= age <= 12: return "child"
    if 13 <= age <= 19: return "teenager"
    if 20 <= age <= 59: return "adult"
    return "senior"
app = FastAPI()

# REQUIREMENT: CORS header Access-Control-Allow-Origin: *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            sample_size=g_data["count"],
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
        "sample_size": profile.sample_size,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
    }

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
async def get_all_profiles(
    gender: str = Query(None),
    country_id: str = Query(None),
    age_group: str = Query(None)
):
    db = SessionLocal()
    try:
        query = db.query(Profile)

        # Apply optional filters (using .ilike for case-insensitive matching)
        if gender:
            query = query.filter(Profile.gender.ilike(gender))
        if country_id:
            query = query.filter(Profile.country_id.ilike(country_id))
        if age_group:
            query = query.filter(Profile.age_group.ilike(age_group))

        profiles = query.all()
        
        return {
            "status": "success",
            "count": len(profiles),
            "data": [serialize_profile(p) for p in profiles]
        }
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