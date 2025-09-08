# WhatsApp OpenAI Chatbot Project

## 🎯 Project Overview
This project creates an intelligent WhatsApp chatbot that uses OpenAI's new Conversations and Responses API to maintain context-aware conversations with users. Each WhatsApp user gets their own persistent conversation thread with the AI.

## 🏗️ Architecture

### Core Components:
1. **WhatsApp Business API** - Sends/receives messages via Meta's Cloud API
2. **Webhook Server** (Flask) - Receives WhatsApp messages via webhooks
3. **OpenAI Conversations API** - Maintains conversation context per user
4. **ngrok** - Exposes local server to internet for WhatsApp webhooks

### Key Files:
- `webhook_openai.py` - Main webhook server that processes WhatsApp messages
- `openai_conversation_manager.py` - Manages OpenAI conversations per user
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
- `/info` - Displays bot information

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
├── start_openai_bot.py         # Startup script
├── .env                        # API credentials
├── conversations.json          # Persistent conversation storage
├── requirements.txt            # Python dependencies
├── send_whatsapp.py           # Utility to send messages
├── whatsapp_sender.py         # CLI message sender
└── LOCAL_DEPLOYMENT_GUIDE.md  # Setup instructions
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

### Send test message:
```bash
python3 send_whatsapp.py
```

### Required packages:
```
Flask>=2.3.0
requests>=2.31.0
openai>=1.0.0
```

---
*Last updated: September 2025*
*This bot uses OpenAI's new Conversations API for persistent, context-aware chat*