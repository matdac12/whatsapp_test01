# OpenAI Function Calling Implementation Guide

## Overview
This guide explains how to implement function calling (tools) with OpenAI's Responses API using conversations. This allows your AI agent to query external data sources (databases, APIs, etc.) and provide intelligent responses based on real-time data.

---

## Table of Contents
1. [Key Concepts](#key-concepts)
2. [Tool Definition Format](#tool-definition-format)
3. [Implementation Steps](#implementation-steps)
4. [Complete Code Examples](#complete-code-examples)
5. [Common Pitfalls](#common-pitfalls)
6. [Testing](#testing)

---

## Key Concepts

### What are Tools/Function Calling?
Tools allow the AI to call external functions when it needs information it doesn't have. The flow is:

1. **User asks question** → "When does my order arrive?"
2. **AI realizes it needs data** → Calls `get_latest_order` tool
3. **Your code executes tool** → Queries database
4. **AI receives result** → Formats natural response
5. **User gets answer** → "Your laptop arrives in 4 days"

### Responses API vs Chat Completions API
- **Chat Completions**: Tools are defined in nested `function` object
- **Responses API**: Tools are defined at top level (flatter structure)

**Important**: `pydantic_function_tool()` creates Chat Completions format, NOT Responses API format!

---

## Tool Definition Format

### ❌ WRONG Format (Chat Completions)
```python
# This is what pydantic_function_tool() creates - DON'T use for Responses API
{
    "type": "function",
    "function": {  # ← Extra nesting!
        "name": "get_order",
        "description": "...",
        "parameters": {...}
    }
}
```

### ✅ CORRECT Format (Responses API)
```python
# This is what Responses API expects
{
    "type": "function",
    "name": "get_order",  # ← Direct at top level
    "description": "Get order information for a user",
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
}
```

---

## Implementation Steps

### Step 1: Create Tool Definitions File (`order_tools.py`)

```python
#!/usr/bin/env python3
"""
Order tools for OpenAI function calling
"""
import logging
from orders_database import orders_db

logger = logging.getLogger(__name__)

# Define tools in Responses API format
AVAILABLE_TOOLS = [
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
    # Add more tools here...
]

# Tool execution functions
def execute_get_latest_order(phone_number: str) -> dict:
    """Execute get_latest_order tool"""
    logger.debug(f"🔧 Tool called: get_latest_order for {phone_number}")

    order = orders_db.get_latest_order(phone_number)
    if not order:
        return {"message": "No orders found"}

    # Calculate days until delivery
    from datetime import datetime
    delivery_date = datetime.strptime(order['expected_delivery_date'], '%Y-%m-%d')
    today = datetime.now()
    days_until = (delivery_date - today).days

    return {
        'order_id': order['order_id'],
        'status': order['status'],
        'expected_delivery_date': order['expected_delivery_date'],
        'product_name': order['product_name'],
        'days_until_delivery': days_until
    }

# Tool execution dispatcher
TOOL_EXECUTORS = {
    "GetLatestOrder": execute_get_latest_order,
    # Map tool names to executor functions
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
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {"error": str(e)}
```

---

### Step 2: Modify Conversation Manager

#### A. Update `generate_response()` method signature

```python
def generate_response(self, user_id: str, message: str,
                     prompt_variables: Optional[Dict[str, str]] = None,
                     tools: Optional[List[Any]] = None) -> str:  # ← Add tools parameter
```

#### B. Pass prompt variables (including phone number for tools)

```python
# Build prompt configuration
prompt_config = {"id": self.prompt_id}

# Add variables if provided
if prompt_variables:
    prompt_config["variables"] = prompt_variables
```

**Important**: Your prompt template should include a `{{client_phone_number}}` variable.
The phone number will be passed via `prompt_variables` from your webhook:

```python
prompt_variables = {
    'client_name': client_info.name or 'non_fornito',
    'client_lastname': client_info.last_name or 'non_fornito',
    'client_company': client_info.ragione_sociale or 'non_fornito',
    'client_email': client_info.email or 'non_fornito',
    'client_phone_number': sender,  # ← Phone number for tool calls
    'completion_status': '...',
    'missing_fields_instruction': '...',
    'agent_notes': contact_notes
}
```

#### C. Add tools to API request

```python
# Build request parameters for Responses API
request_params = {
    "prompt": prompt_config,
    "input": [{"role": "user", "content": message_utf8}],
    "model": self.model,
    "conversation": conversation_id
}

# Add tools if provided
if tools:
    request_params["tools"] = tools
    request_params["tool_choice"] = "auto"  # Let AI decide when to use tools

# Generate response
response = self.client.responses.create(**request_params)
```

#### D. Check for function calls

```python
# Check if response contains tool calls
if hasattr(response, 'output') and response.output:
    first_message = response.output[0]
    if hasattr(first_message, 'type') and first_message.type == 'function_call':
        logger.debug(f"🔧 Response contains function call: {first_message.name}")

        # Execute the tool and get final response
        final_response = self._handle_tool_calls_responses(
            conversation_id=conversation_id,
            original_input=[{"role": "user", "content": message_utf8}],
            response_output=response.output,
            prompt_config=prompt_config,
            tools=tools
        )
        return final_response

# No tool calls, return regular response
output_text = response.output_text
return output_text
```

---

### Step 3: Implement Tool Call Handler

```python
def _handle_tool_calls_responses(self, conversation_id: str, original_input: List[Dict],
                                 response_output: List[Any], prompt_config: Dict,
                                 tools: List[Any]) -> str:
    """
    Handle function calls from Responses API

    IMPORTANT: When using conversations, the conversation already stores the history.
    We ONLY need to send the function_call_output, not duplicate the function_call.
    """
    from order_tools import execute_tool_call
    import json

    # Build input list with only function outputs
    input_list = []

    # Process each function call in the output
    for item in response_output:
        if item.type == "function_call":
            tool_name = item.name
            call_id = item.call_id  # ← CRITICAL: Must use call_id to match the call
            tool_arguments = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments

            logger.debug(f"🔧 Executing tool: {tool_name} (call_id: {call_id})")
            logger.debug(f"🔧 Arguments: {tool_arguments}")

            # Execute the tool
            result = execute_tool_call(tool_name, tool_arguments)

            logger.debug(f"🔧 Tool result: {result}")

            # Add only the function call output
            input_list.append({
                "type": "function_call_output",
                "call_id": call_id,  # ← MUST match the call_id from function_call
                "output": json.dumps(result)
            })

    # Send only the function outputs (conversation already has the calls)
    logger.debug(f"🔧 Sending function outputs back to OpenAI ({len(input_list)} items)")

    response = self.client.responses.create(
        prompt=prompt_config,
        input=input_list,  # ← Only function_call_output items
        model=self.model,
        conversation=conversation_id,
        tools=tools,
        tool_choice="auto"
    )

    # Return final response text
    output_text = response.output_text
    logger.debug(f"✅ Final response after tool execution: {output_text[:100]}...")

    return output_text
```

---

### Step 4: Pass Tools to Conversation Manager

In your webhook/main application:

```python
from order_tools import AVAILABLE_TOOLS

# When generating response
ai_response = ai_manager.generate_response(
    user_id=sender,
    message=text,
    prompt_variables=prompt_variables,
    tools=AVAILABLE_TOOLS  # ← Pass tools here
)
```

---

## Complete Code Examples

### Example: Database Manager (`orders_database.py`)

```python
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

class OrdersDatabase:
    def __init__(self, db_path: str = "orders.db"):
        self.db_path = db_path
        self._create_tables()
        self._insert_sample_data()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expected_delivery_date DATE NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def get_latest_order(self, phone_number: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders
                WHERE phone_number = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (phone_number,))

            row = cursor.fetchone()
            return dict(row) if row else None

orders_db = OrdersDatabase()
```

---

## Common Pitfalls

### ❌ Pitfall 1: Using `pydantic_function_tool()`
```python
# DON'T do this for Responses API:
import openai
tools = [openai.pydantic_function_tool(MyModel)]
```
**Why**: Creates Chat Completions format with nested `function` key.

**Solution**: Define tools manually in Responses API format.

---

### ❌ Pitfall 2: Duplicating function_call in input
```python
# DON'T do this:
input_list = original_input + response.output + [function_call_output]
```
**Why**: When using conversations, the function_call is already stored. Sending it again causes "Duplicate item" error.

**Solution**: Only send `function_call_output` items.

---

### ❌ Pitfall 3: Mismatched call_id
```python
# DON'T do this:
{
    "type": "function_call_output",
    "id": call_id,  # ← WRONG key name
    "output": "..."
}
```
**Why**: The key must be `call_id`, not `id`.

**Solution**: Use `call_id` consistently.

---

### ❌ Pitfall 4: Missing phone number in prompt variables
```python
# If AI doesn't know the user's phone number, it will ask the user instead of calling the tool
```
**Solution**: Add `client_phone_number` to your prompt template and pass it via `prompt_variables`:
```python
prompt_variables = {
    # ... other variables ...
    'client_phone_number': sender,  # ← Required for tool calls
}
```

---

## Testing

### Test Script Template

```python
from openai_conversation_manager import OpenAIConversationManager
from order_tools import AVAILABLE_TOOLS

# Initialize
ai_manager = OpenAIConversationManager(api_key="...", prompt_id="...", model="gpt-4.1")

# Test query
phone = "+393404570180"
message = "Quando arriva il mio ultimo ordine?"

# Reset conversation for fresh start
ai_manager.reset_conversation(phone)

# Get profile and build prompt variables
prompt_variables = {
    'client_name': 'non_fornito',
    'client_lastname': 'non_fornito',
    'client_company': 'non_fornito',
    'client_email': 'non_fornito',
    'client_phone_number': phone,  # ← Required for tool calls
    'completion_status': '',
    'missing_fields_instruction': '',
    'agent_notes': ''
}

# Make API call with tools
response = ai_manager.generate_response(
    user_id=phone,
    message=message,
    prompt_variables=prompt_variables,
    tools=AVAILABLE_TOOLS
)

print(f"Response: {response}")
```

### Expected Output
```
Response: Il tuo ultimo ordine (Laptop Dell XPS 15) è in fase di elaborazione
e la consegna è prevista per il 18 novembre 2025, quindi tra circa 4 giorni.
```

---

## API Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Message: "When does my order arrive?"              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. responses.create(                                        │
│      input=[{"role": "user", "content": "..."}],           │
│      tools=[...],                                           │
│      conversation=conv_id                                   │
│    )                                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Response contains function_call:                        │
│    {                                                        │
│      "type": "function_call",                              │
│      "call_id": "fc_abc123...",                            │
│      "name": "GetLatestOrder",                             │
│      "arguments": {"phone_number": "+39..."}              │
│    }                                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Execute Tool Locally:                                   │
│    result = execute_get_latest_order("+39...")             │
│    → Returns: {order_id, status, delivery_date, ...}      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. responses.create(                                        │
│      input=[{                                              │
│        "type": "function_call_output",                     │
│        "call_id": "fc_abc123...",  ← MUST MATCH           │
│        "output": json.dumps(result)                        │
│      }],                                                   │
│      conversation=conv_id                                  │
│    )                                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Final Response:                                         │
│    "Your laptop arrives in 4 days"                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Responses API uses flat tool format** - No nested `function` object
2. **Conversations store history** - Only send `function_call_output`, not duplicates
3. **`call_id` is critical** - Must match between function_call and function_call_output
4. **Phone number context** - Add to prompt variables so AI knows to use it
5. **Tool execution is synchronous** - Execute tools locally, then send results back

---

## Extending with More Tools

### Adding a New Tool

1. **Define tool in `AVAILABLE_TOOLS`**:
```python
{
    "type": "function",
    "name": "GetAllOrders",
    "description": "Get all orders for a user",
    "parameters": {
        "type": "object",
        "properties": {
            "phone_number": {"type": "string", "description": "User phone"}
        },
        "required": ["phone_number"]
    }
}
```

2. **Create executor function**:
```python
def execute_get_all_orders(phone_number: str) -> dict:
    orders = orders_db.get_user_orders(phone_number)
    return {"orders": orders, "total_count": len(orders)}
```

3. **Register in `TOOL_EXECUTORS`**:
```python
TOOL_EXECUTORS = {
    "GetLatestOrder": execute_get_latest_order,
    "GetAllOrders": execute_get_all_orders,  # ← Add here
}
```

That's it! The AI will automatically decide when to use the new tool.

---

*Last updated: November 13, 2025*
*Working implementation with OpenAI Responses API + Conversations*
