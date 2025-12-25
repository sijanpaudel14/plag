#!/bin/bash
# We don't need Xvfb logic here anymore if using headless=new
echo "🚀 Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
