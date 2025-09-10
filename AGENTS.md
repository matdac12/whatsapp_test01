# Repository Guidelines

## Project Structure & Module Organization
- Root Python entry points: `start_openai_bot.py` (launcher), `webhook_openai.py` (Flask webhook), utility scripts like `whatsapp_sender.py`, `send_whatsapp.py`.
- Data and models: `data_models.py`, `data_extractor.py`, `database.py`, `whatsapp_bot.db`, `message_history.json`, `client_profiles.json`.
- Web UI assets: `templates/` (Jinja templates), `static/` (CSS/JS). Example Node webhook logger: `app.js`.
- Setup docs: `SETUP_GUIDE*.md`, `LOCAL_DEPLOYMENT_GUIDE.md`, `openAI_integration.md`.

## Build, Test, and Development Commands
- Create env: `python3 -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`).
- Install deps: `pip install -r requirements.txt`.
- Run bot (recommended): `bash run_bot.sh` or `python3 start_openai_bot.py`.
- Run Flask directly: `python3 webhook_openai.py`.
- Node webhook logger (optional): `node app.js`.
- Env vars: set in `.env` (not committed). Required: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `OPENAI_API_KEY`, `OPENAI_PROMPT_ID`. Optional: `PORT`, `VERIFY_TOKEN`, `OPENAI_MODEL`.

## Coding Style & Naming Conventions
- Python 3.10+; PEP 8; 4‑space indents.
- Names: modules/files `snake_case.py`, functions/vars `snake_case`, classes `PascalCase`, constants/env `UPPER_SNAKE_CASE`.
- Keep scripts self‑contained; avoid hidden side effects on import. Prefer small, testable functions.

## Testing Guidelines
- Framework: prefer `pytest` with tests under `tests/` named `test_*.py`.
- Run: `pytest -q` (add `pytest`/`pytest-cov` to dev env as needed).
- Aim for coverage on message parsing, DB writes, and WhatsApp/OpenAI client wrappers (mock external calls).

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise scope. Example: `feat: add /reset command handling` or `fix(db): prevent duplicate message IDs`.
- PRs: include summary, rationale, screenshots for UI changes (`templates/`, `static/`), and steps to validate (commands, sample payloads).
- Link issues (e.g., `Closes #123`). Keep PRs focused and small.

## Security & Configuration Tips
- Never commit tokens, DB dumps, or `.env`. Add redacted examples in the PR body if helpful.
- When testing webhooks locally, use `ngrok http $PORT` and set the verify token to `VERIFY_TOKEN`.
- Validate and sanitize any user input before persisting to `whatsapp_bot.db`.
