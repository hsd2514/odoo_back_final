#!/usr/bin/env python3
"""
Production server for Odoo Final Backend
"""
import uvicorn
from app.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )
