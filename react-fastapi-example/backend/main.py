import os
from fastapi import FastAPI
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
def simulate_latency():
    """
    Simulates random latency with occasional high-latency spikes
    """
    base_latency = random.uniform(0.1, 0.5)

    if random.random() < 0.2:
        spike_latency = random.uniform(2, 5) 
        time.sleep(spike_latency)
        return {"latency": f"{spike_latency:.2f} seconds (Spike)"}

    time.sleep(base_latency)
    return {"latency": f"{base_latency:.2f} seconds"}

