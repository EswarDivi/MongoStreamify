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
CHUNK_SIZE = 100 * 1024

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="abc")
PROTOCOL = "http"
HOST = "localhost"
MONGO_HOST = "localhost"
MONGO_PORT = 27017
AUTH_HOST = "localhost"
AUTH_PORT = 8000


@app.on_event("startup")
async def get_mongo():
    video_db = AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}").video
    # video_db=AsyncIOMotorClient("mongodb+srv://admin:admin@cluster0.mqqrdrd.mongodb.net/?retryWrites=true&w=majority").video
    app.library = video_db.library
    app.fs = AsyncIOMotorGridFSBucket(video_db)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        if request.session["email"]:
            print(request.session["email"])
            videos = await _get_videos(request)
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "videos": videos,
                    "username": request.session["email"],
                },
            )
    except Exception:
        return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/sign-up")
async def sign_up(request: Request, email: str = Form(), password: str = Form()):
    user_data = {"email": email, "password": password}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{AUTH_HOST}:{AUTH_PORT}/sign-up", data=user_data
            ) as response:
                r = await response.text()
    except Exception as e:
        return templates.TemplateResponse("auth.html", {"request": request})

    if "1" in r:
        return templates.TemplateResponse("auth.html", {"request": request, "Error": 1})
    return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/login")
async def login(request: Request, email: str = Form(), password: str = Form()):
    user_data = {"email": email, "password": password}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{AUTH_HOST}:{AUTH_PORT}/login", data=user_data
            ) as response:
                r = await response.text()
                print(r)
    except Exception as e:
        return templates.TemplateResponse("auth.html")

    if "1" in r:
        return templates.TemplateResponse("auth.html", {"request": request, "Error": 2})
    request.session["email"] = email
    videos = await _get_videos(request)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "videos": videos, "username": request.session["email"]},
    )


@app.get("/logout")
async def logout(request: Request):
    request.session["email"] = None
    return templates.TemplateResponse("auth.html", {"request": request})


async def _get_videos(request: Request):
    videos = app.library.find({"email": request.session["email"]})
    docs = await videos.to_list(None)
    url = []
    video_urls = ""
    for i in docs:
        filename = i["filename"]
        video_urls += f"{PROTOCOL}://127.0.0.1/stream/{filename}+"

    video_urls = video_urls.split("+")
    video_urls = video_urls[::-1]
    video_urls = video_urls[1:]
    return "+".join(video_urls)


async def _generate_hash():
    return binascii.hexlify(os.urandom(16)).decode("utf-8")


async def _add_library_record(email: str, hash: str):
    data = {"email": email, "filename": hash}
    await app.library.insert_one(data)


async def _upload(file: object, hash: str):
    grid_in = app.fs.open_upload_stream(hash, metadata={"contentType": "video/mp4"})
    data = await file.read()
    await grid_in.write(data)
    await grid_in.close()  # uploaded on close


@app.post("/upload")
async def upload(request: Request, file: UploadFile, background_tasks: BackgroundTasks):
    if request.session["email"]:
        if file.filename:
            hash = await _generate_hash()
            background_tasks.add_task(_upload, file, hash)
            background_tasks.add_task(
                _add_library_record, request.session["email"], hash
            )
            videos = await _get_videos(request)
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "videos": videos,
                    "username": request.session["email"],
                },
            )
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "videos": videos,
                "username": request.session["email"],
                "Error": 3,
            },
        )
    return templates.TemplateResponse("auth.html")


@app.get("/stream/{filename}")
async def stream(filename: str, request: Request, range: str = Header(None)):
    if not request.session["email"]:
        return templates.TemplateResponse("auth.html")
    # play from middle
    start = 0
    end = start + CHUNK_SIZE

    grid_out = await app.fs.open_download_stream_by_name(filename)
    if end > grid_out.length:
        end = grid_out.length
    # grid_out.seek(0)

    async def read():
        while grid_out.tell() < grid_out.length:
            yield await grid_out.readchunk()

    headers = {}
    headers["Content-Length"] = str(grid_out.length)
    headers["Accept-Ranges"] = "bytes"
    headers["Content-Range"] = f"bytes {start}-{end}/{grid_out.length}"
    headers["Content-Type"] = "video/mp4"

    return StreamingResponse(read(), media_type="video/mp4", headers=headers)


@app.get("/publicVideo")
async def publicVideo(request: Request):
    if not request.session["email"]:
        return templates.TemplateResponse("auth.html", {"request": request})
    # get all names from library
    videos = app.library.find({}, {"filename": 1, "_id": 0, "email": 1})

    docs = await videos.to_list(None)

    user_videos = {}

    for i in docs:
        if i["email"] in user_videos:
            user_videos[i["email"]].append(i["filename"])
        else:
            user_videos[i["email"]] = [i["filename"]]

    # make a html page with all the videos

    html_page = ""

    for i in user_videos:
        html_page += f"<h1>{i}</h1>"
        for j in user_videos[i]:
            html_page += f'<li><a href="/stream/{j}">{j}</a></li>'

    return templates.TemplateResponse(
        "public.html", {"request": request, "user_videos": user_videos}
    )
