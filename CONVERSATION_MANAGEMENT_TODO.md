# OpenAI Conversation Management - Implementation Guide

## Current Situation
Currently, we maintain ONE OpenAI conversation per WhatsApp user forever. This means the AI context grows indefinitely, leading to:
- Increased API costs (more tokens per request)
- Slower response times
- Irrelevant old context polluting new conversations

## Solution: Hybrid Conversation Management
Implement a **48-72 hour conversation window** with smart context preservation.

## Implementation Steps

### Step 1: Database Schema Updates
Add these fields to the `conversations` table:
```sql
ALTER TABLE conversations ADD COLUMN last_message_at TIMESTAMP;
ALTER TABLE conversations ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE conversations ADD COLUMN parent_conversation_id TEXT;
```

### Step 2: Create Conversation Summary System
Create new file `conversation_summarizer.py`:
```python
class ConversationSummarizer:
    def __init__(self, openai_client):
        self.client = openai_client
    
    def generate_summary(self, phone_number: str) -> str:
        """
        Generate a summary of past conversations for context injection
        Returns a formatted string with:
        - Client info (from profiles)
        - Recent topics discussed
        - Any unresolved issues
        - Noted preferences
        """
        # Get last 50 messages from database
        # Use GPT to summarize key points
        # Return formatted context string
```

### Step 3: Modify `openai_conversation_manager.py`

#### Add configuration constants:
```python
CONVERSATION_TIMEOUT_HOURS = 48  # Configurable
MAX_CONVERSATION_MESSAGES = 50   # Limit context size
```

#### Update `get_or_create_conversation()` method:
```python
def get_or_create_conversation(self, user_id: str, initial_message: Optional[str] = None) -> str:
    """
    MODIFIED: Check if existing conversation is still active (< 48 hours old)
    If expired, create new conversation with summary context
    """
    
    # 1. Check if user has existing conversation
    existing_conv_id = db.get_conversation(user_id)
    
    if existing_conv_id:
        # 2. Check last message timestamp
        last_message_time = db.get_conversation_last_message_time(user_id)
        hours_since = calculate_hours_since(last_message_time)
        
        if hours_since < CONVERSATION_TIMEOUT_HOURS:
            # 3a. Use existing conversation
            return existing_conv_id
        else:
            # 3b. Mark old conversation as inactive
            db.mark_conversation_inactive(existing_conv_id)
    
    # 4. Generate summary of past interactions
    summary = self.generate_conversation_summary(user_id)
    
    # 5. Create new conversation with summary as initial context
    new_conversation = self.client.conversations.create(
        items=[
            {"type": "message", "role": "system", "content": summary},
            {"type": "message", "role": "user", "content": initial_message}
        ] if initial_message else [
            {"type": "message", "role": "system", "content": summary}
        ]
    )
    
    # 6. Save new conversation with parent reference
    db.save_conversation(user_id, new_conversation.id, parent_id=existing_conv_id)
    
    return new_conversation.id
```

### Step 4: Add Summary Generation Method
```python
def generate_conversation_summary(self, user_id: str) -> str:
    """
    Generate a context summary for new conversations
    """
    # Get client profile
    profile = db.get_profile(user_id)
    
    # Get recent conversation topics (last 7 days)
    recent_messages = db.get_messages_since(user_id, days=7, limit=20)
    
    # Build context summary
    summary_parts = []
    
    # Add client info if available
    if profile and profile['found_all_info']:
        summary_parts.append(
            f"Cliente: {profile['name']} {profile['last_name']} "
            f"di {profile['ragione_sociale']} ({profile['email']})"
        )
    
    # Add interaction history
    if recent_messages:
        # Use GPT to extract key topics (optional, or do it simply)
        topics = extract_topics(recent_messages)  # Simple keyword extraction
        summary_parts.append(f"Argomenti recenti: {', '.join(topics)}")
    
    # Add any open issues or notes
    # (This could come from a new 'notes' table in the future)
    
    return "\n".join(summary_parts) if summary_parts else ""
```

### Step 5: Update Database Manager (`database.py`)

Add new methods:
```python
def get_conversation_last_message_time(self, phone_number: str) -> Optional[datetime]:
    """Get timestamp of last message in a conversation"""
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(timestamp) as last_message 
            FROM messages 
            WHERE phone_number = ?
        """, (phone_number,))
        row = cursor.fetchone()
        return datetime.fromisoformat(row['last_message']) if row['last_message'] else None

def mark_conversation_inactive(self, conversation_id: str):
    """Mark a conversation as inactive"""
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations 
            SET is_active = 0 
            WHERE conversation_id = ?
        """, (conversation_id,))

def get_messages_since(self, phone_number: str, days: int, limit: int = 50) -> List[Dict]:
    """Get messages from the last N days"""
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sender, message, timestamp 
            FROM messages 
            WHERE phone_number = ? 
            AND timestamp > datetime('now', ? || ' days')
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (phone_number, -days, limit))
        # Return as list of dicts
```

### Step 6: Add Configuration Options

Create `config.py`:
```python
# Conversation Management Settings
CONVERSATION_TIMEOUT_HOURS = int(os.environ.get('CONVERSATION_TIMEOUT_HOURS', 48))
INCLUDE_SUMMARY_IN_NEW_CONVERSATIONS = os.environ.get('INCLUDE_SUMMARY', 'true').lower() == 'true'
MAX_SUMMARY_MESSAGES = int(os.environ.get('MAX_SUMMARY_MESSAGES', 20))
```

### Step 7: Testing Checklist

1. **Test conversation expiry**:
   - Send message → wait 48+ hours → send again
   - Verify new conversation created
   - Verify summary included

2. **Test summary generation**:
   - Create conversation with multiple messages
   - Let expire
   - Check summary contains key info

3. **Test continuity within window**:
   - Send multiple messages within 48 hours
   - Verify same conversation used

4. **Test profile integration**:
   - Ensure client info included in summary
   - Test with complete and incomplete profiles

5. **Performance testing**:
   - Compare response times (old vs new system)
   - Measure token usage reduction

### Step 8: Migration for Existing Data

```python
# One-time migration script
def migrate_existing_conversations():
    """
    Mark all existing conversations with last_message_at
    based on their most recent message
    """
    all_conversations = db.get_all_conversations()
    for phone, conv_id in all_conversations.items():
        last_msg_time = db.get_conversation_last_message_time(phone)
        if last_msg_time:
            db.update_conversation_last_message_time(phone, last_msg_time)
```

## Configuration Options to Implement

### Environment Variables:
```env
# Conversation Management
CONVERSATION_TIMEOUT_HOURS=48        # Hours before new conversation
MAX_CONTEXT_MESSAGES=50              # Max messages to include in context
INCLUDE_CLIENT_SUMMARY=true          # Include client profile in new conversations
SUMMARIZE_OLD_CONVERSATIONS=true     # Generate AI summary of past chats
```

## Benefits After Implementation

1. **Cost Reduction**: ~70-80% reduction in OpenAI API costs
2. **Performance**: 2-3x faster response times
3. **Better Context**: Focused conversations without irrelevant history
4. **Full History**: Database still has everything for dashboard viewing
5. **Flexibility**: Easy to adjust timeout period based on use case

## Future Enhancements (Phase 2)

1. **Topic-based conversations**: New conversation for different topics
2. **Manual reset command**: User can type `/new` to start fresh
3. **Conversation templates**: Different prompts for support vs sales
4. **Summary quality improvements**: Use GPT-4 to generate better summaries
5. **Conversation analytics**: Track average length, common topics, etc.

## Implementation Order

1. First: Database schema updates
2. Second: Basic timeout logic (without summaries)
3. Third: Add summary generation
4. Fourth: Test with small group
5. Fifth: Roll out to all users

## Notes for Implementation

- Start with a LONGER timeout (72-96 hours) and reduce based on testing
- Make timeout configurable without code changes (env variable)
- Log when new conversations are created for monitoring
- Consider adding a "conversation_created_reason" field for analytics
- Keep the old conversation IDs in database for audit trail

---

**Implementation Estimate**: 4-6 hours
**Testing Required**: 2-3 hours
**Risk Level**: Low (backward compatible)
**Priority**: High (immediate cost savings)