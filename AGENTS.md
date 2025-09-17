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
- Webhook payloads sent to Make escape all user-provided text, treat any 2xx status code as success, and handle `Retry-After` seconds or HTTP-date formats gracefully.

## Make Webhook Notes
- Conversation transcripts in webhook payloads no longer use the collapsible `<details>` wrapper so they render consistently in email clients.
- The fallback summary string is "Riassunto non disponibile al momento. Riferirsi alla conversazione. Grazie" when OpenAI summarization is unavailable.

## Manuale Mode (Per-Contact) — Shipped

Overview
- Per-contact Manuale mode pauses auto-sending; AI drafts are stored for operator review. Manual send from dashboard auto-enables Manuale for that contact.

Database
- Schema additions to `client_profiles` (idempotent in `DatabaseManager._create_tables`):
  - `manual_mode BOOLEAN DEFAULT 0`
  - `ai_draft TEXT`
  - `ai_draft_created_at TIMESTAMP`
  - `notes TEXT`
- Helpers added:
  - `get_settings(phone)`, `set_manual_mode(phone, enabled)`
  - `save_ai_draft(phone, text)`, `get_ai_draft(phone)`, `clear_ai_draft(phone)`
  - `get_notes(phone)`, `set_notes(phone, text)`
  - `get_last_user_message(phone)`

Backend (Flask)
- Gating in `handle_ai_conversation`: always passes `agent_notes` (from `notes`). When `manual_mode` is ON, saves AI output as draft and does not send to WhatsApp.
- Manual send: `/api/send` auto-enables Manuale via `db.set_manual_mode(phone, True)`.
- Endpoints:
  - `GET /api/settings/<phone>` → `{ manual_mode }`
  - `POST /api/settings/<phone>` with `{ manual_mode }`
  - `GET /api/draft/<phone>` → `{ draft, created_at }`
  - `POST /api/draft/<phone>/clear`
  - `POST /api/draft/<phone>/regenerate` with `{ regenerate_notes }` combines persistent notes + extra input; regenerates using the last user message.
- Profile endpoints now include `notes` in GET and accept `notes` in POST (persisted via DB).

Frontend (Dashboard)
- Header toggle “Manuale” (form-switch) synced with `/api/settings`.
- Draft panel above composer shows “Bozza AI (Manuale)” with actions:
  - Inserisci nel messaggio → moves draft to composer and clears draft immediately
  - Rigenera → reveals “Aggiungi informazioni” textarea and regenerates a new draft
  - Scarta → clears draft
- Notes textarea added to the contact edit modal; saved via profile POST.
- Polling: refreshes draft/settings for active contact; skips re-render of draft panel while typing/regenerating to preserve focus and caret.

UX/Style Decisions
- “Rigenera” button shows spinner + “Sto pensando…” while generating.
- Separate scrolling for contacts vs. chat; page-level scrolling disabled.
- Removed blue focus rings globally (no Bootstrap default glow).
- Send button is pill-shaped; draft boxes use rounded corners consistent with composer.
- Display name in list/header never shows literal `None`; shows only non-empty parts of name/lastname.

Notes
- Regenerate uses the last user message + `agent_notes` for best quality. We can switch to a different input strategy if desired.
- Default Manuale = OFF; behavior is backward compatible.
