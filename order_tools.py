#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Order Tools for OpenAI Function Calling
Defines Pydantic models and tool functions for querying order data
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
import openai
from orders_database import orders_db

logger = logging.getLogger(__name__)

# === Pydantic Models for Tool Outputs ===

class OrderInfo(BaseModel):
    """Information about a single order"""
    order_id: str = Field(description="Unique order identifier")
    status: str = Field(description="Order status: processing, shipped, or delivered")
    expected_delivery_date: str = Field(description="Expected delivery date in YYYY-MM-DD format")
    product_name: str = Field(description="Name of the product ordered")
    quantity: int = Field(description="Quantity ordered")
    total_amount: float = Field(description="Total amount in euros")
    created_at: str = Field(description="Order creation timestamp")

class OrdersList(BaseModel):
    """List of orders for a user"""
    orders: List[OrderInfo] = Field(description="List of user orders")
    total_count: int = Field(description="Total number of orders")

class LatestOrder(BaseModel):
    """Most recent order information"""
    order_id: str = Field(description="Unique order identifier")
    status: str = Field(description="Order status")
    expected_delivery_date: str = Field(description="Expected delivery date")
    product_name: str = Field(description="Product name")
    days_until_delivery: int = Field(description="Number of days until delivery (negative if already delivered)")

# === Simplified Tool Models (Direct Pydantic for Responses API) ===

class GetUserOrders(BaseModel):
    """Get all orders for a user. Returns a list of all orders with details including status, delivery date, products, and amounts."""
    phone_number: str = Field(description="User's phone number in international format (e.g., +393404570180)")

class GetLatestOrder(BaseModel):
    """Get the most recent order for a user with delivery information. Use this when the user asks about their latest/most recent order or expected delivery date."""
    phone_number: str = Field(description="User's phone number in international format")

class SearchOrdersByStatus(BaseModel):
    """Search and filter orders by status (processing, shipped, or delivered). Use this when user asks about orders with specific status."""
    phone_number: str = Field(description="User's phone number in international format")
    status: str = Field(description="Order status to filter by: 'processing', 'shipped', or 'delivered'")

# === Tool Execution Functions ===

def execute_get_user_orders(phone_number: str) -> OrdersList:
    """Execute get_user_orders tool"""
    logger.debug(f"🔧 Tool called: get_user_orders for {phone_number}")

    orders = orders_db.get_user_orders(phone_number)
    order_list = [OrderInfo(**order) for order in orders]

    return OrdersList(
        orders=order_list,
        total_count=len(order_list)
    )

def execute_get_latest_order(phone_number: str) -> Optional[LatestOrder]:
    """Execute get_latest_order tool"""
    logger.debug(f"🔧 Tool called: get_latest_order for {phone_number}")

    order = orders_db.get_latest_order(phone_number)

    if not order:
        return None

    # Calculate days until delivery
    from datetime import datetime
    delivery_date = datetime.strptime(order['expected_delivery_date'], '%Y-%m-%d')
    today = datetime.now()
    days_until = (delivery_date - today).days

    return LatestOrder(
        order_id=order['order_id'],
        status=order['status'],
        expected_delivery_date=order['expected_delivery_date'],
        product_name=order['product_name'],
        days_until_delivery=days_until
    )

def execute_search_orders_by_status(phone_number: str, status: str) -> OrdersList:
    """Execute search_orders_by_status tool"""
    logger.debug(f"🔧 Tool called: search_orders_by_status for {phone_number}, status={status}")

    orders = orders_db.search_orders_by_status(phone_number, status)
    order_list = [OrderInfo(**order) for order in orders]

    return OrdersList(
        orders=order_list,
        total_count=len(order_list)
    )

# === Tool Definitions for OpenAI Responses API ===

# Responses API expects a different format than chat.completions!
# Format: {"type": "function", "name": "...", "description": "...", "parameters": {...}}
# NOT: {"type": "function", "function": {"name": "...", ...}}

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "name": "GetUserOrders",
        "description": "Get all orders for a user. Returns a list of all orders with details including status, delivery date, products, and amounts.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "User's phone number in international format (e.g., +393404570180)"
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "type": "function",
        "name": "GetLatestOrder",
        "description": "Get the most recent order for a user with delivery information. Use this when the user asks about their latest/most recent order or expected delivery date.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "User's phone number in international format"
                }
            },
            "required": ["phone_number"]
        }
    },
    {
        "type": "function",
        "name": "SearchOrdersByStatus",
        "description": "Search and filter orders by status (processing, shipped, or delivered). Use this when user asks about orders with specific status.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "User's phone number in international format"
                },
                "status": {
                    "type": "string",
                    "description": "Order status to filter by: 'processing', 'shipped', or 'delivered'"
                }
            },
            "required": ["phone_number", "status"]
        }
    }
]

# Tool execution dispatcher - map function names to executors
TOOL_EXECUTORS = {
    "GetUserOrders": execute_get_user_orders,
    "GetLatestOrder": execute_get_latest_order,
    "SearchOrdersByStatus": execute_search_orders_by_status,
}

def execute_tool_call(tool_name: str, tool_arguments: dict) -> dict:
    """
    Execute a tool call and return the result

    Args:
        tool_name: Name of the tool to execute
        tool_arguments: Arguments for the tool

    Returns:
        Tool execution result as a dictionary
    """
    if tool_name not in TOOL_EXECUTORS:
        logger.error(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        executor = TOOL_EXECUTORS[tool_name]
        result = executor(**tool_arguments)

        # Convert Pydantic model to dict
        if result is None:
            return {"message": "No orders found for this user"}

        return result.model_dump() if hasattr(result, 'model_dump') else result

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}
