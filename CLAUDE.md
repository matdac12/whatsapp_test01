# WhatsApp OpenAI Chatbot Project

## 🎯 Project Overview
This project creates an intelligent WhatsApp chatbot that uses OpenAI's new Conversations and Responses API to maintain context-aware conversations with users. Each WhatsApp user gets their own persistent conversation thread with the AI.

## 🏗️ Architecture

### Core Components:
1. **WhatsApp Business API** - Sends/receives messages via Meta's Cloud API
2. **Webhook Server** (Flask) - Receives WhatsApp messages via webhooks
3. **OpenAI Conversations API** - Maintains conversation context per user
4. **SQLite Database** - Stores all conversations, messages, and client profiles
5. **ngrok** - Exposes local server to internet for WhatsApp webhooks

### Key Files:
- `webhook_openai.py` - Main webhook server that processes WhatsApp messages
- `openai_conversation_manager.py` - Manages OpenAI conversations per user
- `data_extractor.py` - Extracts structured client data (name, email, company) from messages
- `database.py` - SQLite database manager for all data persistence
- `start_openai_bot.py` - Startup script that loads environment variables
- `.env` - Contains all API credentials

## 🔑 API Credentials Required

### WhatsApp:
- `WHATSAPP_ACCESS_TOKEN` - Meta access token for WhatsApp Business
- `WHATSAPP_PHONE_ID` - WhatsApp Business phone number ID (e.g., 729549136917595)
- `WHATSAPP_ACCOUNT_ID` - WhatsApp Business account ID

### OpenAI:
- `OPENAI_API_KEY` - OpenAI API key (sk-proj-...)
- `OPENAI_PROMPT_ID` - Prompt ID for responses (pmpt_68bee228e8288196811e9e0426855ad501793deee998d9b1)
- `OPENAI_MODEL` - Model to use (gpt-4.1)

### Server:
- `PORT` - Server port (default: 3000)
- `VERIFY_TOKEN` - Webhook verification token

## 📋 Implementation Details

### OpenAI Integration (based on openAI_integration.md):
1. **Create Conversation**: `client.conversations.create()` - Creates a new conversation thread
2. **Generate Response**: `client.responses.create()` with:
   - `prompt.id`: Your specific prompt ID
   - `input`: User's message
   - `model`: gpt-4.1
   - `conversation`: Conversation ID for context
   - No streaming (for WhatsApp compatibility)
3. **Conversation Persistence**: Conversation IDs saved to `conversations.json`

### Message Flow:
1. User sends WhatsApp message → 
2. WhatsApp sends webhook to your server →
3. Server extracts user ID and message →
4. Checks if user has existing conversation (or creates new) →
5. Sends message to OpenAI with conversation context →
6. Receives AI response →
7. Sends response back via WhatsApp API →
8. Conversation context maintained for next message

### Special Commands:
- `/reset` - Starts a new conversation
- `/history` - Shows recent conversation history
- `/info` - Displays client profile information (WhatsApp command)

## 🚀 Deployment Instructions

### Local Development:
```bash
# 1. Install dependencies
pip install Flask requests openai

# 2. Set up .env file with all credentials

# 3. Start the webhook server
python3 start_openai_bot.py

# 4. In another terminal, expose with ngrok
ngrok http 3000

# 5. Configure WhatsApp webhook
# - Go to developers.facebook.com
# - Set Callback URL to ngrok URL
# - Set Verify Token to match your .env
# - Subscribe to 'messages' and 'message_status' events
```

### Production (Render):
- Deploy `webhook_openai.py` as main application
- Set all environment variables from .env
- Use Render's public URL as webhook callback

## ⚠️ Important Notes

### API Version:
- Use WhatsApp API v22.0 or later (not v21.0)
- API auto-upgrades to latest version

### Encoding Issues:
- Ensure no extra spaces in API keys
- Use UTF-8 encoding for all files
- Set `PYTHONIOENCODING=utf-8` if needed

### Rate Limits:
- WhatsApp: 24-hour window for non-template messages
- OpenAI: Check your API plan limits
- Implement error handling for both APIs

### Message Types:
- Currently handles: text, images, audio, location
- Only text messages are processed by AI
- Other types receive acknowledgment messages

## 🛠️ Troubleshooting

### Common Issues:
1. **"ascii codec can't encode"** - Check for extra spaces in API keys
2. **Webhook not receiving** - Verify ngrok is running and URL is correct
3. **No AI response** - Check OpenAI API key and prompt ID are valid
4. **Message not delivered** - Ensure recipient messaged you first (24hr rule)

### Debug Commands:
```bash
# Check server health
curl http://localhost:3000/health

# View active conversations
curl http://localhost:3000/conversations

# Check logs for errors
# Look for OpenAI initialization and conversation creation
```

## 📁 Project Structure
```
/Progetto Whatsapp/
├── webhook_openai.py           # Main webhook server
├── openai_conversation_manager.py # OpenAI conversation handler
├── data_extractor.py          # Client data extraction with AI
├── data_models.py             # Pydantic models for structured data
├── database.py                # SQLite database manager
├── start_openai_bot.py        # Startup script
├── templates/
│   └── dashboard.html         # Web interface for conversations
├── static/
│   └── style.css             # WhatsApp-style CSS
├── whatsapp_bot.db           # SQLite database file (auto-created)
├── .env                       # API credentials
├── requirements.txt           # Python dependencies
├── SETUP_GUIDE_clean.md      # Client setup documentation
└── CONVERSATION_MANAGEMENT_TODO.md # Future conversation rotation plan
```

## 🔄 Future Improvements
- Add image processing with GPT-4 Vision
- Implement voice message transcription
- Add database for conversation history
- Create admin dashboard
- Add multi-language support
- Implement user preferences/profiles

## 📝 Quick Reference

### Start the bot:
```bash
python3 start_openai_bot.py
```

### Required packages:
```
Flask>=2.3.0
requests>=2.31.0
openai>=1.0.0
pydantic>=2.0.0
email-validator>=2.0.0
```

## 🎉 Major Updates (January 9, 2025)

### 1. **Dual-Step Data Extraction System**
- Implemented automatic extraction of client information (Name, Last Name, Company, Email)
- Uses OpenAI's `responses.parse()` API for structured data extraction
- AI naturally requests missing information while maintaining conversation flow
- Profile completion tracking with Italian language support

### 2. **Web Dashboard Implementation** 
- Created WhatsApp-style web interface at `localhost:3000/dashboard`
- Left sidebar shows all conversations with client info
- Right panel displays chat history with green/gray message bubbles
- Auto-refresh every 5 seconds for real-time updates
- Accessible from any device on local network

### 3. **Edit Contact Feature**
- Click on any contact name to open edit modal
- Manually input/update client information
- Saves to database and updates AI behavior (won't ask for saved info)
- Bootstrap modal with save confirmation

### 4. **SQLite Database Migration**
- Migrated from JSON files to SQLite for production scalability
- Three main tables: conversations, client_profiles, messages
- Thread-safe connection pooling
- Indexed queries for performance
- Handles concurrent access and millions of messages

### 5. **Important Learnings**

#### API Corrections:
- Use `responses.parse()` not `beta.chat.completions.parse()` for extraction
- Use `text_format` parameter, not `response_format`
- WhatsApp API v22.0 works, v21.0 has issues

#### Data Flow:
1. Message arrives → Save to database
2. Extract client data → Update profile
3. Generate AI response with data request if needed
4. Send response → Update conversation

#### Dashboard Access Options:
- **Option A (Implemented)**: Local network access only
- **Option B (Future)**: Internet access with authentication

### 6. **Future Conversation Management Plan**
- Created `CONVERSATION_MANAGEMENT_TODO.md` for 48-hour conversation rotation
- Will implement conversation summaries to reduce API costs by 70-80%
- Maintains full history in database while limiting OpenAI context

## 📊 Current System Capabilities

- **Handles**: Unlimited concurrent users
- **Stores**: Complete message history in SQLite
- **Extracts**: Client data automatically in Italian
- **Dashboard**: Real-time conversation monitoring
- **Manual Control**: Edit client info, send manual messages
- **Performance**: Production-ready with database backend

## 🔧 Major Refactoring (January 10, 2025)

### Database Integration Issues Fixed

#### Problems Identified:
1. **Data not persisting** - Extracted client info wasn't being saved to database immediately
2. **Dual storage confusion** - Data stored in both `data_extractor.profiles` dictionary AND database
3. **Dashboard showing stale data** - Because of sync issues between memory and database
4. **Profile completion flag** - SQLite uses 0/1 for boolean, needed proper conversion

#### Fixes Applied:
1. **Immediate database saves** - `update_profile()` and `get_or_create_profile()` now save directly to DB
2. **Fixed profile loading** - `load_profiles()` properly recalculates `what_is_missing` field
3. **Manual update sync** - Dashboard edits now properly update both memory and database
4. **Boolean handling** - Proper conversion between SQLite (0/1) and Python bool

### Complete Refactoring - Removed In-Memory Storage

#### Why the Change:
- In-memory `self.profiles` dictionary caused synchronization issues
- Unnecessary complexity maintaining two data sources
- Memory overhead storing all profiles in RAM
- Risk of stale data when multiple processes access database

#### What Changed:
1. **Removed**:
   - `self.profiles` dictionary completely removed
   - `load_profiles()` method deleted
   - `save_profiles()` method deleted

2. **Refactored Methods**:
   - `get_or_create_profile()` - Now queries database directly
   - `update_profile()` - Updates database immediately
   - `update_profile_manually()` - Works only with database
   - `get_profile_status()` - Real-time database query

3. **New Helper Methods**:
   - `_calculate_what_is_missing()` - Calculates missing fields
   - `_create_client_info_from_db()` - Creates ClientInfo from DB data

#### Benefits:
- ✅ **Single source of truth** - Database only
- ✅ **No sync issues** - No more dual storage problems
- ✅ **Lower memory usage** - No profiles cached in RAM
- ✅ **Always fresh data** - Every read gets latest from DB
- ✅ **Simpler code** - Removed complex synchronization logic
- ✅ **Multi-process safe** - Multiple servers can share same database
- ✅ **Better scalability** - Can handle thousands of users without memory issues

#### Dashboard Verification:
- Dashboard already uses database directly via API endpoints
- `/api/conversations` → `db.get_all_conversations_with_info()`
- `/api/profile/<phone>` → `db.get_profile()`
- No changes needed to dashboard code

### Current Data Flow:
1. **WhatsApp message arrives** → Extract info → Save directly to database
2. **Dashboard refreshes** (every 5 seconds) → Reads directly from database
3. **Manual edit via dashboard** → Updates database immediately
4. **Server restart** → No memory to reload, just queries database as needed

### Performance Notes:
- SQLite is very fast for this use case (low message frequency)
- No need for in-memory caching with WhatsApp's message rate
- Database handles concurrent access properly
- Indexes on phone_number ensure fast queries

---
*Last updated: January 10, 2025*
*System refactored to use database-only approach, removing all in-memory storage*