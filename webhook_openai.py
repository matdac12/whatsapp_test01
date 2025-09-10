#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Webhook Server with OpenAI Integration
Uses OpenAI's new Conversations and Responses API for intelligent chat
"""

from flask import Flask, request, jsonify, render_template
import json
import os
import sys
import requests
from datetime import datetime
import logging
from threading import Thread

# Set default encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from openai_conversation_manager import OpenAIConversationManager
from data_extractor import DataExtractor
from data_models import ClientInfo
from database import db

# Configure logging with UTF-8 support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration from environment
PORT = int(os.environ.get('PORT', 3000))
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my-verify-token-123')

# WhatsApp API Configuration
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_ID', '')
API_VERSION = 'v22.0'

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_PROMPT_ID = os.environ.get('OPENAI_PROMPT_ID', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4.1')

# Initialize OpenAI Conversation Manager
ai_manager = None
data_extractor = None

if OPENAI_API_KEY and OPENAI_PROMPT_ID:
    try:
        ai_manager = OpenAIConversationManager(
            api_key=OPENAI_API_KEY,
            prompt_id=OPENAI_PROMPT_ID,
            model=OPENAI_MODEL
        )
        logger.info("✅ OpenAI Conversation Manager initialized successfully")
        
        # Initialize Data Extractor
        data_extractor = DataExtractor(
            api_key=OPENAI_API_KEY,
            model="gpt-4o"  # Using gpt-4o for structured output parsing
        )
        logger.info("✅ Data Extractor initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI: {e}")
        ai_manager = None
        data_extractor = None
else:
    logger.warning("⚠️  OpenAI credentials not configured")

def send_whatsapp_message(to_number, message_text):
    """
    Send a WhatsApp message
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return False
    
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Message sent to +{to_number}")
            # Add sent message to database
            db.add_message(to_number, "bot", message_text)
            return True
        else:
            logger.error(f"Failed to send message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False

def mark_as_read(message_id):
    """
    Mark a WhatsApp message as read
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return False
    
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        return False

@app.route('/', methods=['GET'])
def verify_webhook():
    """
    Webhook verification endpoint for WhatsApp
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info('WEBHOOK VERIFIED')
        return challenge, 200
    else:
        logger.warning('Webhook verification failed')
        return '', 403

@app.route('/', methods=['POST'])
def receive_message():
    """
    Receives incoming WhatsApp messages and status updates
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get the request body
    body = request.get_json()
    
    # Log the received webhook
    logger.info(f"\n\nWebhook received {timestamp}\n")
    logger.debug(json.dumps(body, indent=2))
    
    # Process the webhook data in a separate thread to respond quickly
    Thread(target=process_webhook, args=(body,)).start()
    
    # Always return 200 OK immediately
    return '', 200

def process_webhook(body):
    """
    Process webhook data in background
    """
    if body.get('object') == 'whatsapp_business_account':
        for entry in body.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # Process messages
                messages = value.get('messages', [])
                for message in messages:
                    process_message(message, value.get('contacts', []))
                
                # Process status updates
                statuses = value.get('statuses', [])
                for status in statuses:
                    process_status(status)

def process_message(message, contacts):
    """
    Process an incoming WhatsApp message with OpenAI
    """
    msg_from = message.get('from')
    msg_id = message.get('id')
    msg_type = message.get('type')
    
    # Mark message as read
    mark_as_read(msg_id)
    
    # Find contact info
    contact_name = 'User'
    for contact in contacts:
        if contact.get('wa_id') == msg_from:
            profile = contact.get('profile', {})
            contact_name = profile.get('name', 'User')
            break
    
    logger.info(f"📨 New message from {contact_name} (+{msg_from})")
    logger.info(f"   Type: {msg_type}")
    
    # Handle text messages with OpenAI
    if msg_type == 'text':
        text = message.get('text', {}).get('body', '')
        logger.info(f"   Text: {text}")
        
        # Add received message to database
        db.add_message(msg_from, "user", text)
        
        # Process with OpenAI
        handle_ai_conversation(msg_from, text, contact_name)
    
    elif msg_type == 'image':
        logger.info(f"   Image received")
        send_whatsapp_message(msg_from, "I received your image! Currently, I can only process text messages. Please send me a text message and I'll be happy to help! 📸")
    
    elif msg_type == 'audio':
        logger.info(f"   Audio received")
        send_whatsapp_message(msg_from, "I received your audio message! Currently, I can only process text messages. Please type your message and I'll respond! 🎤")
    
    elif msg_type == 'location':
        location = message.get('location', {})
        lat = location.get('latitude')
        lon = location.get('longitude')
        logger.info(f"   Location: {lat}, {lon}")
        send_whatsapp_message(msg_from, f"Thanks for sharing your location! 📍\nI can see you're at coordinates {lat}, {lon}.\nHow can I help you today?")
    
    else:
        logger.info(f"   Unhandled message type: {msg_type}")
        send_whatsapp_message(msg_from, "I received your message! Please send me a text message so I can assist you better.")

def handle_ai_conversation(sender, text, contact_name):
    """
    Handle conversation with OpenAI and extract client data (dual-step)
    """
    # Check if AI manager is available
    if not ai_manager or not data_extractor:
        logger.error("OpenAI manager or data extractor not initialized")
        send_whatsapp_message(sender, "I'm sorry, but I'm having technical difficulties. Please try again later.")
        return
    
    try:
        # Check for commands first
        if text.strip().startswith('/'):
            command = text.strip()[1:].split()[0].lower()
            
            # Add info command to show profile status
            if command == 'info':
                profile_status = data_extractor.get_profile_status(sender)
                if profile_status:
                    info_msg = f"📋 Il tuo profilo:\n"
                    info_msg += f"Nome: {profile_status['data'].get('name', '❓')}\n"
                    info_msg += f"Cognome: {profile_status['data'].get('last_name', '❓')}\n"
                    info_msg += f"Azienda: {profile_status['data'].get('ragione_sociale', '❓')}\n"
                    info_msg += f"Email: {profile_status['data'].get('email', '❓')}\n"
                    if profile_status['missing']:
                        info_msg += f"\n{profile_status['missing']}"
                    send_whatsapp_message(sender, info_msg)
                    return
            
            # Handle other special commands
            command_response = ai_manager.handle_command(sender, command)
            if command_response:
                send_whatsapp_message(sender, command_response)
                return
        
        logger.info(f"🤖 Processing message from {sender}")
        
        # STEP 1: Get conversation and check if profile is already complete
        conversation_id = ai_manager.get_or_create_conversation(sender, text)
        
        # Check if we already have a complete profile
        existing_profile = data_extractor.get_profile_status(sender)
        
        if existing_profile and existing_profile['complete']:
            # Profile is already complete, no need to extract
            logger.info(f"✅ Using complete profile for {sender}")
            client_info = ClientInfo(
                name=existing_profile['data']['name'],
                last_name=existing_profile['data']['last_name'],
                ragione_sociale=existing_profile['data']['ragione_sociale'],
                email=existing_profile['data']['email'],
                found_all_info=True,
                what_is_missing=None
            )
            is_newly_complete = False
        else:
            # Profile incomplete or doesn't exist, proceed with extraction
            client_info, is_newly_complete = data_extractor.process_message(sender, text, conversation_id)
        
        # Log current profile state
        logger.info(f"📝 Profile status: {data_extractor.format_extraction_summary(client_info)}")
        
        # STEP 2: Prepare variables for prompt
        prompt_variables = {
            "client_name": client_info.name or "non_fornito",
            "client_lastname": client_info.last_name or "non_fornito",
            "client_company": client_info.ragione_sociale or "non_fornito",
            "client_email": client_info.email or "non_fornito",
            "completion_status": "Profilo completo ✅" if client_info.found_all_info else "Profilo incompleto 📝",
            "missing_fields_instruction": "" if client_info.found_all_info else f"Richiedi cortesemente: {client_info.what_is_missing}"
        }
        
        # Special handling for newly completed profiles
        if is_newly_complete:
            prompt_variables["completion_status"] = "Profilo appena completato! ✅"
            prompt_variables["missing_fields_instruction"] = "Ringrazia il cliente per aver fornito tutte le informazioni."
            logger.info(f"✅ Profile completed for {sender}")
        
        logger.info(f"📝 Prompt variables: Status={prompt_variables['completion_status']}")
        
        # Generate AI response with variables
        ai_response = ai_manager.generate_response(sender, text, prompt_variables)
        
        # STEP 3: Update conversation with extracted data if significant info was found
        if any([client_info.name, client_info.last_name, client_info.ragione_sociale, client_info.email]):
            # Update the conversation with extracted data
            client_info_json = client_info.json(exclude={'found_all_info', 'what_is_missing'})
            ai_manager.update_conversation_with_data(sender, client_info_json)
        
        # STEP 4: Send response to user
        if ai_response:
            # Let the AI handle the completion confirmation naturally
            # No need to add our own confirmation message
            
            # Split long messages if needed
            if len(ai_response) > 4000:
                chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                for chunk in chunks:
                    send_whatsapp_message(sender, chunk)
            else:
                send_whatsapp_message(sender, ai_response)
            
            logger.info(f"✅ AI response sent to {contact_name}")
        else:
            logger.error("No response generated from AI")
            send_whatsapp_message(sender, "I apologize, but I couldn't generate a response. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in AI conversation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        send_whatsapp_message(sender, "I encountered an error while processing your message. Please try again or type /reset to start over.")

def process_status(status):
    """
    Process a message status update
    """
    msg_id = status.get('id')
    status_type = status.get('status')
    
    logger.info(f"📊 Status update: {status_type} for message {msg_id}")
    
    if status_type == 'failed':
        errors = status.get('errors', [])
        for error in errors:
            logger.error(f"   Error: {error.get('title')} - {error.get('message')}")

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'port': PORT,
        'whatsapp_configured': bool(WHATSAPP_TOKEN and PHONE_NUMBER_ID),
        'openai_configured': bool(ai_manager is not None),
        'active_conversations': len(ai_manager.conversations) if ai_manager else 0
    }), 200

@app.route('/conversations', methods=['GET'])
def get_conversations():
    """
    Get active conversations (for monitoring)
    """
    if not ai_manager:
        return jsonify({'error': 'OpenAI not configured'}), 503
    
    return jsonify({
        'active_conversations': len(ai_manager.conversations),
        'users': list(ai_manager.conversations.keys())
    }), 200

@app.route('/dashboard')
def dashboard():
    """
    Web dashboard for viewing conversations
    """
    return render_template('dashboard.html')

@app.route('/api/conversations')
def api_get_conversations():
    """
    API endpoint to get all conversations with details
    """
    conversations = db.get_all_conversations_with_info()
    return jsonify(conversations)

@app.route('/api/messages/<phone>')
def api_get_messages(phone):
    """
    API endpoint to get messages for a specific phone number
    """
    messages = db.get_messages(phone)
    return jsonify(messages)

@app.route('/api/send', methods=['POST'])
def api_send_message():
    """
    API endpoint to send a manual message
    """
    data = request.json
    phone = data.get('phone')
    message = data.get('message')
    
    if not phone or not message:
        return jsonify({'success': False, 'error': 'Missing phone or message'}), 400
    
    success = send_whatsapp_message(phone, message)
    return jsonify({'success': success})

@app.route('/api/profile/<phone>', methods=['GET'])
def api_get_profile(phone):
    """
    API endpoint to get profile data for a phone number
    """
    profile = db.get_profile(phone)
    if profile:
        return jsonify({
            'name': profile['name'],
            'last_name': profile['last_name'],
            'ragione_sociale': profile['ragione_sociale'],
            'email': profile['email'],
            'found_all_info': profile['found_all_info']
        })
    else:
        # Return empty profile if not found
        return jsonify({
            'name': None,
            'last_name': None,
            'ragione_sociale': None,
            'email': None,
            'found_all_info': False
        })

@app.route('/api/profile/<phone>', methods=['POST'])
def api_update_profile(phone):
    """
    API endpoint to manually update profile data
    """
    if not data_extractor:
        return jsonify({'success': False, 'error': 'Data extractor not initialized'}), 503
    
    data = request.json
    
    try:
        # Update via data_extractor which will save to database
        success = data_extractor.update_profile_manually(
            phone,
            name=data.get('name'),
            last_name=data.get('last_name'),
            ragione_sociale=data.get('ragione_sociale'),
            email=data.get('email')
        )
        
        if success:
            logger.info(f"Profile manually updated for {phone} via dashboard")
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"\n🚀 WhatsApp OpenAI Bot Server")
    logger.info(f"=" * 50)
    logger.info(f"Port: {PORT}")
    logger.info(f"Verify Token: {'SET' if VERIFY_TOKEN else 'NOT SET'}")
    logger.info(f"WhatsApp Token: {'SET' if WHATSAPP_TOKEN else 'NOT SET'}")
    logger.info(f"Phone Number ID: {PHONE_NUMBER_ID if PHONE_NUMBER_ID else 'NOT SET'}")
    logger.info(f"OpenAI API Key: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
    logger.info(f"OpenAI Prompt ID: {OPENAI_PROMPT_ID[:20]}..." if OPENAI_PROMPT_ID else 'NOT SET')
    logger.info(f"OpenAI Model: {OPENAI_MODEL}")
    logger.info(f"=" * 50)
    logger.info(f"Health check: http://localhost:{PORT}/health")
    logger.info(f"Conversations: http://localhost:{PORT}/conversations")
    logger.info(f"Dashboard: http://localhost:{PORT}/dashboard")
    logger.info(f"=" * 50)
    logger.info(f"\n📝 Available Commands:")
    logger.info(f"  /reset - Reset conversation")
    logger.info(f"  /history - Show conversation history")
    logger.info(f"  /info - Show bot information")
    logger.info(f"=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)