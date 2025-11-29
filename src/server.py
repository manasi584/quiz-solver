import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
import uvicorn
from dotenv import load_dotenv
from .solver import solve_task

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

PORT = int(os.getenv("PORT", 3000))
QUIZ_SECRET = os.getenv("QUIZ_SECRET")
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", 180000))

@app.post("/solve")
async def receiveRequest(request: Request):
    try:
        body = await request.json()
        quiz_request = QuizRequest(**body)
    except (ValueError, ValidationError):
        raise HTTPException(status_code=400, detail="invalid JSON")
    
    if quiz_request.secret != QUIZ_SECRET:
        raise HTTPException(status_code=403, detail="invalid secret")
    
    asyncio.create_task(solve_quiz(quiz_request.email, quiz_request.secret, quiz_request.url))
    
    return {"status": "accepted"}

async def solve_quiz(email: str, secret: str, url: str):
    print("Solving quiz:", email, secret, url)
    try:
        result = await asyncio.wait_for(
            solve_task(email, secret, url),
            timeout=TIMEOUT_MS / 1000
        )
        print("Solve finished:", result)
    except asyncio.TimeoutError:
        print("Error solving task: timeout")
    except Exception as err:
        print("Error solving task:", err)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)