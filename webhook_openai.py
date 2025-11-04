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
import time
from datetime import datetime
import logging
from threading import Thread


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

# Silence werkzeug HTTP request logs (only show warnings/errors)
# This prevents log spam from dashboard API polling every 2 seconds
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Create Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration from environment
PORT = int(os.environ.get('PORT', 3000))
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my-verify-token-123')

# HTTP Request Configuration
REQUEST_TIMEOUT = (3, 10)  # (connect timeout, read timeout) in seconds
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # Wait 1s, 2s, 4s between retries

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

def make_request_with_retry(method, url, headers, json_data=None, timeout=REQUEST_TIMEOUT):
    """
    Make HTTP request with timeout and retry logic
    
    Args:
        method: 'POST' or 'GET'
        url: Request URL
        headers: Request headers
        json_data: JSON payload (optional)
        timeout: Timeout tuple (connect, read)
    
    Returns:
        Response object or None if all retries failed
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            if method == 'POST':
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=json_data,
                    timeout=timeout
                )
            else:
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=timeout
                )
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)]))
                logger.warning(f"Rate limited. Waiting {retry_after}s before retry...")
                time.sleep(retry_after)
                continue
            
            # Success or client error (don't retry on 4xx except 429)
            if response.status_code < 500:
                return response
                
            # Server error (5xx) - retry
            logger.warning(f"Server error {response.status_code}, attempt {attempt + 1}/{MAX_RETRIES}")
            
        except requests.Timeout:
            logger.warning(f"Request timeout, attempt {attempt + 1}/{MAX_RETRIES}")
            last_error = "timeout"
        except requests.ConnectionError:
            logger.warning(f"Connection error, attempt {attempt + 1}/{MAX_RETRIES}")
            last_error = "connection"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            last_error = str(e)
        
        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)])
    
    logger.error(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None

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
    
    # Use retry logic for sending message
    response = make_request_with_retry('POST', url, headers, payload)
    
    if response is None:
        logger.error(f"Failed to send message to {to_number} after {MAX_RETRIES} attempts")
        return False
    
    if response.status_code == 200:
        result = response.json()
        logger.info(f"✅ Message sent to +{to_number}")

        # Extract WhatsApp message ID from response
        whatsapp_msg_id = None
        if 'messages' in result and len(result['messages']) > 0:
            whatsapp_msg_id = result['messages'][0].get('id')

        # Add sent message to database with WhatsApp message ID
        db.add_message(to_number, "bot", message_text, whatsapp_message_id=whatsapp_msg_id)
        return True
    else:
        logger.error(f"Failed to send message: {response.text}")
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
    
    # Use retry logic for marking as read
    response = make_request_with_retry('POST', url, headers, payload)
    
    if response is None:
        logger.error(f"Failed to mark message {message_id} as read after {MAX_RETRIES} attempts")
        return False
        
    return response.status_code == 200

def download_whatsapp_audio(media_id):
    """
    Download audio/voice message from WhatsApp Cloud API

    Args:
        media_id: The media ID from the webhook payload (audio.id)

    Returns:
        tuple: (audio_bytes, mime_type, file_extension) or (None, None, None) on error
    """
    if not WHATSAPP_TOKEN:
        logger.error("WhatsApp token not configured")
        return None, None, None

    try:
        # Step 1: Get the media URL
        url = f"https://graph.facebook.com/{API_VERSION}/{media_id}/"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}"
        }

        logger.info(f"Fetching media URL for {media_id}...")
        response = make_request_with_retry('GET', url, headers)

        if response is None or response.status_code != 200:
            logger.error(f"Failed to get media URL: {response.text if response else 'No response'}")
            return None, None, None

        media_info = response.json()
        download_url = media_info.get('url')
        mime_type = media_info.get('mime_type', 'audio/ogg')
        file_size = media_info.get('file_size', 0)

        if not download_url:
            logger.error("No download URL in response")
            return None, None, None

        logger.info(f"Media URL retrieved. Size: {file_size} bytes, Type: {mime_type}")

        # Step 2: Download the actual audio file
        logger.info(f"Downloading audio from {download_url[:50]}...")

        # Use longer timeout for download (30 seconds)
        audio_response = make_request_with_retry(
            'GET',
            download_url,
            headers,
            timeout=(3, 30)
        )

        if audio_response is None or audio_response.status_code != 200:
            logger.error(f"Failed to download audio: {audio_response.status_code if audio_response else 'No response'}")
            return None, None, None

        # Determine file extension from MIME type
        extension_map = {
            'audio/ogg': 'ogg',
            'audio/ogg; codecs=opus': 'ogg',
            'audio/mpeg': 'mp3',
            'audio/mp3': 'mp3',
            'audio/mp4': 'm4a',
            'audio/aac': 'aac',
            'audio/amr': 'amr'
        }

        file_extension = extension_map.get(mime_type, 'ogg')

        logger.info(f"✅ Audio downloaded: {len(audio_response.content)} bytes, {mime_type}")
        return audio_response.content, mime_type, file_extension

    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return None, None, None

def transcribe_audio(audio_file_path):
    """
    Transcribe audio file using OpenAI gpt-4o-transcribe

    Args:
        audio_file_path: Path to the audio file

    Returns:
        str: Transcribed text or None on error
    """
    try:
        from openai import OpenAI

        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            return None

        client = OpenAI(api_key=OPENAI_API_KEY)

        # Check file exists
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None

        # Check file size (25MB limit)
        file_size = os.path.getsize(audio_file_path)
        if file_size > 25 * 1024 * 1024:
            logger.error(f"Audio file too large: {file_size} bytes (25MB max)")
            return None

        logger.info(f"Transcribing audio: {audio_file_path} ({file_size} bytes)")

        # Transcribe with gpt-4o-transcribe
        with open(audio_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="gpt-4o-transcribe",
                response_format='text'
            )

        transcribed_text = transcript.strip()
        logger.info(f"✅ Transcription successful: {transcribed_text[:100]}{'...' if len(transcribed_text) > 100 else ''}")

        return transcribed_text

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None

@app.route('/webhook', methods=['GET'])
@app.route('/', methods=['GET'])
def verify_webhook():
    """
    Webhook verification endpoint for WhatsApp
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Debug logging
    logger.info(f"Webhook verification attempt:")
    logger.info(f"  hub.mode: '{mode}'")
    logger.info(f"  hub.verify_token: '{token}'")
    logger.info(f"  hub.challenge: '{challenge}'")
    logger.info(f"  Expected VERIFY_TOKEN: '{VERIFY_TOKEN}'")
    logger.info(f"  Token match: {token == VERIFY_TOKEN}")

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info('WEBHOOK VERIFIED')
        return challenge, 200
    else:
        logger.warning(f'Webhook verification failed: mode={mode}, token_match={token == VERIFY_TOKEN}')
        return '', 403

@app.route('/webhook', methods=['POST'])
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
    
    # Check for duplicate processing (deduplication)
    if db.is_message_processed(msg_id):
        logger.info(f"Message {msg_id} already processed, skipping duplicate")
        return
    
    # Mark as processed immediately to prevent race conditions
    db.mark_message_processed(msg_id, msg_from)
    
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
        audio_data = message.get('audio', {})
        media_id = audio_data.get('id')
        is_voice = audio_data.get('voice', False)
        mime_type = audio_data.get('mime_type', 'unknown')

        logger.info(f"   Audio: {'Voice message' if is_voice else 'Audio file'} ({mime_type})")

        # Download audio file
        audio_bytes, mime, ext = download_whatsapp_audio(media_id)

        if audio_bytes:
            # Save audio to file
            import os
            from datetime import datetime

            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audio_{msg_from}_{timestamp}.{ext}"
            filepath = os.path.join('audio', filename)

            try:
                with open(filepath, 'wb') as f:
                    f.write(audio_bytes)

                logger.info(f"✅ Audio saved: {filepath} ({len(audio_bytes)} bytes)")

                # Save metadata to database and get audio_id
                audio_id = db.save_audio_message(
                    phone_number=msg_from,
                    whatsapp_message_id=msg_id,
                    media_id=media_id,
                    file_path=filepath,
                    mime_type=mime,
                    file_extension=ext,
                    is_voice=is_voice
                )

                # Transcribe audio with gpt-4o-transcribe
                transcription = transcribe_audio(filepath)

                if transcription:
                    logger.info(f"📝 Transcription: {transcription[:100]}{'...' if len(transcription) > 100 else ''}")

                    # Update database with transcription
                    db.update_audio_transcription(audio_id, transcription)

                    # Add transcribed text as user message to database
                    db.add_message(msg_from, "user", transcription)

                    # Process transcription through AI using the same workflow as text messages
                    handle_ai_conversation(msg_from, transcription, contact_name)
                else:
                    # Transcription failed
                    logger.error("Transcription failed")
                    send_whatsapp_message(
                        msg_from,
                        "I received your audio message but couldn't transcribe it. Could you please send a text message instead?"
                    )

            except Exception as e:
                logger.error(f"Failed to save audio file: {e}")
                send_whatsapp_message(
                    msg_from,
                    "Sorry, I had trouble saving your audio message. Please try again."
                )
        else:
            logger.error(f"Failed to download audio from {msg_from}")
            send_whatsapp_message(
                msg_from,
                "Sorry, I couldn't download your audio message. Please try again."
            )
    
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

            # Helper function to normalize empty strings to None
            def normalize_field(value):
                """Convert empty strings to None for Pydantic validation"""
                return value if value and str(value).strip() else None

            client_info = ClientInfo(
                name=normalize_field(existing_profile['data']['name']),
                last_name=normalize_field(existing_profile['data']['last_name']),
                ragione_sociale=normalize_field(existing_profile['data']['ragione_sociale']),
                email=normalize_field(existing_profile['data']['email']),
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
        # Always include agent_notes based on per-contact notes (may be empty)
        contact_notes = db.get_notes(sender) or ""
        prompt_variables = {
            "client_name": client_info.name or "non_fornito",
            "client_lastname": client_info.last_name or "non_fornito",
            "client_company": client_info.ragione_sociale or "non_fornito",
            "client_email": client_info.email or "non_fornito",
            "completion_status": "Profilo completo ✅" if client_info.found_all_info else "Profilo incompleto 📝",
            "missing_fields_instruction": "" if client_info.found_all_info else f"Richiedi cortesemente: {client_info.what_is_missing}",
            "agent_notes": contact_notes
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
        
        # STEP 4: Send response to user or store as draft based on manual mode
        settings = db.get_settings(sender)
        manual_mode = bool(settings.get('manual_mode'))

        if ai_response:
            if manual_mode:
                # Save draft and do not send
                db.save_ai_draft(sender, ai_response)
                logger.info(f"📝 Draft stored for +{sender} (Manuale ON)")
            else:
                # Clear any existing draft before sending automatic response
                db.clear_ai_draft(sender)

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
            if not manual_mode:
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

    # Update message status in database
    if msg_id and status_type:
        db.update_message_status(msg_id, status_type)

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

@app.route('/api/message-statuses/<phone>')
def api_get_message_statuses(phone):
    """
    API endpoint to get only message statuses for a specific phone number (lightweight)
    """
    statuses = db.get_message_statuses(phone)
    return jsonify(statuses)

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
    
    # Auto-enable Manuale when sending a manual message
    try:
        db.set_manual_mode(phone, True)
    except Exception as e:
        logger.warning(f"Could not enable Manuale automatically for {phone}: {e}")

    success = send_whatsapp_message(phone, message)
    return jsonify({'success': success})

@app.route('/api/settings/<phone>', methods=['GET'])
def api_get_settings(phone):
    try:
        settings = db.get_settings(phone)
        return jsonify({'manual_mode': bool(settings.get('manual_mode', False))})
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'manual_mode': False}), 200

@app.route('/api/settings/<phone>', methods=['POST'])
def api_set_settings(phone):
    try:
        data = request.json or {}
        manual = bool(data.get('manual_mode', False))
        db.set_manual_mode(phone, manual)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error setting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/draft/<phone>', methods=['GET'])
def api_get_draft(phone):
    try:
        draft = db.get_ai_draft(phone)
        if draft:
            return jsonify({'draft': draft['text'], 'created_at': draft['created_at']})
        return jsonify({'draft': None, 'created_at': None})
    except Exception as e:
        logger.error(f"Error getting draft: {e}")
        return jsonify({'draft': None, 'created_at': None}), 200

@app.route('/api/draft/<phone>/clear', methods=['POST'])
def api_clear_draft(phone):
    try:
        db.clear_ai_draft(phone)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing draft: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/draft/<phone>/regenerate', methods=['POST'])
def api_regenerate_draft(phone):
    if not ai_manager:
        return jsonify({'success': False, 'error': 'OpenAI not configured'}), 503
    try:
        data = request.json or {}
        extra = (data.get('regenerate_notes') or '').strip()

        # Build agent_notes combining persistent notes and extra notes
        base_notes = db.get_notes(phone) or ''
        if base_notes and extra:
            combined_notes = base_notes + "\n\n---\n" + extra
        else:
            combined_notes = base_notes or extra or ''

        # Use last user message for a robust regeneration context
        last_user_msg = db.get_last_user_message(phone)
        if not last_user_msg:
            return jsonify({'success': False, 'error': 'No previous user message found to regenerate from.'}), 400

        # Minimal prompt variables (others not strictly needed for regenerate)
        prompt_variables = {
            'client_name': 'non_fornito',
            'client_lastname': 'non_fornito',
            'client_company': 'non_fornito',
            'client_email': 'non_fornito',
            'completion_status': '',
            'missing_fields_instruction': '',
            'agent_notes': combined_notes,
        }

        new_draft = ai_manager.generate_response(phone, last_user_msg, prompt_variables)
        if new_draft:
            db.save_ai_draft(phone, new_draft)
            return jsonify({'success': True, 'draft': new_draft})
        else:
            return jsonify({'success': False, 'error': 'No draft generated'}), 500
    except Exception as e:
        logger.error(f"Error regenerating draft: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            'found_all_info': profile['found_all_info'],
            'notes': profile.get('notes')
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

        # Update notes if provided
        if 'notes' in data:
            try:
                db.set_notes(phone, (data.get('notes') or '').strip() or None)
            except Exception as e:
                logger.warning(f"Could not update notes for {phone}: {e}")
        
        if success:
            logger.info(f"Profile manually updated for {phone} via dashboard")
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/canned-responses', methods=['GET'])
def api_get_canned_responses():
    """
    API endpoint to get canned responses (slash commands)
    Optional query parameter ?q=/shortcut to filter by shortcut
    """
    try:
        query = request.args.get('q', '').strip()

        # If query starts with /, use it to filter
        if query.startswith('/'):
            responses = db.get_canned_responses(query)
        else:
            responses = db.get_canned_responses()

        return jsonify(responses)
    except Exception as e:
        logger.error(f"Error fetching canned responses: {e}")
        return jsonify([]), 500

@app.route('/api/audio/<phone>', methods=['GET'])
def api_get_audio_messages(phone):
    """
    API endpoint to get audio messages for a phone number
    """
    try:
        audio_messages = db.get_audio_messages(phone)
        return jsonify(audio_messages)
    except Exception as e:
        logger.error(f"Error fetching audio messages for {phone}: {e}")
        return jsonify([]), 500

@app.route('/audio/<filename>', methods=['GET'])
def serve_audio_file(filename):
    """
    Serve audio file for playback in dashboard
    """
    try:
        from flask import send_from_directory
        import os

        # Security check: ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Suspicious audio file request: {filename}")
            return "Invalid filename", 400

        audio_dir = os.path.join(os.getcwd(), 'audio')

        # Check if file exists
        file_path = os.path.join(audio_dir, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Audio file not found: {filename}")
            return "Audio file not found", 404

        # Determine MIME type from extension
        ext = filename.split('.')[-1].lower()
        mime_type_map = {
            'ogg': 'audio/ogg; codecs=opus',  # WhatsApp voice messages use Opus codec
            'mp3': 'audio/mpeg',
            'm4a': 'audio/mp4',
            'aac': 'audio/aac',
            'amr': 'audio/amr'
        }
        mime_type = mime_type_map.get(ext, 'audio/ogg; codecs=opus')

        logger.info(f"Serving audio file: {filename} with MIME type: {mime_type}")
        return send_from_directory(audio_dir, filename, mimetype=mime_type)
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {e}")
        return "Error serving audio file", 500

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
