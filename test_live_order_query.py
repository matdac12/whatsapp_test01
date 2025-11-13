#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live test of order query with actual OpenAI API call
Simulates a WhatsApp user asking about their order
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_live_order_query():
    """Test actual OpenAI API call with order tools"""

    logger.info("=" * 80)
    logger.info("LIVE ORDER QUERY TEST")
    logger.info("=" * 80)

    try:
        # Import required modules
        from openai_conversation_manager import OpenAIConversationManager
        from order_tools import AVAILABLE_TOOLS
        from database import db

        # Get credentials
        api_key = os.environ.get('OPENAI_API_KEY')
        prompt_id = os.environ.get('OPENAI_PROMPT_ID')
        model = os.environ.get('OPENAI_MODEL', 'gpt-4.1')

        if not api_key or not prompt_id:
            logger.error("❌ Missing OpenAI credentials in .env file")
            logger.error("   Required: OPENAI_API_KEY, OPENAI_PROMPT_ID")
            return False

        logger.info(f"✅ Loaded credentials")
        logger.info(f"   Model: {model}")
        logger.info(f"   Prompt ID: {prompt_id[:20]}...")
        logger.info(f"   API Key: {api_key[:20]}...")

        # Initialize conversation manager
        logger.info("\n📞 Initializing OpenAI Conversation Manager...")
        ai_manager = OpenAIConversationManager(
            api_key=api_key,
            prompt_id=prompt_id,
            model=model
        )

        # Test phone number
        phone = "+393404570180"

        # Reset conversation to start fresh
        logger.info(f"🔄 Resetting conversation to start fresh...")
        ai_manager.reset_conversation(phone)

        logger.info(f"✅ Conversation manager initialized with fresh conversation")

        # Test message
        test_message = "Quando arriva il mio ultimo ordine?"

        logger.info("\n" + "=" * 80)
        logger.info("SIMULATING WHATSAPP MESSAGE")
        logger.info("=" * 80)
        logger.info(f"📱 From: {phone}")
        logger.info(f"💬 Message: {test_message}")
        logger.info(f"🔧 Tools: {len(AVAILABLE_TOOLS)} available")
        for tool in AVAILABLE_TOOLS:
            logger.info(f"     - {tool['name']}")

        # Get profile for prompt variables
        profile = db.get_profile(phone)
        notes = db.get_notes(phone) or ""

        prompt_variables = {
            'client_name': profile.get('name') if profile and profile.get('name') else 'non_fornito',
            'client_lastname': profile.get('last_name') if profile and profile.get('last_name') else 'non_fornito',
            'client_company': profile.get('ragione_sociale') if profile and profile.get('ragione_sociale') else 'non_fornito',
            'client_email': profile.get('email') if profile and profile.get('email') else 'non_fornito',
            'client_phone_number': phone,
            'completion_status': '',
            'missing_fields_instruction': '',
            'agent_notes': notes
        }

        logger.info("\n🚀 Calling OpenAI API with tools...")
        logger.info("-" * 80)

        # Make the actual API call
        response = ai_manager.generate_response(
            user_id=phone,
            message=test_message,
            prompt_variables=prompt_variables,
            tools=AVAILABLE_TOOLS
        )

        logger.info("-" * 80)
        logger.info("\n✅ RESPONSE RECEIVED")
        logger.info("=" * 80)
        logger.info(f"🤖 AI Response:\n")
        logger.info(response)
        logger.info("=" * 80)

        # Check if response contains order information
        if any(keyword in response.lower() for keyword in ['laptop', 'ordine', 'delivery', 'consegna', 'novembre', 'giorni']):
            logger.info("\n🎉 SUCCESS! Response contains order information!")
            logger.info("✅ Tool was likely called and data was retrieved")
        else:
            logger.warning("\n⚠️  Response doesn't contain obvious order info")
            logger.warning("   Check if tool was actually called")

        return True

    except Exception as e:
        logger.error(f"\n❌ ERROR during live test: {e}")
        import traceback
        logger.error(f"\nFull traceback:")
        logger.error(traceback.format_exc())
        return False

def main():
    logger.info("\n" + "🧪" * 40)
    logger.info("LIVE ORDER QUERY TEST WITH ACTUAL API CALL")
    logger.info("🧪" * 40 + "\n")

    logger.info("This will:")
    logger.info("  1. Load your OpenAI credentials from .env")
    logger.info("  2. Initialize the conversation manager")
    logger.info("  3. Make a REAL API call asking: 'Quando arriva il mio ultimo ordine?'")
    logger.info("  4. The AI should call the get_latest_order tool")
    logger.info("  5. Show you the final response\n")

    input("Press ENTER to start the test...")

    success = test_live_order_query()

    if success:
        logger.info("\n✅ Test completed successfully!")
        return 0
    else:
        logger.error("\n❌ Test failed - see errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
