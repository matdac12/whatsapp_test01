# 🚀 Local WhatsApp Webhook Deployment Guide

## Prerequisites

### 1. Install Required Python Packages
```bash
# On Windows (if using Windows Python)
pip install Flask requests

# On WSL/Linux
sudo apt update
sudo apt install python3-pip
pip3 install Flask requests

# Or if pip3 doesn't work
python3 -m pip install Flask requests
```

### 2. Install ngrok (to expose local server to internet)
Download from: https://ngrok.com/download

Or use command line:
```bash
# On Windows
choco install ngrok

# On Mac
brew install ngrok

# On Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

## Step-by-Step Deployment

### Step 1: Start the Local Webhook Server

Open Terminal 1:
```bash
cd "/mnt/c/Users/MattiaDaCampo/OneDrive - Be Digital Consulting Srl/ArrowHead/Progetto Whatsapp"
python3 start_local_webhook.py
```

You should see:
```
🚀 Starting WhatsApp Webhook Server locally
📍 Local URL: http://localhost:3000
🔑 Verify Token: my-verify-token-123
✅ Health Check: http://localhost:3000/health
```

### Step 2: Expose Local Server with ngrok

Open Terminal 2:
```bash
ngrok http 3000
```

You'll see something like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:3000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Step 3: Configure WhatsApp Webhook

1. Go to: https://developers.facebook.com
2. Select your app
3. Go to WhatsApp > Configuration > Webhook
4. Click "Edit" on Callback URL
5. Enter:
   - **Callback URL**: `https://abc123.ngrok.io/` (your ngrok URL)
   - **Verify Token**: `my-verify-token-123`
6. Click "Verify and Save"

### Step 4: Subscribe to Webhook Events

1. In the same webhook configuration page
2. Click "Manage" next to your webhook
3. Subscribe to:
   - `messages` - To receive incoming messages
   - `message_status` - To get delivery updates

### Step 5: Test Your Setup

#### Test from another terminal:
```bash
# Test health check
curl http://localhost:3000/health

# Test webhook verification
curl "http://localhost:3000/?hub.mode=subscribe&hub.verify_token=my-verify-token-123&hub.challenge=test123"

# Test with the test script
python3 test_local_webhook.py
```

#### Test from WhatsApp:
1. Send a message to your WhatsApp Business number
2. Watch Terminal 1 - you should see the incoming message logged
3. Try sending "hello" or "help" to get auto-replies

## 📊 Monitor Your Webhook

### Check server logs:
Watch Terminal 1 for:
- Incoming messages
- Status updates
- Auto-reply actions

### Check ngrok dashboard:
Open: http://localhost:4040
- See all incoming requests
- Inspect request/response details
- Debug any issues

## 🛠️ Troubleshooting

### Flask not found error:
```bash
# Install for current user
pip3 install --user Flask requests

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install Flask requests
```

### Port already in use:
Change port in `start_local_webhook.py`:
```python
os.environ['PORT'] = '5000'  # Change to different port
```
Then run ngrok with new port: `ngrok http 5000`

### Webhook not receiving messages:
1. Check ngrok is running and showing "Online"
2. Verify webhook URL in Facebook Developer Console
3. Make sure you subscribed to webhook events
4. Check Terminal 1 for any error messages

### Auto-reply not working:
- Check that WHATSAPP_ACCESS_TOKEN is set correctly
- Ensure the recipient has messaged you first (24-hour window rule)
- Look for error messages in Terminal 1

## 🎯 Available Auto-Reply Commands

When someone sends these messages, the bot will auto-respond:
- `hello` or `hi` - Greeting
- `help` - Show available commands
- `ping` - Test connection
- `test` - Confirmation message
- `info` - Bot information
- `time` - Current server time
- `/echo [text]` - Echo back the text
- `/template` - Send hello_world template

## 📝 Notes

- ngrok URLs change each time you restart (unless you have a paid account)
- You'll need to update the webhook URL in Facebook each time ngrok restarts
- The 24-hour window rule applies: you can only send non-template messages to users who messaged you in the last 24 hours
- Keep both terminals open while testing