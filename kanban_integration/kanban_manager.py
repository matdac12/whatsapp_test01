#!/usr/bin/env python3
"""
Kanban Manager - Direct Database Interface
Full control of your Kanban system via SQLite database
"""

import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

class KanbanDirectTester:
    def __init__(self):
        self.db_path = "/mnt/c/Users/MattiaDaCampo/OneDrive - Be Digital Consulting Srl/Kanban_Project/kanbanlite/app.db"
    
    def get_connection(self):
        """Get database connection"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)
    
    def list_tables(self):
        """List all tables in the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            return [table[0] for table in tables]
    
    def describe_table(self, table_name):
        """Show table structure"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            return columns
    
    def list_boards(self):
        """List all boards"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM boards;")
            return cursor.fetchall()
    
    def list_columns(self):
        """List all columns"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM columns;")
            return cursor.fetchall()
    
    def list_cards(self, limit=10):
        """List recent cards"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM cards ORDER BY id DESC LIMIT {limit};")
            return cursor.fetchall()
    
    def create_test_card(self, title="Test Card via Direct DB"):
        """Create a test card"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the first column (Todo)
            cursor.execute("SELECT id FROM columns ORDER BY position LIMIT 1;")
            column_result = cursor.fetchone()
            if not column_result:
                print("❌ No columns found! Creating basic structure...")
                return self.setup_basic_structure()
            
            column_id = column_result[0]
            
            # Get the next position in this column
            cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM cards WHERE column_id = ?;", (column_id,))
            position = cursor.fetchone()[0]
            
            # Insert the card
            cursor.execute("""
                INSERT INTO cards (column_id, title, notes, position)
                VALUES (?, ?, ?, ?)
            """, (column_id, title, "Created by direct DB test", position))
            
            card_id = cursor.lastrowid
            conn.commit()
            return card_id
    
    def setup_basic_structure(self):
        """Setup basic board and columns if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create board if it doesn't exist
            cursor.execute("SELECT id FROM board WHERE name='My Board';")
            board = cursor.fetchone()
            if not board:
                cursor.execute("INSERT INTO board (name) VALUES ('My Board');")
                board_id = cursor.lastrowid
            else:
                board_id = board[0]
            
            # Create columns if they don't exist
            columns = [("Todo", 0), ("Doing", 1), ("Done", 2)]
            for name, position in columns:
                cursor.execute("SELECT id FROM column_model WHERE name=? AND board_id=?;", (name, board_id))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO column_model (name, position, board_id)
                        VALUES (?, ?, ?)
                    """, (name, position, board_id))
            
            conn.commit()
            return "✅ Basic structure created"
    
    def run_full_test(self):
        """Run comprehensive test of Kanban database"""
        print("🚀 Starting Direct Kanban Database Test")
        print("=" * 60)
        
        try:
            # Test 1: Database connectivity
            print("🔍 Testing database connectivity...")
            tables = self.list_tables()
            print(f"✅ Connected! Found {len(tables)} tables: {', '.join(tables)}")
            
            # Test 2: Show table structures
            print(f"\n📋 Table Structures:")
            for table in ['boards', 'columns', 'cards', 'checklist_items']:
                if table in tables:
                    columns = self.describe_table(table)
                    print(f"  {table}: {[col[1] for col in columns]}")
            
            # Test 3: Show current data
            print(f"\n📊 Current Data:")
            
            boards = self.list_boards()
            print(f"  Boards ({len(boards)}): {boards}")
            
            columns = self.list_columns()
            print(f"  Columns ({len(columns)}): {columns}")
            
            cards = self.list_cards()
            print(f"  Recent Cards ({len(cards)}):")
            for card in cards[:5]:  # Show first 5
                print(f"    ID {card[0]}: {card[2]} (Column: {card[1]})")
            
            # Test 4: Create a test card
            print(f"\n🧪 Testing Card Creation...")
            card_id = self.create_test_card("Direct DB Test Card")
            if isinstance(card_id, int):
                print(f"✅ Created test card with ID: {card_id}")
            else:
                print(f"ℹ️  {card_id}")
            
            print(f"\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

def main():
    """Main test runner"""
    tester = KanbanDirectTester()
    tester.run_full_test()

if __name__ == "__main__":
    main()