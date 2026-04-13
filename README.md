SubMan - Subscription Manager (EX1)
SubMan is a backend microservice built with FastAPI to track and manage personal subscriptions (Netflix, Spotify, etc.) and calculate monthly burn rates.

🚀 How to Run the API Locally
Prerequisites: Make sure you have uv installed.

Install Dependencies:

Bash
uv sync
Start the Server:
Make sure you are in the root directory (subman-project) and run:

Bash
uv run uvicorn app.main:app --reload
Access the API:
Open your browser and navigate to the interactive Swagger UI:
👉 http://127.0.0.1:8000/docs

🧪 How to Run the Tests
To execute the test suite (testing CRUD operations and the summary endpoint), run:

Bash
uv run python -m pytest
🤖 AI Assistance
In this exercise, I used Gemini to:

Brainstorm an elegant domain (Subscription Manager) that avoids complex relational databases for EX1.

Draft the Pydantic models with data validation (Enums and date validation).

Scaffold the FastAPI endpoints and the in-memory database logic.

Generate the automated test suite (pytest) to verify all endpoints work correctly.

Outputs were verified locally via the Swagger UI and by running the tests to ensure 100% pass rate.