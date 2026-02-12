"""Main server module for OpenCode Web."""
import os
import socket
import uuid
import subprocess
from typing import Optional, List

import click
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from opencode_web.server.config import load_config

app = FastAPI(title="OpenCode Web")
security = HTTPBasic(auto_error=False)

# Get the base directory for templates and static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class Session(BaseModel):
    """Model representing a coding session."""
    id: str
    name: str

active_sessions: List[Session] = []

def find_available_port():
    """Find a random available port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_network_ips():
    """Get list of network IP addresses."""
    try:
        output = subprocess.check_output(["hostname", "-I"]).decode().split()
        return output
    except Exception: # pylint: disable=broad-exception-caught
        return []

def get_current_user(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    """Authenticate user via HTTP Basic Auth."""
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
async def home(request: Request, _: str = Depends(get_current_user)):
    """Render the dashboard home page."""
    return templates.TemplateResponse(request, "index.html")

@app.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request, _: str = Depends(get_current_user)):
    """Render the server status page."""
    return templates.TemplateResponse(request, "servers.html")

@app.get("/session/{session_id}", response_class=HTMLResponse)
async def session_view(request: Request, session_id: str, _: str = Depends(get_current_user)):
    """Render the active session editor view."""
    # pylint: disable=unused-argument
    return templates.TemplateResponse(request, "session.html")

@app.get("/api/status")
async def api_status(_: str = Depends(get_current_user)):
    """Get current server status."""
    config = load_config()
    return {"hostname": config.hostname, "port": os.environ.get("RUNNING_PORT", config.port)}

@app.get("/api/sessions")
async def get_sessions(_: str = Depends(get_current_user)):
    """List all active sessions."""
    return active_sessions

class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""
    name: str

@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest, _: str = Depends(get_current_user)):
    """Create a new coding session."""
    new_session = Session(id=str(uuid.uuid4())[:8], name=req.name)
    active_sessions.append(new_session)
    return new_session

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, _: str = Depends(get_current_user)):
    """Get details of a specific session."""
    for s in active_sessions:
        if s.id == session_id:
            return s
    raise HTTPException(status_code=404, detail="Session not found")

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for terminal attachment."""
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
    """Initialize and run the FastAPI server."""
    cli_overrides = {
        'port': port,
        'hostname': hostname,
        'mdns': mdns,
        'mdns_domain': mdns_domain,
        'cors': cors
    }
    config = load_config(cli_overrides=cli_overrides)

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

    static_dir = os.path.join(BASE_DIR, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    click.echo("Starting web server...")
    click.echo(f"  Local access:       http://localhost:{config.port}")
    if config.hostname == "0.0.0.0":
        ips = get_network_ips()
        for ip in ips:
            click.echo(f"  Network access:     http://{ip}:{config.port}")

    if config.mdns:
        # pylint: disable=import-outside-toplevel
        from opencode_web.server.mdns import advertise_service
        advertise_service(config.port, config.mdns_domain)

    uvicorn.run(app, host=config.hostname, port=config.port)
