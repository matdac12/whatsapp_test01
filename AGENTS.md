# Repository Guidelines

## Project Structure & Module Organization
- Python: `start_openai_bot.py` (launcher), `webhook_openai.py` (Flask webhook), helpers `openai_conversation_manager.py`, `data_extractor.py`, `database.py`.
- Data/models: `data_models.py`; runtime data in SQLite `whatsapp_bot.db` (do not commit).
- Web UI: `templates/dashboard.html` (Flask+Bootstrap), `static/style.css` (CSS tokens, themes).
- Docs: `SETUP_GUIDE*.md`, `LOCAL_DEPLOYMENT_GUIDE.md`, `openAI_integration.md`.

## Build, Test, and Development Commands
- Create env: `python3 -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`).
- Install deps: `pip install -r requirements.txt`.
- Run locally: `bash run_bot.sh` or `python3 start_openai_bot.py` (starts Flask with dashboard at `/dashboard`).
- Optional Node webhook logger: `node app.js`.
- Env: `.env` (not committed). Required: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `OPENAI_API_KEY`, `OPENAI_PROMPT_ID`. Optional: `PORT`, `VERIFY_TOKEN`, `OPENAI_MODEL`.

## Frontend (Dashboard) Conventions
- Design tokens live in `static/style.css` (`:root` and `.theme-dark`). Reuse variables (colors, radius, shadows) instead of hard-coding.
- Current UI: search/filter bar, contact sorting by recent activity with friendly timestamps, sticky day separators, skeleton loaders, resizing textarea (Enter=send, Shift+Enter=newline), autofocus on contact select, smooth scroll-to-bottom. No avatars.
- Safety: when rendering user content, prefer `textContent` over `innerHTML` to prevent XSS.

## Coding Style & Naming
- Python 3.10+, PEP 8, 4‑space indents. Filenames `snake_case.py`; functions/vars `snake_case`; classes `PascalCase`; constants/env `UPPER_SNAKE_CASE`.
- Frontend: keep logic in `dashboard.html` inline script; style in `static/style.css`. Prefer small helpers and semantic class names (e.g., `.contact-name`, `.contact-preview`).

## Testing Guidelines
- Start with `pytest` for backend units (DB ops, extractor, OpenAI manager) and Flask route smoke tests (mock HTTP calls).
- Manual UI checks: verify search, sorting, skeleton loaders, composer behavior, day separators.

## Commit & Pull Request Guidelines
- Commits: imperative, scoped. Examples: `feat(ui): add skeleton loaders`, `style(css): add design tokens`.
- PRs: include a short demo (GIF/screens) for UI changes and validation steps. Link issues (e.g., `Closes #123`).

## Security & Configuration Tips
- Never commit secrets, `.env`, or user data (e.g., DB, message/profile JSON). Rotate any leaked tokens immediately.
- Validate and sanitize input before DB writes; avoid logging PII. For UI, avoid `innerHTML` with untrusted strings.
