# AI Chatbot System

Full-stack customer-support chatbot with Flask, MySQL, a JSON chat API, conversation history, user feedback, a knowledge base, and an admin dashboard.

## Requirements
- Python 3.10+
- MySQL 8+
- Optional API key for AI-generated answers

## Setup (Windows CMD)
1. Open CMD in this project folder.
2. Create and activate a virtual environment:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```
3. Install packages:
   ```bat
   py -m pip install -r requirements.txt
   ```
4. Create the database and tables. Open MySQL Workbench, open `schema.sql`, and execute it. Or run:
   ```bat
   mysql -u root -p < schema.sql
   ```
5. Copy `.env.example` to `.env` and fill in your database settings. Load it before starting the app:
   ```bat
   py -c "from dotenv import load_dotenv; load_dotenv()"
   ```
   The command above only checks dotenv loading in that process. For a convenient local setup, add `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py`, before reading environment variables.
6. Create the first admin account securely using the one-time script below.
7. Run:
   ```bat
   py app.py
   ```
8. Visit `http://127.0.0.1:5000`.

## Create an admin account
After setting `.env`, run:
```bat
py create_admin.py
```
Follow the prompts. Do not publish passwords, API keys, or `.env` to GitHub.

## AI API
If `OPENAI_API_KEY` is configured, the chat endpoint uses the configured model. Without it, the system uses keyword matches from the MySQL knowledge base and a safe fallback response. API usage may incur provider charges.

## API endpoint
`POST /api/chat` requires a logged-in session and JSON:
```json
{"message": "What are your working hours?"}
```
Success response:
```json
{"answer": "Our support team is available ...", "conversation_id": 1, "timestamp": "2026-10-15 21:00"}
```

## Main routes
- `/` landing page
- `/register` user registration
- `/login` login
- `/chat` user chat
- `/history` user interaction history
- `/feedback` feedback form
- `/admin` admin analytics dashboard
- `/admin/knowledge` knowledge-base management
- `/admin/feedback` feedback review

## Notes
- This is an educational starter, not a production deployment. Before production, add CSRF protection, rate limiting, secure cookie settings, audit logging, migrations, stronger validation, and a managed secrets solution.
- For local development, Flask's built-in server is used. Deploy behind a production WSGI server for real usage.
