#!/usr/bin/env python3
"""
Inspect Redis mailbox stream content
Shows all messages in a readable format
"""
import redis
import json
import sys

def inspect_mailbox(session_id):
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    mailbox_key = f"mailbox:{session_id}"
    
    # Get stream length
    length = r.xlen(mailbox_key)
    print(f"\n📊 Mailbox Statistics:")
    print(f"   Session ID: {session_id}")
    print(f"   Total Messages: {length}")
    print(f"   {'='*60}\n")
    
    # Get all stream entries
    messages = r.xrange(mailbox_key, count=length)
    
    for idx, (message_id, data) in enumerate(messages, 1):
        try:
            msg = data.get('msg', '{}')
            parsed = json.loads(msg)
            msg_type = parsed.get('type', 'unknown')
            
            print(f"[{idx:3d}] {message_id}")
            print(f"      Type: {msg_type}")
            
            # Show relevant content based on type
            if msg_type == 'audio':
                audio_len = len(parsed.get('data', ''))
                print(f"      Data: {audio_len} bytes of audio")
            elif msg_type == 'transcript':
                transcript = parsed.get('data', '')
                print(f"      📝 Transcript: {transcript[:80]}{'...' if len(transcript) > 80 else ''}")
            elif msg_type == 'token':
                token = parsed.get('data', '')
                print(f"      🤖 LLM Token: {token}")
            elif msg_type == 'audio_chunk':
                chunk_len = len(parsed.get('data', ''))
                print(f"      Data: {chunk_len} bytes of audio chunk")
            elif msg_type == 'stop':
                print(f"      🛑 Pipeline stopped")
            else:
                print(f"      Data: {json.dumps(parsed, indent=8)}")
                
            print()
        except Exception as e:
            print(f"      ❌ Error parsing: {e}\n")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python inspect_mailbox.py <session_id>")
        print("Example: python inspect_mailbox.py 076f3b1f-d6dd-438a-87d4-c177fdc83417")
        sys.exit(1)
    
    session_id = sys.argv[1]
    inspect_mailbox(session_id)
