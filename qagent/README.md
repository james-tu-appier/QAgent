# QAgent

AI-assisted test plan generator with a simple Flask frontend. Upload a PRD, provide a Figma URL, and get a structured test plan and detailed test cases. Runs fully with live APIs or in demo mode with mock data. This project was initially built for the **2025 Appier Hackathon**, and is the proud winner of the **Practical Impact Award (Second Place)**. 
Hackathon Confluence Page: https://appier.atlassian.net/wiki/spaces/Labs/pages/4144693249/TEAM+CoverIQ+QA+Workflow+Automation+with+QAgent+An+AI-Powered+Test+Planner

### Quick Start

```bash
# 1) Clone
git clone <this-repo>
cd qagent

# 2) Create and activate a virtualenv (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Run the app
python app.py

# 5) Open in browser
# http://localhost:8080
```

### Requirements

- Python 3.9+ recommended
- Optional: Google Gemini API key and Figma access token for full functionality

### Environment Variables

Create a `.env` in the repo root:

```env
# Required for full (non-demo) mode
GEMINI_API_KEY="your_gemini_api_key"
FIGMA_ACCESS_TOKEN="your_figma_access_token"

# Optional: TestRail upload
TESTRAIL_URL=https://appier.testrail.io/
TESTRAIL_USER=y"our_user"
TESTRAIL_PASSWORD_OR_KEY="your_password_or_api_key"
```

Notes:
- If `GEMINI_API_KEY` or `FIGMA_ACCESS_TOKEN` are missing, the app will run in demo mode with mock data.

### Running the Frontend

- Start the Flask app:
  ```bash
  python app.py
  ```
- Visit `http://localhost:8080`
- Upload a PRD file (`.pdf`, `.txt`, `.md`), paste a Figma URL, and optionally toggle Trust Mode:
  - Trust Mode: automatic, end-to-end generation
  - Checkpoint Mode: review and edit at key steps

Outputs are saved under `output/<session_id>/`:
- `prd_context.json`, `figma_summary.txt`
- `test_plan.json`, `test_plan.md`
- `test_suite.json`, `test_suite.md`

Health check:
```text
GET /health
```

### TestRail (Optional)

Once a plan is generated, you can POST to:
```text
POST /upload_to_testrail/<session_id>
```
with JSON body:
```json
{ "project_id": 1, "suite_id": 2 }
```
Requires `TESTRAIL_URL`, `TESTRAIL_USER`, `TESTRAIL_PASSWORD_OR_KEY` in `.env`.

### Troubleshooting
Contact james.tu@appier.com 

### Project Structure (high-level)

- `app.py`: Flask app and routes
- `templates/`, `static/`: frontend UI
- `backend/`: modular classes for PRD extraction, Figma parsing, plan generation
- `uploads/`: uploaded PRDs
- `output/`: generated artifacts by session

### Notes: 
1. If you wish to load results from previous sessions, use the session id from the output folder and enter it in the View Previous Session section on the homepage. 
2. If you want the test cases to focus on certain aspects or modify the coverage of testing types, feel free to update the backend/prompt_templates to best fit your needs. (If you come across great results after prompt engineering, please share your findings with me!!)


