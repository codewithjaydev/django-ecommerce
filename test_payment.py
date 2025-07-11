#!/usr/bin/env python
"""
Test script for eSewa payment callback debugging
"""
import requests
import json

def test_payment_callback():
    """Test the payment callback with sample parameters"""
    
    # Base URL for your Django server
    base_url = "http://127.0.0.1:8000"
    
    # Test different parameter combinations that eSewa might send
    test_cases = [
        {
            "name": "Standard eSewa parameters",
            "params": {
                "oid": "TXN_123_456_20250101120000_abc12345",
                "amt": "100.00",
                "refId": "REF123456789"
            }
        },
        {
            "name": "Alternative parameter names",
            "params": {
                "pid": "TXN_123_456_20250101120000_abc12345",
                "amount": "100.00",
                "rid": "REF123456789"
            }
        },
        {
            "name": "Missing parameters (should fail)",
            "params": {
                "oid": "TXN_123_456_20250101120000_abc12345"
                # Missing amt and refId
            }
        },
        {
            "name": "Empty parameters",
            "params": {
                "oid": "",
                "amt": "",
                "refId": ""
            }
        }
    ]
    
    print("=== eSewa Payment Callback Test ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Parameters: {test_case['params']}")
        
        try:
            # Test the debug endpoint first
            debug_url = f"{base_url}/payment/debug/"
            debug_response = requests.get(debug_url, params=test_case['params'])
            print(f"Debug endpoint response: {debug_response.status_code}")
            
            # Test the success endpoint
            success_url = f"{base_url}/payment/success/"
            success_response = requests.get(success_url, params=test_case['params'])
            print(f"Success endpoint response: {success_response.status_code}")
            
            if success_response.status_code == 302:  # Redirect
                print(f"Redirected to: {success_response.headers.get('Location', 'Unknown')}")
            
        except requests.RequestException as e:
            print(f"Error: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_payment_callback() 