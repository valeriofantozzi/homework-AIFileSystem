#!/usr/bin/env python3
"""
CI Validation Script for workspace_fs package
Author: DevArchitect-GPT
Purpose: Automated CI checks with proper exit codes and reporting
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status with output.

    Args:
        cmd: Command to run as list of strings
        description: Human-readable description for logging

    Returns:
        Tuple of (success: bool, output: str)
    """
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
            cwd=Path(__file__).parent,
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False, result.stderr

    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False, str(e)


def check_dependencies() -> bool:
    """Verify Poetry and dependencies are installed."""
    success, _ = run_command(["poetry", "check"], "Checking Poetry configuration")
    if not success:
        return False

    success, _ = run_command(
        ["poetry", "install", "--quiet"], "Installing dependencies"
    )
    return success


def run_tests() -> bool:
    """Run pytest with coverage requirements."""
    success, output = run_command(
        [
            "poetry",
            "run",
            "pytest",
            "-v",
            "--cov=src/workspace_fs",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=80",
        ],
        "Running tests with coverage",
    )

    if success:
        # Extract coverage percentage from output
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                print(f"📊 Coverage: {line.split()[-1]}")
                break

    return success


def run_linting() -> bool:
    """Run ruff linting and formatting checks."""
    # Check code style
    success1, _ = run_command(
        ["poetry", "run", "ruff", "check", "."], "Running ruff linting"
    )

    # Check formatting
    success2, _ = run_command(
        ["poetry", "run", "ruff", "format", "--check", "."], "Checking code formatting"
    )

    return success1 and success2


def run_security() -> bool:
    """Run bandit security analysis."""
    success, _ = run_command(
        ["poetry", "run", "bandit", "-r", "src/", "-ll"], "Running security analysis"
    )
    return success


def main() -> int:
    """Main CI pipeline."""
    print("🚀 Starting CI validation for workspace_fs package")
    print("=" * 60)

    # Track overall success
    all_passed = True

    # Step 1: Check dependencies
    if not check_dependencies():
        print("💀 Dependency check failed - aborting")
        return 1

    # Step 2: Run linting
    if not run_linting():
        print("⚠️ Linting failed")
        all_passed = False

    # Step 3: Run security analysis
    if not run_security():
        print("⚠️ Security analysis failed")
        all_passed = False

    # Step 4: Run tests (always run to get coverage report)
    if not run_tests():
        print("⚠️ Tests failed")
        all_passed = False

    print("=" * 60)

    if all_passed:
        print("🎉 All CI checks PASSED!")
        print("📋 Next steps:")
        print("   - Review coverage report: htmlcov/index.html")
        print("   - Check git status and commit changes")
        return 0
    else:
        print("💥 Some CI checks FAILED!")
        print("📋 Action required:")
        print("   - Fix linting issues: poetry run ruff check . --fix")
        print("   - Fix security issues: review bandit output")
        print("   - Fix failing tests: poetry run pytest -v")
        return 1


if __name__ == "__main__":
    sys.exit(main())
