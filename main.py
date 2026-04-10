from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime, timezone

app = FastAPI()

# Requirement: CORS must be open (*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/classify")
async def classify_name(name: str = Query(None)):
    # 1. Validation: Is the name missing or empty?
    if not name or name.strip() == "":
        return Response(
            content='{"status": "error", "message": "Missing or empty name"}',
            status_code=400,
            media_type="application/json"
        )

    # 2. Call the External API
    try:
        async with httpx.AsyncClient() as client:
            # We fetch data from Genderize
            external_res = await client.get(f"https://api.genderize.io?name={name}")
            data = external_res.json()

        # 3. Handle Genderize Edge Cases (No result found)
        if data.get("gender") is None or data.get("count") == 0:
            return {
                "status": "error", 
                "message": "No prediction available for the provided name"
            }

        # 4. Process the Data (Rename count and check confidence)
        prob = data.get("probability", 0)
        size = data.get("count", 0)
        
        # Rule: probability >= 0.7 AND sample_size >= 100
        is_confident = prob >= 0.7 and size >= 100
        
        # Timestamp in ISO 8601 format
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 5. Return the Success Response
        return {
            "status": "success",
            "data": {
                "name": name,
                "gender": data.get("gender"),
                "probability": prob,
                "sample_size": size, # Renamed from 'count'
                "is_confident": is_confident,
                "processed_at": now
            }
        }

    except Exception:
        return Response(
            content='{"status": "error", "message": "Internal Server Error"}',
            status_code=500,
            media_type="application/json"
        )