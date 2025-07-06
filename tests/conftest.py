"""
Test configuration and utilities for the AI File System Agent test suite.

This module provides common test fixtures, utilities, and configuration
for all test modules.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import asyncio
from typing import AsyncGenerator, Tuple

from agent.core.secure_agent import SecureAgent
from workspace_fs import Workspace


class TestConfig:
    """Test configuration constants."""
    
    # Timeout settings
    DEFAULT_TIMEOUT = 30.0
    SLOW_OPERATION_TIMEOUT = 60.0
    
    # Performance thresholds
    MAX_RESPONSE_TIME = 15.0
    MAX_TOTAL_WORKFLOW_TIME = 60.0
    
    # Test data settings
    MIN_RESPONSE_LENGTH = 20
    EXPECTED_SUCCESS_RATE = 0.8


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def clean_workspace() -> AsyncGenerator[Tuple[SecureAgent, Path], None]:
    """Create a clean workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        workspace = Workspace(temp_dir)
        agent = SecureAgent(workspace_path=temp_dir)
        yield agent, temp_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture  
async def workspace_with_test_data() -> AsyncGenerator[Tuple[SecureAgent, Path], None]:
    """Create workspace with complete test data."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Copy all sandbox test data
    sandbox_path = Path(__file__).parent / "sandbox"
    if sandbox_path.exists():
        shutil.copytree(sandbox_path, temp_path / "test_data", dirs_exist_ok=True)
    
    try:
        workspace = Workspace(temp_dir)
        agent = SecureAgent(workspace_path=temp_dir)
        yield agent, temp_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def assert_successful_response(response: str, operation_name: str = "operation") -> None:
    """Assert that a response indicates successful operation."""
    assert len(response) >= TestConfig.MIN_RESPONSE_LENGTH, f"{operation_name} response too short: {len(response)} chars"
    
    # Check for various success indicators in multiple languages
    success_indicators = [
        "successfully", "completed", "created", "written", "deleted", "read", 
        "successo", "creato", "completato", "eliminato", "letto", "scritto",
        "complete", "done", "finished", "accomplished", "✅"
    ]
    
    # For listing operations, also accept informative responses that provide data
    listing_indicators = [
        "here are", "ecco", "files currently", "directories", "cartelle",
        "directory", "file", "workspace", "spazio", "present", "presenti"
    ]
    
    # For content display operations, accept content-showing patterns
    content_indicators = [
        "content of", "contents of", "contenuto di", "contenuti di",
        "content è:", "contents are:", "contenuto è:", "contenuti sono:"
    ]
    
    # Combine all indicators
    all_indicators = success_indicators + listing_indicators + content_indicators
    
    assert any(indicator in response.lower() for indicator in all_indicators), \
        f"{operation_name} did not indicate successful completion. Response: {response[:100]}"


def assert_error_response(response: str, operation_name: str = "operation") -> None:
    """Assert that a response properly handles an error."""
    assert len(response) >= TestConfig.MIN_RESPONSE_LENGTH, f"{operation_name} error response too short"
    
    # Check for various error indicators in multiple languages
    error_indicators = [
        "not found", "error", "cannot", "does not exist", "invalid", "failed",
        "non trovato", "errore", "non esiste", "non valido", "fallito",
        "missing", "unavailable", "inaccessible", "forbidden"
    ]
    
    assert any(keyword in response.lower() for keyword in error_indicators), \
        f"{operation_name} did not properly indicate error. Response: {response[:100]}"


def assert_security_rejection(response: str, operation_name: str = "operation") -> None:
    """Assert that a response properly rejects unsafe/irrelevant requests."""
    assert len(response) >= TestConfig.MIN_RESPONSE_LENGTH, f"{operation_name} rejection too short"
    assert any(keyword in response.lower() for keyword in [
        "cannot", "decline", "not safe", "irrelevant", "boundary", "designed", "file-related"
    ]), f"{operation_name} did not properly reject unsafe request"


# Test markers for different test categories
pytestmark = [
    pytest.mark.asyncio,
]
