import socket
import uvicorn
import click
import os
import uuid
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from opencode_web.server.config import load_config, ServerConfig

app = FastAPI(title="OpenCode Web")
security = HTTPBasic(auto_error=False)
templates = Jinja2Templates(directory="opencode_web/templates")

class Session(BaseModel):
    id: str
    name: str

active_sessions: List[Session] = []

def find_available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_network_ips():
    import subprocess
    try:
        output = subprocess.check_output(["hostname", "-I"]).decode().split()
        return output
    except:
        return []

def get_current_user(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    config = load_config()
    if not config.password:
        return config.username

    if credentials:
        if credentials.username == config.username and credentials.password == config.password:
            return credentials.username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, username: str = Depends(get_current_user)):
    return templates.TemplateResponse(request, "index.html")

@app.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request, username: str = Depends(get_current_user)):
    return templates.TemplateResponse(request, "servers.html")

@app.get("/session/{session_id}", response_class=HTMLResponse)
async def session_view(request: Request, session_id: str, username: str = Depends(get_current_user)):
    return templates.TemplateResponse(request, "session.html")

@app.get("/api/status")
async def api_status(username: str = Depends(get_current_user)):
    config = load_config()
    return {"hostname": config.hostname, "port": os.environ.get("RUNNING_PORT", config.port)}

@app.get("/api/sessions")
async def get_sessions(username: str = Depends(get_current_user)):
    return active_sessions

class CreateSessionRequest(BaseModel):
    name: str

@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest, username: str = Depends(get_current_user)):
    new_session = Session(id=str(uuid.uuid4())[:8], name=req.name)
    active_sessions.append(new_session)
    return new_session

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_text("OpenCode Terminal Attached. Type 'exit' to quit.")
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == 'exit':
                break
            # Mock shell response
            await websocket.send_text(f"Executed: {data}")
    except WebSocketDisconnect:
        pass

def run_server(port=None, hostname=None, mdns=None, mdns_domain=None, cors=None):
    config = load_config()

    if port is not None: config.port = port
    if hostname is not None: config.hostname = hostname
    if mdns is not None: config.mdns = mdns
    if mdns_domain is not None: config.mdns_domain = mdns_domain
    if cors: config.cors = list(cors)

    if config.port is None:
        config.port = find_available_port()

    os.environ["RUNNING_PORT"] = str(config.port)

    if config.cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if os.path.exists("opencode_web/static"):
        app.mount("/static", StaticFiles(directory="opencode_web/static"), name="static")

    click.echo(f"Starting web server...")
    click.echo(f"  Local access:       http://localhost:{config.port}")
    if config.hostname == "0.0.0.0":
        ips = get_network_ips()
        for ip in ips:
            click.echo(f"  Network access:     http://{ip}:{config.port}")

    if config.mdns:
        from opencode_web.server.mdns import advertise_service
        advertise_service(config.port, config.mdns_domain)

    uvicorn.run(app, host=config.hostname, port=config.port)
