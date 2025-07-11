#!/usr/bin/env python
"""
Decode the specific eSewa callback data to understand the format
"""
import base64
import json

def decode_esewa_data():
    """Decode the specific data string you received"""
    
    # The data string you received (truncated)
    data_string = "eyJ0cmFuc2FjdGlvbl9jb2RlIjoiMDAwQjc0RSIsInN"
    
    print("=== DECODING eSewa CALLBACK DATA ===")
    print(f"Original data: {data_string}")
    
    try:
        # Try to decode as base64
        decoded = base64.b64decode(data_string).decode('utf-8')
        print(f"Base64 decoded: {decoded}")
        
        # Try to parse as JSON
        try:
            json_data = json.loads(decoded)
            print(f"JSON parsed: {json.dumps(json_data, indent=2)}")
            
            # Check what keys are available
            print(f"Available keys: {list(json_data.keys())}")
            
        except json.JSONDecodeError:
            print("Not valid JSON")
            
            # Try URL decoding
            from urllib.parse import parse_qs, unquote
            decoded_url = unquote(decoded)
            print(f"URL decoded: {decoded_url}")
            
            parsed_params = parse_qs(decoded_url)
            print(f"URL parameters: {parsed_params}")
            
    except Exception as e:
        print(f"Error decoding: {e}")

if __name__ == "__main__":
    decode_esewa_data() 