#!/usr/bin/env python
"""
Test script for new eSewa callback format with encoded data
"""
import requests
import json
import base64
from urllib.parse import urlencode

def test_new_callback_format():
    """Test the new callback format with encoded data parameter"""
    
    base_url = "http://127.0.0.1:8000"
    
    # Test cases with different encoding formats
    test_cases = [
        {
            "name": "Base64 encoded JSON",
            "data": {
                "transaction_code": "TXN_123_456_20250101120000_abc12345",
                "amount": "100.00",
                "reference_id": "REF123456789",
                "status": "success"
            }
        },
        {
            "name": "Base64 encoded URL parameters",
            "data": "transaction_code=TXN_123_456_20250101120000_abc12345&amount=100.00&reference_id=REF123456789&status=success"
        },
        {
            "name": "Direct JSON (not encoded)",
            "data": {
                "transaction_code": "TXN_123_456_20250101120000_abc12345",
                "amount": "100.00",
                "reference_id": "REF123456789"
            }
        },
        {
            "name": "Mixed format with legacy parameters",
            "data": {
                "oid": "TXN_123_456_20250101120000_abc12345",
                "amt": "100.00",
                "refId": "REF123456789"
            }
        }
    ]
    
    print("=== NEW eSewa Callback Format Test ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        
        # Prepare the data parameter
        if isinstance(test_case['data'], dict):
            # Convert dict to JSON string
            json_data = json.dumps(test_case['data'])
            print(f"JSON data: {json_data}")
            
            # Base64 encode
            encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
            print(f"Base64 encoded: {encoded_data}")
            
            params = {'data': encoded_data}
        else:
            # Already a string, base64 encode it
            encoded_data = base64.b64encode(test_case['data'].encode('utf-8')).decode('utf-8')
            print(f"URL data: {test_case['data']}")
            print(f"Base64 encoded: {encoded_data}")
            
            params = {'data': encoded_data}
        
        try:
            # Test debug endpoint
            debug_url = f"{base_url}/payment/debug/"
            debug_response = requests.get(debug_url, params=params)
            print(f"Debug endpoint response: {debug_response.status_code}")
            
            # Test success endpoint
            success_url = f"{base_url}/payment/success/"
            success_response = requests.get(success_url, params=params)
            print(f"Success endpoint response: {success_response.status_code}")
            
            if success_response.status_code == 302:
                print(f"Redirected to: {success_response.headers.get('Location', 'Unknown')}")
                
        except requests.RequestException as e:
            print(f"Error: {e}")
        
        print("-" * 50)

def test_with_real_data():
    """Test with the actual data format you received"""
    
    base_url = "http://127.0.0.1:8000"
    
    # The actual data you received (truncated)
    real_data = "eyJ0cmFuc2FjdGlvbl9jb2RlIjoi"
    
    print("=== Testing with Real Data Format ===")
    print(f"Real data (truncated): {real_data}")
    
    params = {'data': real_data}
    
    try:
        # Test debug endpoint
        debug_url = f"{base_url}/payment/debug/"
        debug_response = requests.get(debug_url, params=params)
        print(f"Debug endpoint response: {debug_response.status_code}")
        
        if debug_response.status_code == 200:
            response_data = debug_response.json()
            print(f"Debug response: {json.dumps(response_data, indent=2)}")
            
    except requests.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_new_callback_format()
    print("\n" + "="*50 + "\n")
    test_with_real_data() 