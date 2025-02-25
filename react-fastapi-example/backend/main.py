import os
import time
import random
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

domain = os.getenv("DOMAIN", "example.com")  

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://plugins.{domain}",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI Backend!"}

@app.get("/data")
def get_data():
    return {"data": ["Item 1", "Item 2", "Item 3"]}

@app.get("/lat")
def simulate_latency(response: Response):
    latency = random.uniform(0.1, 2.0)  
    time.sleep(latency)

    if random.random() < 0.5:  
        time.sleep(3)  

    custom_code = 418  
    response.status_code = custom_code

    return {"message": "Simulated latency", "latency_seconds": latency, "custom_status": custom_code}
