# Webhook Behavior Analysis: Manual Profile Updates

## Executive Summary

This document analyzes the current webhook behavior when profiles are updated manually through the dashboard versus automatically through WhatsApp messages. Currently, webhooks are only triggered when profiles are completed through message extraction, not manual updates.

## Current System Behavior

### 1. Message-Based Profile Completion (Working)

When a user sends a WhatsApp message:

```
User Message → Data Extraction → Profile Update → Check if Newly Complete → Trigger Webhook
```

**Code Flow:**
1. `webhook_openai.py`: Receives WhatsApp message
2. `data_extractor.process_message()`: Extracts data from message
3. `data_extractor.update_profile()`: Updates profile with extracted data
4. If `is_newly_complete` (was incomplete, now complete): Triggers webhook
5. `webhook_notifier.send_profile_completion_webhook()`: Sends to Make/Zapier

### 2. Manual Profile Updates (No Webhook)

When an agent updates via dashboard:

```
Dashboard Edit → API Call → Manual Update → Update Database → No Webhook
```

**Code Flow:**
1. Dashboard calls `/api/profile/<phone>` endpoint
2. `webhook_openai.api_update_profile()`: Receives update request
3. `data_extractor.update_profile_manually()`: Updates database
4. Database recalculates `found_all_info` flag
5. **No webhook triggered** even if profile becomes complete

## Detailed Analysis of Your Questions

### Question 1: Agent Deletes a Field (e.g., Company Name)

**What happens:**
- `found_all_info` flag changes from `true` to `false`
- Profile marked as incomplete in database
- No webhook triggered (correct behavior)

**Code responsible** (`database.py:save_profile`):
```python
# Check if all required fields are present
found_all_info = all([
    profile_data.get('name'),
    profile_data.get('last_name'),
    profile_data.get('ragione_sociale'),
    profile_data.get('email')
])
```

### Question 2: Agent Adds Missing Field

**What happens:**
- `found_all_info` flag changes from `false` to `true`
- Profile marked as complete in database
- **No webhook triggered** (potential issue)

**Why no webhook:**
The webhook logic only exists in `update_profile()` method:
```python
# From data_extractor.py
if is_newly_complete:
    logger.info(f"Profile completed for {whatsapp_number}")
    # Send webhook notification
    notify_profile_completion(whatsapp_number, profile_for_webhook)
```

But `update_profile_manually()` doesn't have this logic.

## Root Cause

The system was designed with the assumption that profile completion happens through conversation flow, not manual intervention. The webhook represents "user has provided all information through chat" rather than "profile has all fields filled".

## Proposed Enhancement

### Implementation Changes Required

**1. Modify `data_extractor.update_profile_manually()`:**

```python
def update_profile_manually(self, whatsapp_number: str, name: Optional[str] = None, 
                          last_name: Optional[str] = None, ragione_sociale: Optional[str] = None,
                          email: Optional[str] = None) -> bool:
    try:
        existing_data = db.get_profile(whatsapp_number)
        
        # Check if profile was complete before update
        was_complete = bool(existing_data.get('found_all_info', False)) if existing_data else False
        
        # ... existing update logic ...
        
        # After saving to database
        db.save_profile(whatsapp_number, updated_data)
        
        # Check if newly complete
        is_complete = all([
            updated_data['name'],
            updated_data['last_name'],
            updated_data['ragione_sociale'],
            updated_data['email']
        ])
        
        # Trigger webhook if newly complete
        if not was_complete and is_complete:
            logger.info(f"Profile manually completed for {whatsapp_number}, triggering webhook")
            try:
                profile_for_webhook = db.get_profile(whatsapp_number)
                if profile_for_webhook:
                    notify_profile_completion(whatsapp_number, profile_for_webhook)
            except Exception as e:
                logger.error(f"Failed to send webhook for manual completion: {e}")
                # Don't fail the update operation
        
        return True
```

## Business Considerations

### Arguments AGAINST Manual Webhook

1. **Agent Already Knows**: When an agent manually completes a profile, they're aware of the completion and can take immediate action

2. **Different Context**: Manual completion might not warrant the same automated follow-up as organic completion

3. **Potential Spam**: If agents frequently edit profiles, could trigger unnecessary webhooks

4. **Email Redundancy**: Sending an email about a profile the agent just completed seems redundant

### Arguments FOR Manual Webhook

1. **Consistency**: All profile completions trigger the same workflow

2. **Audit Trail**: External systems get notified regardless of completion method

3. **Team Coordination**: Other team members/systems are notified when any profile is ready

4. **Automation**: Subsequent workflows (CRM update, welcome email) trigger automatically

## Alternative Approaches

### Option 1: Separate Webhook Event
```json
{
    "event": "profile.manually_completed",
    "completed_by": "agent",
    "timestamp": "2025-01-16T12:00:00Z"
}
```

### Option 2: Flag in Webhook Payload
```json
{
    "event": "profile.completed",
    "completion_method": "manual", // or "chat"
    "timestamp": "2025-01-16T12:00:00Z"
}
```

### Option 3: Dashboard Action Button
Add an explicit "Send to CRM" button that agents click after manual completion.

## Recommended Approach

**For Now**: Keep current behavior (no webhook on manual update) because:
- Simpler implementation
- Avoids redundant notifications
- Agents can manually trigger next steps if needed

**Future Enhancement**: If needed, implement Option 2 (flag in payload) so Make/Zapier can decide whether to process manual completions differently.

## Testing Considerations

If implementing webhook for manual updates:

1. **Test Scenarios:**
   - Add single missing field → Webhook fires once
   - Delete field then re-add → Webhook fires only on re-completion
   - Edit existing complete profile → No webhook
   - Create new profile manually with all fields → Webhook fires

2. **Edge Cases:**
   - Rapid edits (debouncing needed?)
   - Partial saves
   - Network failures during webhook

## Conclusion

The current behavior is intentional but may not meet all business needs. The decision to add webhooks for manual completions depends on whether your workflow requires external systems to be notified of ALL completions or just organic ones through chat.

**Current State**: Webhooks fire only for chat-based completions
**Proposed State**: Configurable to fire for all completions with method indicator

---

*Document created: January 16, 2025*
*System Version: WhatsApp OpenAI Chatbot v1.0*