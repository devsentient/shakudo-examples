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
