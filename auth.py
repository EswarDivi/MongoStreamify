import os
from fastapi import FastAPI, Form
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()
MONGO_HOST = "localhost"
MONGO_PORT = 27017


@app.on_event("startup")
async def get_users():
    users_db = AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}").users
    # users_db=AsyncIOMotorClient("mongodb+srv://admin:admin@cluster0.mqqrdrd.mongodb.net/?retryWrites=true&w=majority").users

    app.users = users_db


@app.post("/sign-up")
async def sign_up(email: str = Form(), password: str = Form()):

    data = {"email": email, "password": password}
    db_user = await app.users.users.find_one({"email": email})
    if db_user:
        return 1
    await app.users.users.insert_one(data)
    return 0


@app.post("/login")
async def login(email: str = Form(), password: str = Form()):
    db_user = await app.users.users.find_one({"email": email})
    return 0 if db_user and db_user["password"] == password else 1


