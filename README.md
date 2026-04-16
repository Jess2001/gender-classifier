
# Data Persistence & Profile API (Stage 1)

A robust backend system that aggregates demographic data from three external APIs, persists results in a PostgreSQL database, and provides full CRUD functionality with built-in idempotency.

## 🚀 Live Demo
- **Base URL**: [https://gender-classifier-production.up.railway.app]

## 🛠 Features
- **Data Persistence**: Uses PostgreSQL to store user profiles, reducing redundant external API calls.
- **Idempotency**: Automatically detects if a name has already been processed and returns the existing record.
- **Multi-API Integration**: Concurrently fetches data from:
  - **Genderize.io**: Gender prediction and probability.
  - **Agify.io**: Age estimation.
  - **Nationalize.io**: Nationality/Country probability.
- **Classification Logic**: 
  - Groups age into categories (child, teenager, adult, senior).
  - Determines the most probable country of origin.
- **UUID v7**: Implements the latest time-ordered UUID standard for primary keys.
- **Advanced Filtering**: Case-insensitive search by gender, country_id, and age_group.

## 📡 API Endpoints

### 1. Create/Retrieve Profile
**POST** `/api/profiles`  
*Body:* `{"name": "ella"}`  
*Behavior:* Fetches from APIs if new; returns existing record if name is already in DB.

### 2. Get All Profiles
**GET** `/api/profiles`  
*Optional Filters:* `?gender=male&country_id=NG&age_group=adult`

### 3. Get Single Profile
**GET** `/api/profiles/{id}`

### 4. Delete Profile
**DELETE** `/api/profiles/{id}`

## ⚙️ Tech Stack
- **Framework:** FastAPI
- **Database:** PostgreSQL (Relational)
- **ORM:** SQLAlchemy
- **ID Standard:** UUID v7 (via `uuid6`)
- **HTTP Client:** HTTPX (Asynchronous)

## 📥 Installation & Local Setup

1. **Clone & Navigate:**
   ```bash
   git clone <your-repo-link>
   cd gender-classifier
   ```

2. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```text
   DATABASE_URL=postgresql://user:password@host:port/dbname
   ```

3. **Install & Run:**
   ```bash
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## ⚠️ Error Responses
- **400 Bad Request**: Missing or empty name.
- **404 Not Found**: Profile ID does not exist.
- **502 Bad Gateway**: One of the upstream APIs (Agify/Genderize/Nationalize) failed or returned invalid data.
