```
# Gender Classifier API

A high-performance FastAPI service that predicts the gender of a given name by interfacing with the Genderize.io API. Built as part of a backend engineering task.

## 🚀 Features
- **Real-time Classification**: Fetches data from Genderize.io.
- **Confidence Logic**: Automatically flags predictions as confident if probability is ≥ 0.7 and sample size is ≥ 100.
- **Input Validation**: Strict handling of missing or invalid name parameters.
- **CORS Enabled**: Configured for cross-origin requests (`Access-Control-Allow-Origin: *`).
- **Asynchronous**: Built using `async/await` for high concurrency and low latency.

## 🛠 Tech Stack
- **Framework:** FastAPI
- **Server:** Uvicorn
- **HTTP Client:** HTTPX (Async)
- **Language:** Python 3.9+

## 📥 Installation & Local Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-link>
   cd gender-classifier
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`.

## 📡 API Usage

### Classify Name
**Endpoint:** `GET /api/classify`

**Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | Yes | The name you want to classify. |

**Example Request:**
`GET /api/classify?name=peter`

**Success Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "name": "peter",
    "gender": "male",
    "probability": 1,
    "sample_size": 1346866,
    "is_confident": true,
    "processed_at": "2026-04-10T14:46:02Z"
  }
}
```

## ⚠️ Error Handling
All errors return a consistent JSON structure:
```json
{
  "status": "error",
  "message": "<description of the error>"
}
```
- **400 Bad Request**: Missing or empty name.
- **422 Unprocessable Entity**: Invalid input type.
- **502 Bad Gateway**: External API (Genderize) failure.
```
