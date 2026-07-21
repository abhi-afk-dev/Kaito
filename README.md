# KAITO_MOBILE 🤖

Kaito is a mobile-first AI personal assistant built to integrate directly with Google Workspace. It uses a React Native (Expo) frontend to communicate with a Django-powered backend, leveraging the Model Context Protocol (MCP) and Google's Gemini API to manage tasks like reading emails and summarizing context.

## 📁 Project Structure

The repository is split into two main directories:
* **`backend/`**: A Django application managing AI interactions, MCP tool execution, and Google Workspace OAuth authentication.
* **`frontend/`**: A React Native mobile application built with Expo Router for the user interface.

## 🛠️ Tech Stack
* **Frontend:** React Native, Expo, TypeScript
* **Backend:** Python, Django
* **AI & Integration:** Gemini GenAI SDK, FastMCP (Model Context Protocol)

## ⚙️ Local Setup & Installation

### 1. Backend Setup (Django)
Navigate to the backend directory and activate the Python environment:

```bash
cd backend
python3 -m venv env
source env/bin/activate  # Activates the virtual environment
pip install -r requirements.txt
```

* Set up your environment variables. You will need to create a .env file inside the backend/ directory:
Code snippet
```bash
GEMINI_KEY=your_gemini_api_key_here
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
CREDENTIALS_DIR=/absolute/path/to/KAITO_MOBILE/backend/mcp_tokens
```

* Run the authentication script to generate your local Workspace tokens, then start the server:

```Bash
python auth_fix.py
python manage.py migrate
python manage.py runserver 8001
```

### 2. Frontend Setup (React Native/Expo)
Open a new terminal and navigate to the frontend directory:

```Bash
cd frontend
npm install
Start the Expo development server:
```

```Bash
npm start
```

Note: Use the Expo Go app on your physical device to scan the QR code, or press a in the terminal to launch an Android emulator.