"""
Quick start script to run both FastAPI and Django services.
This script helps you start both services in the correct order.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def check_fastapi_service():
    """Check if FastAPI service is running."""
    try:
        response = requests.get("http://localhost:8000/", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_fastapi():
    """Start FastAPI service."""
    print("🚀 Starting FastAPI AI Service on port 8000...")
    print("   (This will run in the background)")
    
    # Start FastAPI in background
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for service to start
    print("   Waiting for FastAPI to start...")
    for i in range(10):
        time.sleep(1)
        if check_fastapi_service():
            print("   ✅ FastAPI service is running!")
            return process
        print(f"   ... waiting ({i+1}/10)")
    
    print("   ⚠️  FastAPI service may not have started properly")
    return process

def start_django():
    """Start Django service."""
    print("\n🎯 Starting Django Backend on port 8001...")
    print("   (Press Ctrl+C to stop both services)")
    
    # Start Django (this will block)
    subprocess.run(
        [sys.executable, "manage.py", "runserver", "8001"]
    )

def main():
    """Main function to start both services."""
    print("=" * 60)
    print("🚀 Recruitment Platform - Quick Start")
    print("=" * 60)
    print()
    
    # Check if FastAPI is already running
    if check_fastapi_service():
        print("✅ FastAPI service is already running on port 8000")
        fastapi_process = None
    else:
        fastapi_process = start_fastapi()
    
    try:
        # Start Django
        start_django()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down services...")
        if fastapi_process:
            fastapi_process.terminate()
            print("   ✅ FastAPI service stopped")
        print("   ✅ Django service stopped")
        print("\nGoodbye! 👋")

if __name__ == "__main__":
    main()
