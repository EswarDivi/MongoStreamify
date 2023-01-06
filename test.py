from pathlib import Path
from fastapi import FastAPI
from fastapi import Request, Response
from fastapi import Header
from fastapi.templating import Jinja2Templates
import os
import binascii
import aiohttp
from fastapi import FastAPI, BackgroundTasks, UploadFile, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from starlette.middleware.sessions import SessionMiddleware
import io

templates = Jinja2Templates(directory="templates")
app=FastAPI()

@app.get("/")
def choices(request: Request):

    return templates.TemplateResponse("choices.html", {"request": request})


#  <input type="checkbox" id="action" name="action" value="action">
#         <label for="action">Action</label><br>
#         <input type="checkbox" id="productivity" name="productivity" value="productivity">
#         <label for="productivity">Productivity</label><br>
#         <input type="checkbox" id="trailers" name="trailers" value="trailers">
#         <label for="trailers">Trailers</label><br>
#         <input type="checkbox" id="comedy" name="comedy" value="comedy">
#         <label for="comedy">Comedy</label><br>

@app.post("/choices")
async def choices(request: Request, action: str=Form(False), productivity: str = Form(False), trailers: str = Form(False), comedy: str = Form(False)):
    choice=[]
    if action:
        choice.append(action)
    if productivity:
        choice.append(productivity)
    if trailers:
        choice.append(trailers)
    if comedy:
        choice.append(comedy)
    return choice




