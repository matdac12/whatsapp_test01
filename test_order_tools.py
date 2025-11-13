#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for order tools functionality
"""

import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_creation():
    """Test that orders database is created with sample data"""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Creation")
    logger.info("=" * 60)

    try:
        from orders_database import orders_db

        # Try to get orders for test user
        phone = "+393404570180"
        orders = orders_db.get_user_orders(phone)

        logger.info(f"✅ Database created successfully")
        logger.info(f"✅ Found {len(orders)} orders for {phone}")

        for order in orders:
            logger.info(f"   - {order['order_id']}: {order['product_name']} ({order['status']})")

        return True
    except Exception as e:
        logger.error(f"❌ Database creation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_tool_definitions():
    """Test that tools are properly defined"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Tool Definitions")
    logger.info("=" * 60)

    try:
        from order_tools import AVAILABLE_TOOLS, TOOL_EXECUTORS

        logger.info(f"✅ Found {len(AVAILABLE_TOOLS)} available tools")
        for tool in AVAILABLE_TOOLS:
            tool_name = tool['name']
            tool_desc = tool['description']
            logger.info(f"   - {tool_name}: {tool_desc[:60]}...")

        logger.info(f"✅ Found {len(TOOL_EXECUTORS)} tool executors")
        for name in TOOL_EXECUTORS.keys():
            logger.info(f"   - {name}")

        return True
    except Exception as e:
        logger.error(f"❌ Tool definition test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_tool_execution():
    """Test executing a tool directly"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Tool Execution")
    logger.info("=" * 60)

    try:
        from order_tools import execute_tool_call

        phone = "+393404570180"

        # Test get_latest_order
        logger.info(f"🔧 Testing get_latest_order for {phone}")
        result = execute_tool_call("get_latest_order", {"phone_number": phone})

        logger.info(f"✅ Tool executed successfully")
        logger.info(f"   Result: {result}")

        if result and 'order_id' in result:
            logger.info(f"   Order ID: {result['order_id']}")
            logger.info(f"   Product: {result['product_name']}")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   Delivery: {result['expected_delivery_date']}")
            logger.info(f"   Days until delivery: {result['days_until_delivery']}")

        return True
    except Exception as e:
        logger.error(f"❌ Tool execution test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_openai_integration():
    """Test that OpenAI conversation manager can accept tools"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: OpenAI Integration (Dry Run)")
    logger.info("=" * 60)

    try:
        from order_tools import AVAILABLE_TOOLS
        import inspect
        from openai_conversation_manager import OpenAIConversationManager

        # Check that generate_response accepts tools parameter
        sig = inspect.signature(OpenAIConversationManager.generate_response)
        params = list(sig.parameters.keys())

        logger.info(f"✅ generate_response parameters: {params}")

        if 'tools' in params:
            logger.info(f"✅ 'tools' parameter is present in generate_response()")
        else:
            logger.error(f"❌ 'tools' parameter NOT found in generate_response()")
            return False

        logger.info(f"✅ OpenAI integration looks good (dry run only, no API call)")
        return True

    except Exception as e:
        logger.error(f"❌ OpenAI integration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all tests"""
    logger.info("\n" + "🚀" * 30)
    logger.info("Starting Order Tools Tests")
    logger.info("🚀" * 30 + "\n")

    results = []

    # Run tests
    results.append(("Database Creation", test_database_creation()))
    results.append(("Tool Definitions", test_tool_definitions()))
    results.append(("Tool Execution", test_tool_execution()))
    results.append(("OpenAI Integration", test_openai_integration()))

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60 + "\n")

    if passed == total:
        logger.info("🎉 All tests passed! The order tools are ready to use.")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Start your WhatsApp bot: python3 start_openai_bot.py")
        logger.info("   2. Send a message to your WhatsApp number:")
        logger.info("      'Quando arriva il mio ultimo ordine?'")
        logger.info("   3. The AI should call the get_latest_order tool and respond!")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
