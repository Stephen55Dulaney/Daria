#!/usr/bin/env python3
"""
Debug tool for LangChain conversation history in the DARIA Interview Tool
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
import requests
from tabulate import tabulate
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Debug LangChain conversation history')
    parser.add_argument('--session-id', '-s', type=str, help='Session ID to debug')
    parser.add_argument('--port', '-p', type=int, default=5050, help='API port (default: 5050)')
    parser.add_argument('--file', '-f', type=str, help='Load conversation from a JSON file instead of API')
    parser.add_argument('--output', '-o', type=str, help='Save conversation to a JSON file')
    parser.add_argument('--format', type=str, choices=['table', 'json', 'raw'], default='table', 
                       help='Output format (default: table)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    return parser.parse_args()

def load_session_from_api(session_id, port=5050):
    """Load conversation from the API"""
    try:
        url = f"http://localhost:{port}/api/session/{session_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('session')
            else:
                print(f"{Fore.RED}Error: {data.get('error', 'Unknown error')}{Style.RESET_ALL}")
                return None
        else:
            print(f"{Fore.RED}Error: API returned status code {response.status_code}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}Error connecting to API: {str(e)}{Style.RESET_ALL}")
        return None

def load_session_from_file(filepath):
    """Load conversation from a JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Check if it's a raw session or wrapped in a response
            if 'session' in data:
                return data.get('session')
            return data
    except Exception as e:
        print(f"{Fore.RED}Error loading file: {str(e)}{Style.RESET_ALL}")
        return None

def save_session_to_file(session, filepath):
    """Save conversation to a JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(session, f, indent=2)
        print(f"{Fore.GREEN}Session saved to {filepath}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error saving file: {str(e)}{Style.RESET_ALL}")

def print_session_info(session):
    """Print basic session information"""
    if not session:
        print(f"{Fore.RED}No session data available{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}======= Session Information ======={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Session ID:{Style.RESET_ALL} {session.get('id', 'N/A')}")
    print(f"{Fore.YELLOW}Guide ID:{Style.RESET_ALL} {session.get('guide_id', 'N/A')}")
    print(f"{Fore.YELLOW}Status:{Style.RESET_ALL} {session.get('status', 'N/A')}")
    print(f"{Fore.YELLOW}Created:{Style.RESET_ALL} {session.get('created_at', 'N/A')}")
    print(f"{Fore.YELLOW}Updated:{Style.RESET_ALL} {session.get('updated_at', 'N/A')}")
    
    # Print interviewee info if available
    interviewee = session.get('interviewee', {})
    if interviewee:
        print(f"{Fore.YELLOW}Interviewee:{Style.RESET_ALL} {interviewee.get('name', 'Unknown')}")
    
    # Message count
    messages = session.get('messages', [])
    print(f"{Fore.YELLOW}Message Count:{Style.RESET_ALL} {len(messages)}")
    
    # Count by role
    roles = {}
    for msg in messages:
        role = msg.get('role', 'unknown')
        roles[role] = roles.get(role, 0) + 1
    
    for role, count in roles.items():
        print(f"  - {role}: {count}")

def format_message_content(content, max_length=80):
    """Format message content to a reasonable length"""
    if not content:
        return ""
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content

def print_conversation_table(session):
    """Print conversation as a table"""
    if not session:
        return
    
    messages = session.get('messages', [])
    if not messages:
        print(f"{Fore.YELLOW}No messages in this session{Style.RESET_ALL}")
        return
    
    table_data = []
    for i, msg in enumerate(messages):
        # Format timestamp
        timestamp = msg.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                timestamp = dt.strftime('%H:%M:%S')
            except:
                pass
        
        # Format role with color
        role = msg.get('role', 'unknown')
        if role == 'assistant':
            role = f"{Fore.BLUE}assistant{Style.RESET_ALL}"
        elif role == 'user':
            role = f"{Fore.GREEN}user{Style.RESET_ALL}"
        elif role == 'system':
            role = f"{Fore.MAGENTA}system{Style.RESET_ALL}"
        
        # Add row to table
        table_data.append([
            i + 1,
            role,
            format_message_content(msg.get('content', '')),
            timestamp,
            msg.get('id', '')[:8] if msg.get('id') else ''
        ])
    
    headers = ["#", "Role", "Content", "Time", "ID"]
    print(f"\n{Fore.CYAN}======= Conversation History ======={Style.RESET_ALL}")
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))

def print_conversation_json(session):
    """Print conversation as formatted JSON"""
    if not session:
        return
    
    messages = session.get('messages', [])
    if not messages:
        print(f"{Fore.YELLOW}No messages in this session{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}======= Conversation JSON ======={Style.RESET_ALL}")
    print(json.dumps(messages, indent=2))

def print_conversation_raw(session):
    """Print raw conversation data"""
    if not session:
        return
    
    print(f"\n{Fore.CYAN}======= Raw Conversation Data ======={Style.RESET_ALL}")
    print(json.dumps(session, indent=2))

def debug_conversation():
    """Main function to debug conversation history"""
    args = parse_arguments()
    
    # Load session data
    session = None
    if args.file:
        print(f"{Fore.YELLOW}Loading session from file: {args.file}{Style.RESET_ALL}")
        session = load_session_from_file(args.file)
    elif args.session_id:
        print(f"{Fore.YELLOW}Loading session from API: {args.session_id}{Style.RESET_ALL}")
        session = load_session_from_api(args.session_id, args.port)
    else:
        # Try to load from debug session file
        if os.path.exists('.debug_session_id'):
            with open('.debug_session_id', 'r') as f:
                session_id = f.read().strip()
                if session_id:
                    print(f"{Fore.YELLOW}Loading debug session from API: {session_id}{Style.RESET_ALL}")
                    session = load_session_from_api(session_id, args.port)
        
        if not session:
            print(f"{Fore.RED}Error: No session ID provided. Use --session-id or --file{Style.RESET_ALL}")
            sys.exit(1)
    
    # Output the conversation
    print_session_info(session)
    
    if args.format == 'table':
        print_conversation_table(session)
    elif args.format == 'json':
        print_conversation_json(session)
    elif args.format == 'raw':
        print_conversation_raw(session)
    
    # Save to file if requested
    if args.output and session:
        save_session_to_file(session, args.output)

if __name__ == "__main__":
    debug_conversation() 