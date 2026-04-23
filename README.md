
# Insighta Labs: Intelligence Query Engine (Stage 2)

A high-performance demographic intelligence system that enables advanced slicing, dicing, and natural language querying of person profiles. Built with FastAPI and PostgreSQL.

## 🚀 Live API
- **Base URL**: https://gender-classifier-production.up.railway.app

## 🛠 Features (Stage 2 Updates)
- **Data Seeding**: Pre-loaded with 2026 intelligence profiles with duplicate prevention.
- **Advanced Querying**: Support for multi-parameter filtering, sorting, and pagination.
- **Natural Language Search**: Rule-based English query parsing into database filters.
- **UUID v7 Implementation**: Time-ordered unique identifiers for optimal indexing.
- **Persistence**: Full PostgreSQL integration with SQLAlchemy ORM.

## 📡 API Endpoints

### 1. Get All Profiles (Advanced)
**GET** `/api/profiles`
Supports filtering, sorting, and pagination.
- **Filters**: `gender`, `age_group`, `country_id`, `min_age`, `max_age`, `min_gender_probability`, `min_country_probability`
- **Sorting**: `sort_by` (age, created_at, gender_probability) | `order` (asc, desc)
- **Pagination**: `page` (default: 1), `limit` (default: 10, max: 50)

*Example:* `/api/profiles?gender=male&min_age=25&sort_by=age&order=desc`

### 2. Natural Language Search
**GET** `/api/profiles/search?q={query}`
*Example:* `/api/profiles/search?q=young males from nigeria`

---

## 🧠 Natural Language Parser (NLP) Approach

The search engine uses a **Rule-Based Tokenization and Pattern Matching** approach to interpret plain English. It avoids the latency of LLMs by using pre-defined mappings and Regular Expressions (Regex).

### Supported Keywords & Logic:
- **Gender**: Matches `male`, `males`, `man`, `men` → `gender=male`; `female`, `females`, `woman`, `women` → `gender=female`.
- **Age Categories**: 
  - `young` maps to ages **16–24**.
  - `child`, `teenager`, `adult`, `senior` map to their respective `age_group` fields.
- **Comparison Logic**: 
  - Keywords like `above`, `over`, `older than` followed by a number are parsed using Regex to set `min_age`.
  - Keywords like `below`, `under`, `younger than` set `max_age`.
- **Geography**: Uses a dictionary-based lookup for common country names (e.g., "Nigeria", "Kenya") and converts them to ISO `country_id` (NG, KE).

### Limitations:
- **Multi-Country Logic**: The parser currently handles the first country identified (e.g., "people from Nigeria and Kenya" will only filter for Nigeria).
- **Negation**: It does not understand "not" or "except" (e.g., "everyone except males").
- **Complex Range**: It handles "above 30" or "below 20", but not complex overlaps like "between 20 and 30" unless explicitly filtered via the standard GET endpoint.
- **Fuzzy Matching**: Country names must be spelled correctly to be identified.

---

## ⚙️ Setup & Installation
1. **Clone & Install**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Database Seeding**:
   The app automatically seeds the `seed_profiles.json` on startup if the records do not already exist.
3. **Environment**:
   Ensure `DATABASE_URL` is set in your `.env` file or Railway variables.

## ⚠️ Error Handling
- **400**: Missing query parameter or unable to interpret NL query.
- **422**: Invalid parameter types (e.g., passing text to `min_age`).
- **404**: Specific profile not found.
```

***

### Checklist for your `main.py` before you push:
1.  **Ensure `country_name` exists** in your `Profile` class.
2.  **Verify the `total` count** in the response for `/api/profiles` (it should reflect the total matching records in the DB, not just the page limit).
3.  **Check for "young"**: In your NLP code, make sure `young` specifically filters for `min_age=16` and `max_age=24`.
4.  **CORS**: Confirm `allow_origins=["*"]` is active so the grading bot doesn't get blocked.