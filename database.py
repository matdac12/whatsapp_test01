#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Database Manager for WhatsApp Bot
Handles all database operations for conversations, profiles, and messages
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "whatsapp_bot.db"):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        self._create_tables()
        logger.info(f"Database initialized at {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get a thread-local database connection"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        try:
            yield self.local.conn
        except Exception as e:
            self.local.conn.rollback()
            raise e
        else:
            self.local.conn.commit()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    phone_number TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Client profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_profiles (
                    phone_number TEXT PRIMARY KEY,
                    name TEXT,
                    last_name TEXT,
                    ragione_sociale TEXT,
                    email TEXT,
                    found_all_info BOOLEAN DEFAULT 0,
                    conversation_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    hubspot_synced BOOLEAN DEFAULT 0,
                    hubspot_contact_id TEXT
                )
            """)

            # Idempotent migration: add manual mode and draft/notes columns
            # Each ALTER is wrapped to avoid failure if column already exists
            try:
                cursor.execute("ALTER TABLE client_profiles ADD COLUMN manual_mode BOOLEAN DEFAULT 0")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE client_profiles ADD COLUMN ai_draft TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE client_profiles ADD COLUMN ai_draft_created_at TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE client_profiles ADD COLUMN notes TEXT")
            except Exception:
                pass
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    sender TEXT NOT NULL CHECK(sender IN ('user', 'bot')),
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Processed messages table for deduplication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_phone 
                ON messages(phone_number)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            
            # Index for cleanup of old processed messages
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_messages_timestamp 
                ON processed_messages(processed_at)
            """)
            
            conn.commit()
    
    # === Conversation Methods ===
    
    def get_conversation(self, phone_number: str) -> Optional[str]:
        """Get conversation ID for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT conversation_id FROM conversations WHERE phone_number = ?",
                (phone_number,)
            )
            row = cursor.fetchone()
            return row['conversation_id'] if row else None
    
    def save_conversation(self, phone_number: str, conversation_id: str):
        """Save or update a conversation ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations 
                (phone_number, conversation_id, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(phone_number) DO UPDATE SET
                    conversation_id = excluded.conversation_id,
                    updated_at = CURRENT_TIMESTAMP
                    -- created_at is NOT updated, preserves original
            """, (phone_number, conversation_id))
    
    def get_all_conversations(self) -> Dict[str, str]:
        """Get all conversations as a dictionary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number, conversation_id FROM conversations")
            return {row['phone_number']: row['conversation_id'] for row in cursor.fetchall()}
    
    def delete_conversation(self, phone_number: str):
        """Delete a conversation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE phone_number = ?", (phone_number,))
    
    # === Profile Methods ===
    
    def get_profile(self, phone_number: str) -> Optional[Dict]:
        """Get a client profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM client_profiles WHERE phone_number = ?",
                (phone_number,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def save_profile(self, phone_number: str, profile_data: Dict):
        """Save or update a client profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if all required fields are present
            found_all_info = all([
                profile_data.get('name'),
                profile_data.get('last_name'),
                profile_data.get('ragione_sociale'),
                profile_data.get('email')
            ])
            
            # Set completed_at if all info is found
            completed_at = datetime.now() if found_all_info else None
            
            cursor.execute("""
                INSERT INTO client_profiles 
                (phone_number, name, last_name, ragione_sociale, email, 
                 found_all_info, conversation_id, created_at, updated_at, completed_at,
                 hubspot_synced, hubspot_contact_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    name = COALESCE(excluded.name, name),
                    last_name = COALESCE(excluded.last_name, last_name),
                    ragione_sociale = COALESCE(excluded.ragione_sociale, ragione_sociale),
                    email = COALESCE(excluded.email, email),
                    found_all_info = excluded.found_all_info,
                    conversation_id = COALESCE(excluded.conversation_id, conversation_id),
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CASE 
                        WHEN excluded.found_all_info = 1 AND completed_at IS NULL 
                        THEN excluded.completed_at 
                        ELSE completed_at 
                    END,
                    hubspot_synced = excluded.hubspot_synced,
                    hubspot_contact_id = excluded.hubspot_contact_id
                    -- created_at is preserved
            """, (
                phone_number,
                profile_data.get('name'),
                profile_data.get('last_name'),
                profile_data.get('ragione_sociale'),
                profile_data.get('email'),
                found_all_info,
                profile_data.get('conversation_id'),
                completed_at,
                profile_data.get('hubspot_synced', False),
                profile_data.get('hubspot_contact_id')
            ))
    
    def get_all_profiles(self) -> Dict[str, Dict]:
        """Get all client profiles"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM client_profiles")
            profiles = {}
            for row in cursor.fetchall():
                profiles[row['phone_number']] = dict(row)
            return profiles
    
    def update_profile_manually(self, phone_number: str, updates: Dict) -> bool:
        """Update specific fields in a profile"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                fields = []
                values = []
                for field in ['name', 'last_name', 'ragione_sociale', 'email']:
                    if field in updates:
                        fields.append(f"{field} = ?")
                        values.append(updates[field] if updates[field] else None)

                # Optional: allow notes update through this method when provided
                if 'notes' in updates:
                    fields.append("notes = ?")
                    values.append(updates['notes'] if updates['notes'] else None)
                
                if not fields:
                    return True  # Nothing to update
                
                # Add updated_at
                fields.append("updated_at = CURRENT_TIMESTAMP")
                
                # Check if profile should be marked as complete
                cursor.execute(
                    "SELECT name, last_name, ragione_sociale, email FROM client_profiles WHERE phone_number = ?",
                    (phone_number,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Merge existing and new data
                    merged = dict(existing)
                    merged.update(updates)
                    
                    # Check if all fields are now present
                    found_all_info = all([
                        merged.get('name'),
                        merged.get('last_name'),
                        merged.get('ragione_sociale'),
                        merged.get('email')
                    ])
                    
                    fields.append("found_all_info = ?")
                    values.append(found_all_info)
                    
                    if found_all_info:
                        fields.append("completed_at = CURRENT_TIMESTAMP")
                
                # Execute update
                values.append(phone_number)
                query = f"UPDATE client_profiles SET {', '.join(fields)} WHERE phone_number = ?"
                cursor.execute(query, values)
                
                return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False

    # === Settings & Draft Helpers ===

    def get_settings(self, phone_number: str) -> Dict[str, Any]:
        """Get per-contact settings like manual_mode"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT manual_mode FROM client_profiles WHERE phone_number = ?",
                (phone_number,),
            )
            row = cursor.fetchone()
            if row is None:
                # Ensure profile exists with default settings
                self.save_profile(phone_number, {})
                return {"manual_mode": False}
            return {"manual_mode": bool(row["manual_mode"]) if row["manual_mode"] is not None else False}

    def set_manual_mode(self, phone_number: str, enabled: bool) -> None:
        """Enable/disable manual mode for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO client_profiles (phone_number, manual_mode, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(phone_number) DO UPDATE SET
                    manual_mode = excluded.manual_mode,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (phone_number, 1 if enabled else 0),
            )

    def save_ai_draft(self, phone_number: str, text: str) -> None:
        """Save AI draft and timestamp for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE client_profiles
                SET ai_draft = ?, ai_draft_created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = ?
                """,
                (text, phone_number),
            )

    def get_ai_draft(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get AI draft text and created timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ai_draft, ai_draft_created_at FROM client_profiles WHERE phone_number = ?",
                (phone_number,),
            )
            row = cursor.fetchone()
            if row and row["ai_draft"]:
                return {"text": row["ai_draft"], "created_at": row["ai_draft_created_at"]}
            return None

    def clear_ai_draft(self, phone_number: str) -> None:
        """Clear AI draft for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE client_profiles
                SET ai_draft = NULL, ai_draft_created_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = ?
                """,
                (phone_number,),
            )

    def get_notes(self, phone_number: str) -> Optional[str]:
        """Get notes for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT notes FROM client_profiles WHERE phone_number = ?",
                (phone_number,),
            )
            row = cursor.fetchone()
            return row["notes"] if row and row["notes"] else None

    def set_notes(self, phone_number: str, text: Optional[str]) -> None:
        """Set notes for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO client_profiles (phone_number, notes, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(phone_number) DO UPDATE SET
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (phone_number, text if text else None),
            )

    def get_last_user_message(self, phone_number: str) -> Optional[str]:
        """Return the last user message text for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT message FROM messages
                WHERE phone_number = ? AND sender = 'user'
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (phone_number,),
            )
            row = cursor.fetchone()
            return row["message"] if row else None
    
    # === Message Methods ===
    
    # === Message Deduplication Methods ===
    
    def is_message_processed(self, message_id: str) -> bool:
        """Check if a WhatsApp message ID has already been processed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?",
                (message_id,)
            )
            return cursor.fetchone() is not None
    
    def mark_message_processed(self, message_id: str, phone_number: str):
        """Mark a WhatsApp message as processed to prevent duplicates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_messages (message_id, phone_number)
                VALUES (?, ?)
            """, (message_id, phone_number))
    
    def cleanup_old_processed_messages(self, days_to_keep: int = 7) -> int:
        """Delete processed message records older than specified days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM processed_messages 
                WHERE processed_at < datetime('now', '-' || ? || ' days')
            """, (days_to_keep,))
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old processed message records")
            return deleted_count
    
    def add_message(self, phone_number: str, sender: str, message: str, timestamp: Optional[str] = None):
        """Add a message to history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if timestamp:
                cursor.execute("""
                    INSERT INTO messages (phone_number, sender, message, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (phone_number, sender, message, timestamp))
            else:
                cursor.execute("""
                    INSERT INTO messages (phone_number, sender, message)
                    VALUES (?, ?, ?)
                """, (phone_number, sender, message))
    
    def get_messages(self, phone_number: str, limit: Optional[int] = None) -> List[Dict]:
        """Get messages for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if limit:
                cursor.execute("""
                    SELECT sender, message, timestamp 
                    FROM messages 
                    WHERE phone_number = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (phone_number, limit))
            else:
                cursor.execute("""
                    SELECT sender, message, timestamp 
                    FROM messages 
                    WHERE phone_number = ? 
                    ORDER BY timestamp
                """, (phone_number,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'sender': row['sender'],
                    'message': row['message'],
                    'timestamp': row['timestamp']
                })
            
            # If we used limit, reverse to get chronological order
            if limit:
                messages.reverse()
            
            return messages
    
    def get_all_conversations_with_info(self) -> Dict[str, Dict]:
        """Get all conversations with profile info and last message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all unique phone numbers from messages and profiles
            cursor.execute("""
                SELECT DISTINCT phone_number FROM (
                    SELECT phone_number FROM messages
                    UNION
                    SELECT phone_number FROM client_profiles
                )
            """)
            
            conversations = {}
            for row in cursor.fetchall():
                phone = row['phone_number']
                
                # Get profile info
                cursor.execute(
                    "SELECT name, last_name, ragione_sociale, email FROM client_profiles WHERE phone_number = ?",
                    (phone,)
                )
                profile = cursor.fetchone()
                
                # Get last message
                cursor.execute("""
                    SELECT message, timestamp 
                    FROM messages 
                    WHERE phone_number = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (phone,))
                last_msg = cursor.fetchone()
                
                # Build a clean display name without 'None' artifacts
                display_name = None
                if profile:
                    first = profile['name'] if profile['name'] else None
                    last = profile['last_name'] if profile['last_name'] else None
                    if first or last:
                        display_name = " ".join([p for p in [first, last] if p])

                conversations[phone] = {
                    'name': display_name,
                    'email': profile['email'] if profile else None,
                    'company': profile['ragione_sociale'] if profile else None,
                    'last_message': last_msg['message'] if last_msg else '',
                    'last_timestamp': last_msg['timestamp'] if last_msg else None
                }
            
            return conversations
    
    def clear_messages(self, phone_number: str):
        """Clear all messages for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE phone_number = ?", (phone_number,))
    
    # === Utility Methods ===
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count conversations
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            stats['total_conversations'] = cursor.fetchone()['count']
            
            # Count profiles
            cursor.execute("SELECT COUNT(*) as count FROM client_profiles")
            stats['total_profiles'] = cursor.fetchone()['count']
            
            # Count complete profiles
            cursor.execute("SELECT COUNT(*) as count FROM client_profiles WHERE found_all_info = 1")
            stats['complete_profiles'] = cursor.fetchone()['count']
            
            # Count messages
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            stats['total_messages'] = cursor.fetchone()['count']
            
            return stats

# Create a singleton instance
db = DatabaseManager()
