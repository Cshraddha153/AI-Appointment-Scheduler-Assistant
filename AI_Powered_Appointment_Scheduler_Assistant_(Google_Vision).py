"""
AI-Powered Appointment Scheduler with Google Vision API
This version uses Google Cloud Vision for superior handwriting recognition
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import io
import os
import re
import dateparser
from datetime import datetime
from google.cloud import vision
import base64


app = FastAPI(title="AI Appointment Scheduler Assistant")

# Initialize Google Vision client
# Set up authentication => set GOOGLE_APPLICATION_CREDENTIALS="path\to\key.json"  ## Windows ##
vision_client = vision.ImageAnnotatorClient()




# -----------------------------------------------------------------------------------------
# -------------------------------- Pydantic models  ---------------------------------------
# -----------------------------------------------------------------------------------------

class RawTextResponse(BaseModel):
    raw_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)

class EntitiesResponse(BaseModel):
    entities: Dict[str, Optional[str]]
    entities_confidence: float = Field(..., ge=0.0, le=1.0)

class NormalizedResponse(BaseModel):
    normalized: Dict[str, Optional[str]]
    normalization_confidence: float = Field(..., ge=0.0, le=1.0)

class FinalAppointmentResponse(BaseModel):
    appointment: Dict[str, Any]
    status: str

class TextInput(BaseModel):
    text: str




# -----------------------------------------------------------------------------------------
# ----------------------------- Google Vision OCR -----------------------------------------
# -----------------------------------------------------------------------------------------

def google_vision_ocr(image_bytes: bytes) -> tuple[str, float]:
    """Use Google Cloud Vision API for OCR - excellent for handwriting."""
    try:
        image = vision.Image(content=image_bytes)
        
        # Use document text detection for better handwriting results
        response = vision_client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(response.error.message)
        
        # Get the full text
        text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Calculate confidence from the response
        if response.full_text_annotation and response.full_text_annotation.pages:
            confidences = []
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    if block.confidence:
                        confidences.append(block.confidence)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        else:
            avg_confidence = 0.0
        
        # Clean up the text
        text = " ".join(text.split())
        
        return text, round(avg_confidence, 2)
    
    except Exception as e:
        print(f"Google Vision Error: {str(e)}")
        return "", 0.0




# -----------------------------------------------------------------------------------------
# -------------------------- Enhanced Text Cleaning ---------------------------------------
# -----------------------------------------------------------------------------------------

def clean_ocr_text(text: str) -> str:
    """Clean OCR text with focus on common mistakes."""
    if not text:
        return ""
    
    # Normalize whitespace first
    text = " ".join(text.split())
    
    # Common replacements
    text = text.replace('@', 'at')
    text = re.sub(r'\bnxt\b', 'next', text, flags=re.IGNORECASE)
    
    return text




# -----------------------------------------------------------------------------------------
# ------------------------------- Entity Extraction --------------------------------------
# -----------------------------------------------------------------------------------------

def extract_entities_from_text(text: str) -> tuple[Dict[str, Optional[str]], float]:
    """Extract appointment entities from text."""
    lower = text.lower()
    cleaned = clean_ocr_text(text).lower()
    
    # Department detection
    dept = None
    dept_patterns = {
        'Dentistry': ['dentist', 'dental', 'tooth', 'teeth'],
        'Dermatology': ['derma', 'skin', 'dermatolog'],
        'Cardiology': ['cardio', 'heart', 'cardiac'],
        'Doctor': ['doctor', 'physician', 'gp', 'general']
    }
    
    
    for dept_name, keywords in dept_patterns.items():
        for keyword in keywords:
            if keyword in cleaned:
                dept = dept_name
                break
        if dept:
            break
    
    # Time extraction
    time_patterns = [
        r'(\d{1,2})\s*([ap])\.?m\.?',
        r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
        r'at\s+(\d{1,2})',
    ]
    
    time_phrase = None
    for pattern in time_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            time_phrase = match.group(0)
            break
    
    # Date extraction
    date_match = None
    
    # Relative dates
    if 'tomorrow' in cleaned:
        date_match = 'tomorrow'
    elif 'today' in cleaned:
        date_match = 'today'
    
    # for weekday
    if not date_match:
        weekday_pattern = r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        m = re.search(weekday_pattern, cleaned)
        if m:
            date_match = m.group(0)
    
    entities = {
        'date_phrase': date_match,
        'time_phrase': time_phrase,
        'department': dept
    }
    
    # Confidence calculation
    base = 0.5
    if date_match:
        base += 0.2
    if time_phrase:
        base += 0.2
    if dept:
        base += 0.1
    
    return entities, round(min(0.95, base), 2)




# -----------------------------------------------------------------------------------------
# -------------------------------- Normalization (Asia/Kolkata) -------------------------------------
# -----------------------------------------------------------------------------------------

def normalize_entities(entities: Dict[str, Optional[str]]) -> tuple[Dict[str, Optional[str]], float]:
    """Normalize entities to ISO format."""
    settings = {
        'TIMEZONE': 'Asia/Kolkata',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'PREFER_DATES_FROM': 'future'
    }
    
    date_phrase = entities.get('date_phrase')
    time_phrase = entities.get('time_phrase')
    
    normalized_date = None
    normalized_time = None
    conf = 0.5
    
    # Parse date
    if date_phrase:
        try:
            pd = dateparser.parse(date_phrase, settings=settings)
            if pd:
                normalized_date = pd.date().isoformat()
                conf += 0.25
        except:
            pass
    
    # Parse time
    if time_phrase:
        try:
            pt = dateparser.parse(time_phrase, settings=settings)
            if pt:
                normalized_time = pt.time().strftime('%H:%M')
                conf += 0.25
        except:
            pass
    
    return {
        'date': normalized_date,
        'time': normalized_time,
        'tz': 'Asia/Kolkata'
    }, round(min(0.90, conf), 2)




# -----------------------------------------------------------------------------------------
# --------------------------------- Guardrail / Exit Condition ----------------------------
# -----------------------------------------------------------------------------------------


def needs_clarification(entities: Dict, normalized: Dict) -> Optional[Dict]:
    """Check if any required fields are missing."""
    missing = []
    
    if not entities.get('department'):
        missing.append('department')
    if not normalized.get('date'):
        missing.append('date')
    if not normalized.get('time'):
        missing.append('time')
    
    if missing:
        return {
            'status': 'needs_clarification',
            'message': f'Ambiguous or missing: {", ".join(missing)}'
        }
    
    return None




# -----------------------------------------------------------------------------------------
# ------------------------------------ API Endpoints --------------------------------------
# -----------------------------------------------------------------------------------------

@app.get("/")
def home():
    return {"message": "AI Appointment Scheduler API with Google Vision"}



@app.post('/parse_text')
async def parse_text(input_data: TextInput):
    """Parse text input."""
    text = input_data.text
    
    if not text:
        raise HTTPException(status_code=400, detail="Text field is required")
    
    # Process the pipeline
    raw = RawTextResponse(raw_text=text.strip(), confidence=0.95)
    entities, ent_conf = extract_entities_from_text(text)
    normalized, norm_conf = normalize_entities(entities)
    
    guard = needs_clarification(entities, normalized)
    if guard:
        return JSONResponse(status_code=200, content=guard)
    
    appointment = {
        'department': entities.get('department'),
        'date': normalized.get('date'),
        'time': normalized.get('time'),
        'tz': normalized.get('tz')
    }
    
    return {
        'step1_raw': raw.dict(),
        'step2_entities': {'entities': entities, 'entities_confidence': ent_conf},
        'step3_normalized': {'normalized': normalized, 'normalization_confidence': norm_conf},
        'final': {'appointment': appointment, 'status': 'ok'}
    }



@app.post('/parse_image')
async def parse_image(file: UploadFile = File(...)):
    """Parse image using Google Vision OCR."""
    contents = await file.read()
    
    try:
        # Use Google Vision for OCR
        text, ocr_conf = google_vision_ocr(contents)
        
        if not text:
            return JSONResponse(
                status_code=200,
                content={
                    'status': 'needs_clarification',
                    'message': 'No text found in image.'
                }
            )
        
        # Process through the pipeline
        raw = RawTextResponse(raw_text=text, confidence=ocr_conf)
        entities, ent_conf = extract_entities_from_text(text)
        normalized, norm_conf = normalize_entities(entities)
        
        guard = needs_clarification(entities, normalized)
        if guard:
            guard['extracted_text'] = text
            return JSONResponse(status_code=200, content=guard)
        
        appointment = {
            'department': entities.get('department'),
            'date': normalized.get('date'),
            'time': normalized.get('time'),
            'tz': normalized.get('tz')
        }
        
        return {
            'step1_raw': raw.dict(),
            'step2_entities': {'entities': entities, 'entities_confidence': ent_conf},
            'step3_normalized': {'normalized': normalized, 'normalization_confidence': norm_conf},
            'final': {'appointment': appointment, 'status': 'ok'}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



@app.get('/health')
async def health():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}


# Run this file in terminal and then write command this for hosting-->
# uvicorn main:app --reload --port 8000    

# sample input text
# Get physician appointment 5:30 pm tomorrow
# Get skin appointment 9pm today
