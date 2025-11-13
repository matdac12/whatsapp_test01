#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orders Database Manager
Manages order data in a separate database for testing tool functionality
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

class OrdersDatabase:
    def __init__(self, db_path: str = "orders.db"):
        """
        Initialize the orders database manager

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        self._create_tables()
        self._insert_sample_data()
        logger.debug(f"Orders database initialized at {db_path}")

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
        """Create orders table if it doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('processing', 'shipped', 'delivered')),
                    expected_delivery_date DATE NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on phone_number for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_phone
                ON orders(phone_number)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status
                ON orders(status)
            """)

            conn.commit()

    def _insert_sample_data(self):
        """Insert sample orders for testing if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if data already exists
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            if cursor.fetchone()['count'] > 0:
                logger.debug("Sample data already exists, skipping insertion")
                return

            # Phone number from user
            phone = "+393404570180"

            # Calculate dates
            today = datetime.now()
            delivered_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
            shipped_date = (today + timedelta(days=2)).strftime('%Y-%m-%d')
            processing_date = (today + timedelta(days=5)).strftime('%Y-%m-%d')

            # Sample orders
            sample_orders = [
                {
                    'order_id': 'ORD-2025-001',
                    'phone_number': phone,
                    'status': 'delivered',
                    'expected_delivery_date': delivered_date,
                    'product_name': 'Tastiera Meccanica RGB',
                    'quantity': 1,
                    'total_amount': 89.99,
                    'created_at': (today - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
                },
                {
                    'order_id': 'ORD-2025-002',
                    'phone_number': phone,
                    'status': 'shipped',
                    'expected_delivery_date': shipped_date,
                    'product_name': 'Mouse Wireless Logitech',
                    'quantity': 2,
                    'total_amount': 45.50,
                    'created_at': (today - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S')
                },
                {
                    'order_id': 'ORD-2025-003',
                    'phone_number': phone,
                    'status': 'processing',
                    'expected_delivery_date': processing_date,
                    'product_name': 'Laptop Dell XPS 15',
                    'quantity': 1,
                    'total_amount': 1499.00,
                    'created_at': today.strftime('%Y-%m-%d %H:%M:%S')
                }
            ]

            # Insert sample orders
            for order in sample_orders:
                cursor.execute("""
                    INSERT INTO orders
                    (order_id, phone_number, status, expected_delivery_date,
                     product_name, quantity, total_amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order['order_id'],
                    order['phone_number'],
                    order['status'],
                    order['expected_delivery_date'],
                    order['product_name'],
                    order['quantity'],
                    order['total_amount'],
                    order['created_at']
                ))

            conn.commit()
            logger.info(f"✅ Inserted {len(sample_orders)} sample orders for {phone}")

    # === Query Methods ===

    def get_user_orders(self, phone_number: str) -> List[Dict]:
        """Get all orders for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id, status, expected_delivery_date,
                       product_name, quantity, total_amount, created_at
                FROM orders
                WHERE phone_number = ?
                ORDER BY created_at DESC
            """, (phone_number,))

            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'order_id': row['order_id'],
                    'status': row['status'],
                    'expected_delivery_date': row['expected_delivery_date'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'total_amount': row['total_amount'],
                    'created_at': row['created_at']
                })

            return orders

    def get_latest_order(self, phone_number: str) -> Optional[Dict]:
        """Get the most recent order for a phone number"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id, status, expected_delivery_date,
                       product_name, quantity, total_amount, created_at
                FROM orders
                WHERE phone_number = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (phone_number,))

            row = cursor.fetchone()
            if row:
                return {
                    'order_id': row['order_id'],
                    'status': row['status'],
                    'expected_delivery_date': row['expected_delivery_date'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'total_amount': row['total_amount'],
                    'created_at': row['created_at']
                }
            return None

    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """Get a specific order by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id, phone_number, status, expected_delivery_date,
                       product_name, quantity, total_amount, created_at
                FROM orders
                WHERE order_id = ?
            """, (order_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'order_id': row['order_id'],
                    'phone_number': row['phone_number'],
                    'status': row['status'],
                    'expected_delivery_date': row['expected_delivery_date'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'total_amount': row['total_amount'],
                    'created_at': row['created_at']
                }
            return None

    def search_orders_by_status(self, phone_number: str, status: str) -> List[Dict]:
        """Get all orders for a phone number filtered by status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id, status, expected_delivery_date,
                       product_name, quantity, total_amount, created_at
                FROM orders
                WHERE phone_number = ? AND status = ?
                ORDER BY created_at DESC
            """, (phone_number, status))

            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'order_id': row['order_id'],
                    'status': row['status'],
                    'expected_delivery_date': row['expected_delivery_date'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'total_amount': row['total_amount'],
                    'created_at': row['created_at']
                })

            return orders

# Create a singleton instance
orders_db = OrdersDatabase()
