from fastapi.testclient import TestClient
from opencode_web.server.main import app
import os

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "OpenCode Web" in response.text

def test_api_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "port" in data

def test_api_sessions():
    # Create a session
    response = client.post("/api/sessions", json={"name": "Test Session"})
    assert response.status_code == 200
    session = response.json()
    assert session["name"] == "Test Session"
    assert "id" in session

    # List sessions
    response = client.get("/api/sessions")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) > 0
    assert sessions[0]["name"] == "Test Session"

def test_auth_failure():
    # Set password env var
    os.environ["OPENCODE_SERVER_PASSWORD"] = "secret"
    try:
        response = client.get("/")
        assert response.status_code == 401
    finally:
        del os.environ["OPENCODE_SERVER_PASSWORD"]

def test_auth_success():
    os.environ["OPENCODE_SERVER_PASSWORD"] = "secret"
    try:
        response = client.get("/", auth=("opencode", "secret"))
        assert response.status_code == 200
    finally:
        del os.environ["OPENCODE_SERVER_PASSWORD"]
