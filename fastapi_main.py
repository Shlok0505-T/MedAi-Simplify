from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import json
import os
from datetime import datetime
from typing import Optional
import uvicorn

app = FastAPI(title="MedSimplify AI", description="Medical Text Simplification Assistant")

# Templates for rendering HTML
templates = Jinja2Templates(directory="templates")

# In-memory storage for demo (in production, use a database)
chat_sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/simplify")
async def simplify_text(
    text: str = Form(...),
    session_id: str = Form(default="default")
):
    """API endpoint to simplify medical text"""
    
    # Get API configuration from environment variables
    api_url = os.getenv("MEDICAL_API_URL", "http://localhost:7860/api/v1/run/1effbd4f-0774-486b-971c-6431bf605188")
    api_key = os.getenv("API_KEY", "sk-KoHDHZh68T9juZavQoTOgjDGx1Nn68TeWqe6AfEACvg")
    
    # Initialize session if not exists
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    current_time = datetime.now().strftime("%H:%M")
    
    try:
        # Make API call to medical simplification service
        headers = {'Content-Type': 'application/json', 'x-api-key': api_key}
        url = f"{api_url}?stream=false"
        data = {
            "input_value": text,
            "output_type": "chat",
            "input_type": "chat"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Extract response content
        if isinstance(response_data, dict):
            simplified_text = (
                response_data.get('output_value') or 
                response_data.get('response') or 
                response_data.get('message') or 
                response_data.get('content') or 
                str(response_data)
            )
        else:
            simplified_text = str(response_data)
        
        # Store messages in session
        chat_sessions[session_id].extend([
            {
                "role": "user",
                "content": text,
                "timestamp": current_time
            },
            {
                "role": "assistant", 
                "content": simplified_text,
                "timestamp": current_time
            }
        ])
        
        return JSONResponse({
            "success": True,
            "simplified_text": simplified_text,
            "timestamp": current_time,
            "session_stats": {
                "total_messages": len(chat_sessions[session_id]),
                "user_messages": len([m for m in chat_sessions[session_id] if m["role"] == "user"]),
                "ai_messages": len([m for m in chat_sessions[session_id] if m["role"] == "assistant"])
            }
        })
        
    except requests.exceptions.RequestException as e:
        # Store error in session
        error_msg = f"Failed to simplify text: {str(e)}"
        chat_sessions[session_id].append({
            "role": "error",
            "content": error_msg,
            "timestamp": current_time
        })
        
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/chat/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = [{
            "role": "assistant",
            "content": "Hello! I'm here to help you simplify complex medical language for better patient communication. Please share the medical text you'd like me to simplify.",
            "timestamp": datetime.now().strftime("%H:%M")
        }]
    
    return JSONResponse({
        "messages": chat_sessions[session_id],
        "session_stats": {
            "total_messages": len(chat_sessions[session_id]),
            "user_messages": len([m for m in chat_sessions[session_id] if m["role"] == "user"]),
            "ai_messages": len([m for m in chat_sessions[session_id] if m["role"] == "assistant"])
        }
    })

@app.delete("/api/chat/{session_id}")
async def clear_chat(session_id: str):
    """Clear chat history for a session"""
    chat_sessions[session_id] = [{
        "role": "assistant",
        "content": "Hello! I'm here to help you simplify complex medical language for better patient communication. Please share the medical text you'd like me to simplify.",
        "timestamp": datetime.now().strftime("%H:%M")
    }]
    
    return JSONResponse({"success": True, "message": "Chat cleared"})

@app.get("/api/test")
async def test_connection():
    """Test API connection"""
    api_url = os.getenv("MEDICAL_API_URL", "http://localhost:7860/api/v1/run/1effbd4f-0774-486b-971c-6431bf605188")
    api_key = os.getenv("API_KEY", "sk-KoHDHZh68T9juZavQoTOgjDGx1Nn68TeWqe6AfEACvg")
    
    try:
        headers = {'Content-Type': 'application/json', 'x-api-key': api_key}
        url = f"{api_url}?stream=false"
        data = {"input_value": "test connection", "output_type": "chat", "input_type": "chat"}
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            return JSONResponse({"success": True, "message": "Connection successful", "status": response.status_code})
        else:
            return JSONResponse({"success": False, "message": f"Connection failed with status {response.status_code}", "status": response.status_code})
            
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Connection failed: {str(e)}", "status": 0})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)