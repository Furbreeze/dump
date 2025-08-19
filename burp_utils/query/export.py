#!/usr/bin/env python3
"""
Script to convert XML export file to JSON and load into SQLite database.

Usage:
    python export.py <xml_file_path> <database_path>
    
Example:
    python export.py ~/exports/burp_export.xml ~/data/requests.db
"""

import xml.etree.ElementTree as ET
import base64
import json
import sqlite3
import sys
import os
from typing import Dict, Any, List


# ==============================
# XML to JSON Conversion Functions
# ==============================

def parse_http_request_response(base64_encoded_data):
    """
    Parses a base64-encoded raw HTTP request or response and returns a JSON object
    containing the headers and the re-encoded body/content.

    Args:
        base64_encoded_data: The base64-encoded HTTP request or response string.

    Returns:
        A tuple containing a JSON string of headers and the re-encoded body/content,
        or (None, None) if an error occurs.
    """
    try:
        decoded_data = base64.b64decode(base64_encoded_data).decode('utf-8')
        lines = decoded_data.splitlines()
        headers = {}
        body_content = ""
        header_parsing_complete = False

        for line in lines[1:]:  # Skip the first line (request/status line)
            if not line.strip():  # Empty line signals end of headers
                header_parsing_complete = True
                continue

            if not header_parsing_complete:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key] = value
            else:
                body_content += line + "\n"

        if body_content:
            body_content = base64.b64encode(body_content.rstrip('\n').encode('utf-8')).decode('utf-8')

        return headers, body_content

    except (base64.binascii.Error, UnicodeDecodeError, ValueError) as e:
        return None, None # or return f"Error: {e}" for more verbose error reporting.


def xml_to_json_data(xml_file_path):
    """
    Converts an XML file to a JSON data structure.

    Args:
        xml_file_path: The path to the XML file.

    Returns:
        A dictionary representing the XML data, or raises an exception on error.
    """
    if not os.path.exists(xml_file_path):
        raise FileNotFoundError(f"XML file not found: {xml_file_path}")

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        items = []

        for item_element in root.findall('item'):
            item = {}
            for child in item_element:
                text = child.text if child.text is not None else ""
                if child.tag == 'request':
                    headers, body = parse_http_request_response(text)
                    item[child.tag] = {'value': body, 'base64': child.get('base64', 'false')}
                    item['request_headers'] = headers if headers else {}
                elif child.tag == 'response':
                    headers, content = parse_http_request_response(text)
                    item[child.tag] = {'value': content, 'base64': child.get('base64', 'false')}
                    item['response_headers'] = headers if headers else {}
                elif child.tag == 'host':
                    item[child.tag] = {'value': text, 'ip': child.get('ip', '')}
                else:
                    item[child.tag] = text

            items.append(item)

        result = {
            'items': items,
            'burpVersion': root.get('burpVersion', ''),
            'exportTime': root.get('exportTime', '')
        }

        return result

    except ET.ParseError as e:
        raise ValueError(f"Error parsing XML: {e}")
    except Exception as e:
        raise Exception(f"An error occurred during XML parsing: {e}")


# ==============================
# Database Functions
# ==============================

def create_database(db_path: str) -> None:
    """Create a new database file at the specified path."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        print(f"Creating database directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    # Create the database file by connecting to it (SQLite creates it if it doesn't exist)
    print(f"Creating/connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.close()
    print(f"✓ Database created/verified at: {db_path}")


def create_tables_if_not_exist(cursor: sqlite3.Cursor) -> None:
    """Create tables and indexes if they don't already exist."""
    
    print("Creating tables if they don't exist...")
    
    # Create requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            url TEXT NOT NULL,
            host_value TEXT,
            host_ip TEXT,
            port TEXT,
            protocol TEXT,
            method TEXT,
            path TEXT,
            extension TEXT,
            request_value TEXT,
            request_base64 BOOLEAN,
            status TEXT,
            response_length INTEGER,
            mime_type TEXT,
            response_value TEXT,
            response_base64 BOOLEAN,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ requests table created/verified")
    
    # Create request_headers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS request_headers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            header_name TEXT NOT NULL,
            header_value TEXT,
            FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
        )
    """)
    print("✓ request_headers table created/verified")
    
    # Create response_headers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS response_headers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            header_name TEXT NOT NULL,
            header_value TEXT,
            FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
        )
    """)
    print("✓ response_headers table created/verified")
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_requests_time ON requests(time)",
        "CREATE INDEX IF NOT EXISTS idx_requests_url ON requests(url)",
        "CREATE INDEX IF NOT EXISTS idx_requests_host ON requests(host_value)",
        "CREATE INDEX IF NOT EXISTS idx_requests_method ON requests(method)",
        "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_request_headers_request_id ON request_headers(request_id)",
        "CREATE INDEX IF NOT EXISTS idx_request_headers_name ON request_headers(header_name)",
        "CREATE INDEX IF NOT EXISTS idx_response_headers_request_id ON response_headers(request_id)",
        "CREATE INDEX IF NOT EXISTS idx_response_headers_name ON response_headers(header_name)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    print("✓ Indexes created/verified")


def insert_request(cursor: sqlite3.Cursor, item: Dict[str, Any]) -> int:
    """Insert a request record and return the request_id."""
    
    # Extract host information
    host_info = item.get('host', {})
    host_value = host_info.get('value') if isinstance(host_info, dict) else None
    host_ip = host_info.get('ip') if isinstance(host_info, dict) else None
    
    # Extract request information
    request_info = item.get('request', {})
    request_value = request_info.get('value') if isinstance(request_info, dict) else None
    request_base64 = request_info.get('base64') == 'true' if isinstance(request_info, dict) else False
    
    # Extract response information
    response_info = item.get('response', {})
    response_value = response_info.get('value') if isinstance(response_info, dict) else None
    response_base64 = response_info.get('base64') == 'true' if isinstance(response_info, dict) else False
    
    print(f"Inserting request: {item.get('method')} {item.get('url')}")
    
    # Insert main request record
    cursor.execute("""
        INSERT INTO requests (
            time, url, host_value, host_ip, port, protocol, method, path, extension,
            request_value, request_base64, status, response_length, mime_type,
            response_value, response_base64, comment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.get('time'),
        item.get('url'),
        host_value,
        host_ip,
        item.get('port'),
        item.get('protocol'),
        item.get('method'),
        item.get('path'),
        item.get('extension'),
        request_value,
        request_base64,
        item.get('status'),
        item.get('responselength'),
        item.get('mimetype'),
        response_value,
        response_base64,
        item.get('comment')
    ))
    
    return cursor.lastrowid


def insert_headers(cursor: sqlite3.Cursor, request_id: int, headers: Dict[str, str], table_name: str) -> None:
    """Insert headers into the specified header table."""
    if not headers or not isinstance(headers, dict):
        return
        
    print(f"Inserting {len(headers)} headers into {table_name}")
    for header_name, header_value in headers.items():
        cursor.execute(f"""
            INSERT INTO {table_name} (request_id, header_name, header_value)
            VALUES (?, ?, ?)
        """, (request_id, header_name, header_value))


def load_data_to_database(data: Dict[str, Any], db_path: str) -> None:
    """Load JSON data structure into SQLite database."""
    
    # Expand tilde in path
    db_path = os.path.expanduser(db_path)
    
    print(f"Database path: {db_path}")
    
    # Create database first
    create_database(db_path)
    
    # Connect to database
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create tables if they don't exist
        create_tables_if_not_exist(cursor)
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        # Handle both single item and array of items
        items = data.get('items', []) if 'items' in data else [data]
        print(f"Processing {len(items)} item(s)")
        
        inserted_count = 0
        
        # Process each item
        for item in items:
            if not isinstance(item, dict):
                print(f"Warning: Skipping invalid item: {item}")
                continue
                
            # Insert main request record
            request_id = insert_request(cursor, item)
            print(f"✓ Inserted request with ID: {request_id}")
            
            # Insert request headers
            request_headers = item.get('request_headers', {})
            insert_headers(cursor, request_id, request_headers, 'request_headers')
            
            # Insert response headers
            response_headers = item.get('response_headers', {})
            insert_headers(cursor, request_id, response_headers, 'response_headers')
            
            inserted_count += 1
        
        # Commit the transaction
        conn.commit()
        print(f"✓ Successfully loaded {inserted_count} request(s) into {db_path}")
        
        # Verify data was inserted
        cursor.execute("SELECT COUNT(*) FROM requests")
        count = cursor.fetchone()[0]
        print(f"Total requests in database: {count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error occurred, rolling back transaction: {e}")
        raise e
    finally:
        conn.close()


# ==============================
# Main Function
# ==============================

def export_xml_to_database(xml_file_path: str, db_path: str) -> None:
    """Main function to convert XML to JSON and load into database."""
    
    # Expand tilde in paths
    xml_file_path = os.path.expanduser(xml_file_path)
    db_path = os.path.expanduser(db_path)
    
    print(f"Converting XML file: {xml_file_path}")
    print(f"Target database: {db_path}")
    print("=" * 50)
    
    # Step 1: Convert XML to JSON data structure
    print("Step 1: Converting XML to JSON data structure...")
    try:
        json_data = xml_to_json_data(xml_file_path)
        print(f"✓ Successfully parsed XML file with {len(json_data.get('items', []))} items")
    except Exception as e:
        raise Exception(f"Failed to convert XML to JSON: {e}")
    
    # Step 2: Load JSON data into database
    print("\nStep 2: Loading data into database...")
    try:
        load_data_to_database(json_data, db_path)
        print("✓ Successfully completed XML to database export")
    except Exception as e:
        raise Exception(f"Failed to load data into database: {e}")


def main():
    """Main function to handle command line arguments and execute the export."""
    if len(sys.argv) != 3:
        print("Usage: python export.py <xml_file_path> <database_path>")
        print("Example: python export.py ~/exports/burp_export.xml ~/data/requests.db")
        sys.exit(1)
    
    xml_file_path = sys.argv[1]
    db_path = sys.argv[2]
    
    try:
        export_xml_to_database(xml_file_path, db_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
