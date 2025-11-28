import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from solver_python import solve_task

load_dotenv()

app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

PORT = int(os.getenv("PORT", 3000))
QUIZ_SECRET = os.getenv("QUIZ_SECRET")
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", 180000))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"{datetime.now().isoformat()} {request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.post("/solve")
async def solve_quiz(request: QuizRequest):
    if request.secret != QUIZ_SECRET:
        raise HTTPException(status_code=403, detail="invalid secret")
    
    asyncio.create_task(solve_quiz_task(request.email, request.secret, request.url))
    
    return {"status": "accepted"}

async def solve_quiz_task(email: str, secret: str, url: str):
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
    uvicorn.run(app, host="0.0.0.0", port=PORT)