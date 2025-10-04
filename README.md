# 🧠 AI Appointment Scheduler Assistant

### A FastAPI-based AI backend that extracts structured appointment details (department, date, time) from both **text** and **images** using **Google Cloud Vision API** and **NLP entity extraction**.

---

## 📘 Overview

This project is built for **Problem Statement 5 – AI-Powered Appointment Scheduler Assistant**.

It processes natural language appointment requests or handwritten images and converts them into structured JSON data for scheduling systems.

**Pipeline:**  
OCR (Vision API) ➜ Entity Extraction ➜ Normalization ➜ Final Structured Output with Guardrails.

---

## 🧩 Features

- 🧾 **Text or Image Input:** Handles both plain text and noisy handwritten images.
- 🔍 **OCR via Google Vision API:** High-accuracy handwriting recognition.
- 🧠 **Entity Extraction:** Identifies date/time phrases and medical department.
- ⏱️ **Date Normalization:** Converts “next Friday” → `2025-10-10` (ISO format, Asia/Kolkata).
- 🧰 **Guardrails:** Detects ambiguity or missing info (`needs_clarification` response).
- ⚡ **FastAPI Backend:** Lightweight, async, production-ready architecture.

---

## 🏗️ Architecture

            ┌───────────────────────────────┐
            │   Client Request (Text/Image) │
            └────────────┬──────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Google Vision OCR   │
              │ (if image input)     │
              └──────────────────────┘
                         │
                         ▼
           ┌───────────────────────────────┐
           │   Entity Extraction Module    │
           │  → Department, Date, Time     │
           └───────────────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────┐
          │   Normalization (dateparser)    │
          │  → ISO Date/Time (Asia/Kolkata) │
          └─────────────────────────────────┘
                         │
                         ▼
       ┌────────────────────────────────────────┐
       │ Guardrail Check → Missing/Ambiguous?   │
       └────────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────────┐   
          │       ✅ Final JSON Response     │
          └──────────────────────────────────┘


---

## ⚙️ Setup Instructions

### 1️⃣ Clone repository

git clone https://github.com/Cshraddha153/AI-Appointment-Scheduler.git
cd AI-Appointment-Scheduler

### 2️⃣ Create virtual environment & install dependencies
python -m venv venv

(Windows)-> venv\Scripts\activate      

pip install fastapi uvicorn google-cloud-vision dateparser python-multipart

### 3️⃣ Configure Google Vision credentials
Set your Google Cloud Vision API key path: set GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your-key.json"



## 🧪 API Endpoints (Testing with Postman)

## ✅ 1. Start Your API Server
In your terminal:
uvicorn AI_Powered_Appointment_Scheduler_Assistant_(Google_Vision):app --reload

## 🩺 2. Test Health Endpoint
Method: GET <br>
URL: http://127.0.0.1:8000/health

Steps:

1. Open Postman

2. Set method to GET

3. Enter URL → http://127.0.0.1:8000/health

4. Click Send

**Response:**

{
  "status": "healthy",
  "timestamp": "2025-10-04T08:35:22.312Z"
}

## ✍️ 3. Test Text Parsing Endpoint

Method: POST <br>
URL: http://127.0.0.1:8000/parse_text

Steps:

1. Go to Body → raw → JSON

2. Paste this:

{
  "text": "Book dentist next Friday at 3pm"
}


3. Click Send

**Response:**

{
  "step1_raw": {"raw_text": "Book dentist next Friday at 3pm", "confidence": 0.95},
  "step2_entities": {
    "entities": {"date_phrase": "next friday", "time_phrase": "3pm", "department": "Dentistry"},
    "entities_confidence": 0.85
  },
  "step3_normalized": {
    "normalized": {"date": "2025-10-10", "time": "15:00", "tz": "Asia/Kolkata"},
    "normalization_confidence": 0.9
  },
  "final": {
    "appointment": {"department": "Dentistry", "date": "2025-10-10", "time": "15:00", "tz": "Asia/Kolkata"},
    "status": "ok"
  }
}

<br>
<img width="1390" height="935" alt="input_text" src="https://github.com/user-attachments/assets/cd52523f-4b07-4593-807c-24fa3542dae4" />
<br>

## 🖼️ 4. Test Image Parsing Endpoint

Method: POST <br>
URL: http://127.0.0.1:8000/parse_image

Steps:

1. Go to Body → form-data

2. Add a key named file

3. Change type to File

4. Upload your image file (e.g., handwritten_image_dentist.jpeg)

5. Click Send

**Expected Response:**

{
  "step1_raw": {"raw_text": "Book dermatologist tomorrow at 10 am", "confidence": 0.93},
  "step2_entities": {
    "entities": {"date_phrase": "tomorrow", "time_phrase": "10 am", "department": "Dermatology"},
    "entities_confidence": 0.85
  },
  "step3_normalized": {
    "normalized": {"date": "2025-10-05", "time": "10:00", "tz": "Asia/Kolkata"},
    "normalization_confidence": 0.9
  },
  "final": {
    "appointment": {"department": "Dermatology", "date": "2025-10-05", "time": "10:00", "tz": "Asia/Kolkata"},
    "status": "ok"
  }
}

<br>
<img width="1698" height="1005" alt="input_imape" src="https://github.com/user-attachments/assets/61a10fee-8b29-4764-a4ea-bba5ee98ffca" />

<br>


## ⚠️ 5. Guardrail (Ambiguous Input Example)

Method: POST <br>
URL: http://127.0.0.1:8000/parse_text

Body (JSON):
{
  "text": "Checkup at 5pm"
}

Response:
{
    "status": "needs_clarification",
    "message": "Ambiguous/missing: department"
}

<br>
<img width="1804" height="818" alt="Guardrail" src="https://github.com/user-attachments/assets/80ea989d-e87b-4b26-b278-7c906e05b270" />
<br>



