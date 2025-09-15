# Manual Mode (Per-Contact) — Implementation Plan

Status: Completed
- Implemented across DB, Flask backend, and dashboard UI.
- Default remains Auto (Manuale = OFF). Manual send from dashboard auto-enables Manuale for that contact.
- Regenerate uses the last user message combined with `agent_notes` (contact notes + optional extra input) for higher-quality drafts.

## Goals & Overview
- Allow agents to pause automatic AI replies for a specific WhatsApp number (per-contact “Manuale” mode).
- In Manuale mode, the AI still generates a draft reply but does NOT send it to WhatsApp. The agent can: insert the draft into the composer, regenerate with added info ("Aggiungi informazioni"), or discard.
- When an agent sends a manual message from the dashboard, Manuale mode is automatically enabled for that phone.

## User Stories
- As an agent, I can toggle Manuale on/off for the current contact so the AI stops auto-sending.
- As an agent, when Manuale is on and a new user message arrives, I see an AI draft (not sent) and can insert, regenerate with extra instructions, or discard.
- As an agent, if I send a manual message in a thread, Manuale turns on automatically for that phone.

## Behavior (Auto vs Manuale)
- Auto (default): current behavior — AI replies are generated and sent automatically.
- Manuale (per-phone): AI generates a draft and stores it; no outbound message is sent automatically. Agent decides what to send.

## Data Model & Migration
We will extend the existing `client_profiles` table in `database.py` (keeps scope minimal and aligns with per-phone profile data):
- Add columns:
  - `manual_mode BOOLEAN DEFAULT 0`
  - `ai_draft TEXT` (nullable)
  - `ai_draft_created_at TIMESTAMP` (nullable)
  - `notes TEXT` (nullable) — persistent per-contact notes maintained by agents

Migration strategy (idempotent):
- In `DatabaseManager._create_tables()`, run `ALTER TABLE client_profiles ADD COLUMN ...` inside try/except for each column (ignoring "duplicate column" errors) so existing installations self-migrate on start.

Database helper methods to add:
- `get_settings(phone) -> {manual_mode: bool}`
- `set_manual_mode(phone, enabled: bool) -> None`
- `save_ai_draft(phone, text: str) -> None` (sets `ai_draft`, `ai_draft_created_at=CURRENT_TIMESTAMP`)
- `get_ai_draft(phone) -> Optional[Dict{text, created_at}]`
- `clear_ai_draft(phone) -> None`
- `get_notes(phone) -> Optional[str]`
- `set_notes(phone, text: str) -> None`

Note: If you prefer a new `conversation_settings` table, we can adapt, but the above is simpler and consistent with current code.

## Backend Changes (Flask)
1) Webhook gating (in `webhook_openai.py`):
- In `process_message`/`handle_ai_conversation` before sending a reply:
  - Check `db.get_settings(sender).manual_mode`.
  - If OFF: send as today.
  - If ON: generate reply via `ai_manager.generate_response(...)`, then call `db.save_ai_draft(sender, ai_response)` and do NOT call `send_whatsapp_message`.

2) Auto-enable Manuale on manual send (in `/api/send`):
- Before/after sending, call `db.set_manual_mode(phone, True)` to enter Manuale mode automatically when an agent sends a message.

3) New API endpoints:
- `GET /api/settings/<phone>` → `{ manual_mode: bool }`
- `POST /api/settings/<phone>` with `{ manual_mode: true|false }` → `{ success: bool }`
- `GET /api/draft/<phone>` → `{ draft: string|null, created_at: iso|null }`
- `POST /api/draft/<phone>/regenerate` with `{ regenerate_notes: string }` → server composes `agent_notes = combine(contact.notes, regenerate_notes)` and replaces stored draft; returns `{ draft }`.
- `POST /api/draft/<phone>/clear` → clears stored draft.
- Notes management (can piggyback on profile endpoint or be separate):
  - Extend existing `GET /api/profile/<phone>` to return `notes`.
  - Extend existing `POST /api/profile/<phone>` to accept `notes`.
  - Alternatively, add `GET/POST /api/notes/<phone>`.

4) Regenerate with “Aggiungi informazioni”:
- Use existing `ai_manager.generate_response(user_id, message, prompt_variables)`; pass a single `agent_notes` variable ALWAYS (empty string allowed).
- Prompt template will consider `agent_notes` only when non-empty.
- For normal auto-replies/drafts, `agent_notes` = per-contact notes from DB.
- For Regenerate, server composes `agent_notes = combine(contact.notes, regenerate_notes)` (with a separator like `\n\n---\n`); does not persist `regenerate_notes`.

## Frontend Changes (templates/dashboard.html)
1) Header toggle:
- Add a small “Manuale” toggle (icon+label) in the chat header.
- On toggle change → `POST /api/settings/<phone>`; update local UI state.
- When entering Manuale via manual send, reflect toggle state automatically on next poll.

2) AI Draft panel (visible only when Manuale ON and a draft exists):
- Placement: above the composer.
- Contents:
  - Title: "Bozza AI (Manuale)"
  - Body: draft text (scrollable if long)
  - Actions: [Inserisci nel messaggio] [Rigenera] [Scarta]
- When clicking Regenera, reveal a small input `Aggiungi informazioni` (multiline) and confirm to call `POST /api/draft/<phone>/regenerate` with `{ regenerate_notes }` (send an empty string if left blank). Backend will combine with contact notes into `agent_notes`.
  - Inserisci: moves the draft into the textarea (agent can edit) and optionally clears the draft (`/clear`) or leave it until send.
  - Scarta: `/clear`.

3) Notes editing (from contact card):
- On clicking the contact name (which already opens the edit modal), show a new `Note` textarea alongside existing fields.
- Save notes via existing profile POST (extended to include `notes`).
- Reflect notes in the UI on next fetch.

4) Polling wiring (simple):
- On contact select: fetch `GET /api/settings/<phone>`. If `manual_mode` is true, fetch `GET /api/draft/<phone>` and render the panel if present.
- During periodic refresh: if the active contact’s `manual_mode` is true and the last timestamp changed, fetch draft again (the webhook will store a new one). Avoid full re-renders.
- Regenerate input (`regenerate_notes`) remains in client memory only; not persisted.

- Always include a single `agent_notes` variable in `prompt_variables` for all AI generations:
  - Auto/draft: `agent_notes` = contact notes from DB (string, possibly empty).
  - Regenerate: `agent_notes` = text from "Aggiungi informazioni" (string, possibly empty; not saved).
- Continue to include existing variables already used in the code (client fields, completion status, etc.).
- No streaming is required.

## Error Handling & Edge Cases
- If OpenAI draft generation fails: store no draft; log the error; show a non-blocking toast (later) or subtle inline message in the panel.
- If Manuale toggled OFF while a draft exists: keep the draft until cleared or overwrite on next user message (OK to keep single latest draft).
- Manuale is per-phone and persists until explicitly turned OFF.

## Testing Plan
- DB migration: run once, verify columns exist; round-trip `set_manual_mode`, `save_ai_draft`, `get_ai_draft`, `clear_ai_draft`.
- Webhook: with Manuale ON, incoming message generates draft and does not send; with OFF, sends as today.
- Endpoints: unit test GET/POST settings, draft CRUD, regenerate path (mock OpenAI), and notes GET/POST. Ensure `agent_notes` is always passed (empty string if missing), and composition logic with `regenerate_notes` works.
- Frontend flows: toggle Manuale, receive incoming message → draft panel shows; insert/regenerate/discard behave as expected; manual send auto-enables Manuale.

## Rollout & Defaults
- Default `manual_mode = 0` for all contacts.
- Backward compatible; no behavior change until agents toggle Manuale or send a manual message.
- No new external dependencies.

## Future Enhancements (post-MVP)
- Unread badge + Manuale indicator in contact list.
- SSE/WebSockets to push draft updates immediately (no polling).
- Approval queue for multiple drafts (out of scope for now).
- Template library for quick replies.

## Implementation Order (Tasks)
1) DB migration + helpers in `database.py`. [Done]
2) API endpoints in `webhook_openai.py` for settings and draft CRUD. [Done]
3) Notes GET/POST integration in profile endpoint and DB helpers. [Done]
4) Webhook gating + draft save on Manuale; always pass `agent_notes`. Regenerate composes `agent_notes = combine(contact.notes, regenerate_notes)`. [Done]
5) Auto-enable Manuale on `/api/send`. [Done]
6) Frontend: toggle + draft panel + regenerate UI with “Aggiungi informazioni”; extend edit modal with `Note` textarea and save. [Done]
7) Wire polling to fetch settings/draft minimally; skip re-render while typing/regenerating to preserve UX. [Done]

What Shipped (Details)
- DB: `client_profiles` now includes `manual_mode`, `ai_draft`, `ai_draft_created_at`, `notes` (idempotent ALTER statements).
- DB helpers: settings, drafts, notes, and `get_last_user_message` to support regenerate.
- Backend: manual gating in `handle_ai_conversation`; endpoints for settings and draft lifecycle; profile endpoints include `notes`.
- Frontend: header toggle, draft panel with “Inserisci / Rigenera / Scarta”, regenerate textarea, spinner state with “Sto pensando…”, notes field in contact modal.
- UX refinements: separate scrolling for chat vs. contacts; no blue focus rings; pill-shaped send; draft boxes rounded; display name avoids “None”.

Notes/Deviations
- Regeneration strategy uses the last user message and `agent_notes` (preferred for response quality) rather than an empty prompt.
- “Inserisci” clears the draft immediately (design choice to avoid stale panel).

Post-MVP Ideas
- Unread badge + Manuale indicator in contact list.
- SSE/WebSockets for immediate draft updates.
- Draft history/queue.

This plan aligns with the current codebase structure and keeps changes small, testable, and reversible.
