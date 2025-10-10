# Quick Start Guide

## 🚀 To run the Together app, you need both frontend and backend:

### 1. Start the Backend API (Required!)
```bash
# Option 1: Using Docker (Recommended)
docker compose up -d api db

# Option 2: Manual setup
cd api-container
pip install -r requirements.txt
python run.py

# The API will run on http://localhost:5001
```

### 2. Start the React Frontend
```bash
cd frontend
npm install  # (if not done yet)
npm run dev

# The frontend will run on http://localhost:3000
```

## ⚠️ Important Notes:

- **The backend API MUST be running** for registration, login, and all features to work
- If you see "Unable to connect to server" error, the API backend is not running
- Make sure port 5001 is available for the API
- Make sure port 3000 is available for the frontend

## 🐛 Troubleshooting:

**Registration/Login fails:**
- Check if API is running: `curl http://localhost:5001/api/auth/register`
- Start the backend: `docker compose up -d api db`

**Password input hard to see:**
- This has been fixed! Password text should now be clearly visible with dark text on white background

**Can't see Docker:**
- Install Docker Desktop and enable WSL2 integration
- Or run the Flask API manually from the api-container directory

## 📱 Features Available:
- ✅ User Registration & Login
- ✅ Partner Connection System
- ✅ Real-time Messaging
- ✅ Shared Calendar
- ✅ Compatibility Quiz
- ✅ Daily Questions
- ✅ Settings & Profile Management

Enjoy your modernized Together app! 💕