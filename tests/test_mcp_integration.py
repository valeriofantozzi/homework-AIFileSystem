"""
Integration tests for the MCP FastAPI server.

Covers:
- /mcp endpoint (initialize, tools/list, tools/call, resources/list)
- /health, /metrics, /diagnostics endpoints

High cohesion: each test targets a single endpoint/behavior.
Low coupling: workspace is isolated per test, no global state.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from server.api_mcp.mcp_server import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    # Patch workspace path to a temp directory for isolation
    monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
    with TestClient(app) as client:
        yield client

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "unhealthy")
    assert "version" in data
    assert "uptime" in data

def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "tool_calls" in data
    assert "error_count" in data
    assert "average_response_time" in data

def test_diagnostics_endpoint(client):
    resp = client.get("/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_info" in data
    assert "agent_status" in data
    assert "workspace_info" in data
    assert "performance_metrics" in data

def test_mcp_initialize(client):
    req = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": None
    }
    resp = client.post("/mcp", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "init-1"
    assert "result" in data

def test_mcp_tools_list(client):
    req = {
        "jsonrpc": "2.0",
        "id": "tools-1",
        "method": "tools/list",
        "params": None
    }
    resp = client.post("/mcp", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "tools-1"
    assert "result" in data
    assert "tools" in data["result"]

def test_mcp_tools_call_list_files(client):
    req = {
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {
            "name": "list_files",
            "arguments": {}
        }
    }
    resp = client.post("/mcp", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "call-1"
    assert "result" in data
    assert "content" in data["result"]
    assert not data["result"].get("isError", False)

def test_mcp_tools_call_invalid_tool(client):
    req = {
        "jsonrpc": "2.0",
        "id": "call-2",
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool",
            "arguments": {}
        }
    }
    resp = client.post("/mcp", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "call-2"
    assert "result" in data or "error" in data
    # Should return isError True or error field
    if "result" in data:
        assert data["result"].get("isError", True)
    else:
        assert "error" in data

def test_mcp_resources_list(client):
    req = {
        "jsonrpc": "2.0",
        "id": "resources-1",
        "method": "resources/list",
        "params": None
    }
    resp = client.post("/mcp", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "resources-1"
    assert "result" in data
    assert "resources" in data["result"]
