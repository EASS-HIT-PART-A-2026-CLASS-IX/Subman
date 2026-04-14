# 💰 SubMan Pro - Subscription Management System

**Developer:** Maor Maimon  
**Course:** Engineering Advanced Software Systems (EASS)  
**Exercise:** EX1 (Backend) & EX2 (Interface)

SubMan Pro is a lightweight Full-Stack application designed to help users track their recurring digital subscriptions, monitor monthly spending (Burn Rate), and export financial reports.

---

## 📁 Project Structure
The project is organized as a monorepo:
* `app/` - Backend logic (FastAPI, Pydantic).
* `frontend/` - User interface (Streamlit, Plotly).
* `tests/` - Automated test suite for core logic.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* `uv` (FastAPI/Streamlit environment manager)

### Installation
1. Clone the repository:
   ```bash
   git clone [Your-Repo-Link]
Sync dependencies:

Bash
uv sync
🛠️ Running the Application
According to the exercise requirements, both services must run side-by-side. Open two separate terminals:

1. Start the Backend (API)
The backend manages data validation and currency logic.

Bash
uv run uvicorn app.main:app --reload
Accessible at: http://localhost:8000

2. Start the Frontend (Interface)
The interface provides the dashboard and analytics.

Bash
uv run streamlit run frontend/app.py
Accessible at: http://localhost:8501

✨ Features (EX1 & EX2)
Core Functionality
Full CRUD: Create, Read, and Delete subscriptions.

Smart Summaries: Real-time metrics for total monthly expenses and active subscription count.

Data Visualization: Interactive pie charts showing expense distribution by category.

Extra Features (Bonus)
Intelligent Currency Conversion: The backend includes a logic layer that dynamically converts USD and EUR prices into ILS based on predefined rates, ensuring the "Monthly Burn Rate" is accurate and unified.

CSV Report Export: Users can download their entire subscription list as a CSV file with one click for external accounting.

Advanced UX: Implementation of native @st.dialog modals for RTL-supported success messages and animated feedback (balloons).

Input Validation: Deep validation using Pydantic to prevent duplicate entries or invalid financial data.

🤖 AI Assistance Declaration
As required by the submission guidelines, I utilized Gemini (LLM) as an interactive pairing partner during this project:

Architecture: Assistance in structuring the FastAPI repository pattern.

Frontend: Help with Streamlit syntax, specifically for managing the session_state and integrating CSS for RTL support.

Logic: Drafting the currency conversion dictionary and the CSV encoding flow.

Verification: All AI-generated snippets were manually reviewed, integrated into the specific project domain, and verified locally to pass the logic requirements of EX1 and EX2.