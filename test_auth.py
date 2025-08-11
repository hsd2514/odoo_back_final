#!/usr/bin/env python3
"""
Test script for the authentication endpoints
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi import FastAPI
from app.main import create_app

if __name__ == "__main__":
    app = create_app()
    
    # Print available routes
    print("=== Available Authentication Routes ===")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"{list(route.methods)} {route.path}")
    
    print("\n=== FastAPI Documentation URLs ===")
    print("Swagger UI: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("OpenAPI JSON: http://localhost:8000/openapi.json")
    
    print("\n=== Test your authentication endpoints ===")
    print("POST /users/register - Register new user")
    print("POST /users/login - Login user")
    
    print("\n=== Starting server ===")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
