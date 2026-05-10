#!/bin/bash

# Environment variables for auth integration
export JWT_SECRET="YourSuperSecretKeyHere12345678901234567890"
export AUTH_SERVICE_URL="http://localhost:5000"

# Run the orchestrator
python app/main.py