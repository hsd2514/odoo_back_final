#!/usr/bin/env python3
"""
Simple test for just the user authentication
"""
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from app.routers.users import router as users_router

# Create a simple app with just the users router
app = FastAPI(title="Odoo Authentication Test")
app.include_router(users_router)

if __name__ == "__main__":
    print("=== Authentication Routes ===")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"{list(route.methods)} {route.path}")
    
    print("\n=== Starting server on http://localhost:8000 ===")
    print("Documentation: http://localhost:8000/docs")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
