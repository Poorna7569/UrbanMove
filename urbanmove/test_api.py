"""
Comprehensive manual test suite for UrbanMove Smart Mobility Platform API

Tests all endpoints:
1. Health check (/api/v1/health)
2. Authentication (/api/v1/auth/login)
3. Data ingestion (/api/v1/ingest)
4. Route optimization (/api/v1/route)

SETUP: Start the service first with: docker-compose up

Run manually with: python test_api.py
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "demo_password_123"

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text):
    """Print formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ {text}{RESET}")


def test_health_check():
    """Test 1: Health Check Endpoint"""
    print_header("Test 1: Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("database") == "connected":
                print_success("Health check passed - Backend and Database operational")
                return True
            else:
                print_error(f"Health check shows issues: {data}")
                return False
        else:
            print_error(f"Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        return False


def test_login():
    """Test 2: Authentication - Login"""
    print_header("Test 2: Authentication - Login")
    
    try:
        payload = {
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=5)
        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token and data.get("token_type") == "bearer":
                print_success(f"Login successful - Token obtained: {token[:50]}...")
                return token
            else:
                print_error("Login response missing token")
                return None
        else:
            print_error(f"Login failed with status {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Login failed: {str(e)}")
        return None


def test_data_ingestion():
    """Test 3: Data Ingestion"""
    print_header("Test 3: Data Ingestion - POST /ingest")
    
    test_cases = [
        {"name": "Low traffic", "data": {"vehicle_id": "VEH-001", "latitude": 40.7128, "longitude": -74.0060, "traffic_level": "low"}},
        {"name": "Medium traffic", "data": {"vehicle_id": "VEH-002", "latitude": 40.7138, "longitude": -74.0070, "traffic_level": "medium"}},
        {"name": "High traffic", "data": {"vehicle_id": "VEH-003", "latitude": 40.7148, "longitude": -74.0080, "traffic_level": "high"}}
    ]
    
    all_passed = True
    for test_case in test_cases:
        try:
            print_info(f"Testing: {test_case['name']}")
            response = requests.post(f"{BASE_URL}/ingest", json=test_case["data"], timeout=5)
            print_info(f"  Status Code: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                print_info(f"  Record ID: {data.get('id')}, Vehicle: {data.get('vehicle_id')}")
                print_success(f"  {test_case['name']} passed")
            else:
                print_error(f"  {test_case['name']} failed (status {response.status_code})")
                all_passed = False
        except Exception as e:
            print_error(f"  {test_case['name']} failed: {str(e)}")
            all_passed = False
    
    return all_passed


def test_route_calculation(token):
    """Test 4: Route Calculation (JWT Protected)"""
    print_header("Test 4: Route Calculation - GET /route (JWT Protected)")
    
    if not token:
        print_error("Cannot test route calculation - no valid token")
        return False
    
    test_cases = [
        {"name": "NY to Boston", "source": "New York, NY", "destination": "Boston, MA"},
        {"name": "LA to SF", "source": "Los Angeles, CA", "destination": "San Francisco, CA"},
        {"name": "Chicago to Milwaukee", "source": "Chicago, IL", "destination": "Milwaukee, WI"}
    ]
    
    all_passed = True
    headers = {"Authorization": f"Bearer {token}"}
    
    for test_case in test_cases:
        try:
            print_info(f"Testing: {test_case['name']}")
            response = requests.get(f"{BASE_URL}/route", params={"source": test_case["source"], "destination": test_case["destination"]}, headers=headers, timeout=5)
            print_info(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_info(f"  Route: {data.get('route')}, Traffic: {data.get('traffic_status')}")
                print_success(f"  {test_case['name']} passed")
            else:
                print_error(f"  {test_case['name']} failed (status {response.status_code})")
                all_passed = False
        except Exception as e:
            print_error(f"  {test_case['name']} failed: {str(e)}")
            all_passed = False
    
    return all_passed


def test_route_without_token():
    """Test 5: Verify Route Protection (No JWT)"""
    print_header("Test 5: Security - Route Protection (No JWT)")
    
    try:
        print_info("Attempting to access /route without JWT token...")
        response = requests.get(f"{BASE_URL}/route", params={"source": "Test", "destination": "Test"}, timeout=5)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print_success("Security check passed - /route correctly requires JWT token")
            return True
        else:
            print_error(f"Security check failed - endpoint returned {response.status_code} instead of 401")
            return False
    except Exception as e:
        print_error(f"Security check failed: {str(e)}")
        return False


def test_invalid_credentials():
    """Test 6: Invalid Credentials"""
    print_header("Test 6: Security - Invalid Credentials")
    
    try:
        payload = {"username": "invalid_user", "password": "invalid_password"}
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=5)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print_success("Security check passed - Invalid credentials rejected")
            return True
        else:
            print_error(f"Security check failed - endpoint returned {response.status_code} instead of 401")
            return False
    except Exception as e:
        print_error(f"Security check failed: {str(e)}")
        return False


def test_invalid_data_ingestion():
    """Test 7: Invalid Data Validation"""
    print_header("Test 7: Data Validation - Invalid Coordinates")
    
    try:
        payload = {"vehicle_id": "TEST-001", "latitude": 200, "longitude": -74.0060, "traffic_level": "low"}
        response = requests.post(f"{BASE_URL}/ingest", json=payload, timeout=5)
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code >= 400:
            print_success("Data validation passed - Invalid coordinates rejected")
            return True
        else:
            print_error(f"Data validation failed - endpoint accepted invalid data")
            return False
    except Exception as e:
        print_error(f"Data validation test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests sequentially"""
    print(f"\n{BOLD}{YELLOW}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                  UrbanMove Smart Mobility Platform                    ║")
    print("║                            API Test Suite                             ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    print_info(f"Testing API: {BASE_URL}")
    print_info(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    # Wait for service to be ready
    print_info("Waiting for service to be ready...")
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                break
        except:
            pass
        
        if attempt < max_retries - 1:
            print_info(f"Attempt {attempt + 1}/{max_retries} - Retrying in 2 seconds...")
            time.sleep(2)
        else:
            print_error("Service did not become ready in time")
            return False
    
    results = {}
    results["Health Check"] = test_health_check()
    token = test_login()
    results["Authentication"] = token is not None
    results["Data Ingestion"] = test_data_ingestion()
    results["Route Calculation"] = test_route_calculation(token)
    results["Route Protection"] = test_route_without_token()
    results["Invalid Credentials"] = test_invalid_credentials()
    results["Invalid Data"] = test_invalid_data_ingestion()
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test_name:.<45} {status}")
    
    print()
    if passed == total:
        print_success(f"All {total} tests passed!")
    else:
        print_error(f"{passed}/{total} tests passed ({total - passed} failed)")
    
    print(f"\n{BOLD}{YELLOW}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                          Test Execution Complete                      ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    return passed == total


if __name__ == "__main__":
    import sys
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test suite interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)

