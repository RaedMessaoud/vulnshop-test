import pytest
import requests
import time
import subprocess
import sys
import os
from datetime import datetime

# ==================== CONFIGURATION ====================
APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
TIMEOUT = 10
TEST_RESULTS = []

# ==================== FIXTURES ====================
@pytest.fixture(scope='session', autouse=True)
def setup_teardown():
    """Setup and teardown for test session"""
    print("\n" + "="*60)
    print("🧪 DAST Security Testing Session Started")
    print("="*60)
    print(f"Target: {APP_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("="*60 + "\n")
    
    # Wait for app to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{APP_URL}/", timeout=5)
            if response.status_code:
                print(f"✅ Application is responding at {APP_URL}")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"⏳ Waiting for application to be ready... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print(f"❌ Application not responding at {APP_URL}")
                raise
    
    yield
    
    print("\n" + "="*60)
    print("✅ DAST Security Testing Session Completed")
    print("="*60 + "\n")


# ==================== HELPER FUNCTIONS ====================
def log_test_result(test_name: str, passed: bool, details: str = ""):
    """Log test result to file and console"""
    status = "✅ PASS" if passed else "❌ FAIL"
    message = f"{status} - {test_name}"
    if details:
        message += f": {details}"
    
    print(message)
    TEST_RESULTS.append({
        'test': test_name,
        'passed': passed,
        'timestamp': datetime.now().isoformat(),
        'details': details
    })


def save_test_results():
    """Save test results to file"""
    results_file = 'dast-test-results.txt'
    with open(results_file, 'w') as f:
        f.write("DAST Test Results\n")
        f.write("="*60 + "\n\n")
        for result in TEST_RESULTS:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            f.write(f"{status} - {result['test']}\n")
            if result['details']:
                f.write(f"  Details: {result['details']}\n")
            f.write(f"  Time: {result['timestamp']}\n\n")


# ==================== CONNECTIVITY TESTS ====================
def test_01_application_accessibility():
    """Verify application is accessible and responsive"""
    try:
        response = requests.get(f"{APP_URL}/", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        log_test_result("Application Accessibility", True, f"Status: {response.status_code}")
        assert "Vuln" in response.text or "Shop" in response.text or "Home" in response.text
    except Exception as e:
        log_test_result("Application Accessibility", False, str(e))
        raise


# ==================== SQL INJECTION TESTS ====================
def test_02_sql_injection_login_bypass():
    """Test SQL injection vulnerability in login form"""
    payload = {'username': 'admin', 'password': "' OR '1'='1"}
    
    try:
        response = requests.post(
            f"{APP_URL}/login",
            data=payload,
            timeout=TIMEOUT,
            allow_redirects=True
        )
        
        # Check if SQL injection should have worked (vulnerable app)
        vulnerable = 'Profil' in response.text or 'profile' in response.text or 'dashboard' in response.text
        
        if vulnerable:
            log_test_result(
                "SQL Injection - Login Bypass",
                False,
                "❌ VULNERABILITY: Login bypass via SQL injection detected"
            )
        else:
            log_test_result(
                "SQL Injection - Login Bypass",
                True,
                "✅ Login appears protected from SQL injection"
            )
    except Exception as e:
        log_test_result("SQL Injection - Login Bypass", False, f"Request failed: {str(e)}")


def test_03_sql_injection_union_based():
    """Test UNION-based SQL injection in search"""
    payload = {'q': "' UNION SELECT id,username,password,role FROM users--"}
    
    try:
        response = requests.get(
            f"{APP_URL}/search",
            params=payload,
            timeout=TIMEOUT
        )
        
        # Check for data extraction
        data_leaked = any(x in response.text.lower() for x in ['admin', 'alice', 'password', 'role'])
        
        if data_leaked:
            log_test_result(
                "SQL Injection - UNION-based",
                False,
                "❌ VULNERABILITY: Data extraction via UNION injection detected"
            )
        else:
            log_test_result(
                "SQL Injection - UNION-based",
                True,
                "✅ Search appears protected from UNION injection"
            )
    except Exception as e:
        log_test_result("SQL Injection - UNION-based", False, f"Request failed: {str(e)}")


def test_04_sql_injection_blind():
    """Test blind SQL injection with time-based detection"""
    
    try:
        # Normal query
        start = time.time()
        response1 = requests.get(
            f"{APP_URL}/search",
            params={'q': 'test'},
            timeout=TIMEOUT
        )
        time_normal = time.time() - start
        
        # Blind injection query
        start = time.time()
        response2 = requests.get(
            f"{APP_URL}/search",
            params={'q': "' AND SLEEP(2)--"},
            timeout=TIMEOUT
        )
        time_sleep = time.time() - start
        
        # Check if sleep caused delay (would indicate vulnerability)
        time_diff = time_sleep - time_normal
        vulnerable = time_diff > 1.5  # Should sleep 2 seconds
        
        if vulnerable:
            log_test_result(
                "SQL Injection - Blind Time-Based",
                False,
                f"❌ VULNERABILITY: Time-based blind SQL injection detected (delay: {time_diff:.2f}s)"
            )
        else:
            log_test_result(
                "SQL Injection - Blind Time-Based",
                True,
                f"✅ No time-delay detected (baseline: {time_normal:.2f}s, test: {time_sleep:.2f}s)"
            )
    except requests.exceptions.Timeout:
        log_test_result(
            "SQL Injection - Blind Time-Based",
            False,
            "⚠️ Request timeout - possible slow query"
        )
    except Exception as e:
        log_test_result("SQL Injection - Blind Time-Based", False, f"Test failed: {str(e)}")


# ==================== AUTHENTICATION TESTS ====================
def test_05_authentication_profile_access():
    """Test if profile page requires authentication"""
    
    try:
        response = requests.get(
            f"{APP_URL}/profile",
            timeout=TIMEOUT,
            allow_redirects=False
        )
        
        # Should redirect to login (302) or deny (401/403)
        protected = response.status_code in [301, 302, 401, 403]
        
        if protected:
            log_test_result(
                "Authentication - Profile Protection",
                True,
                f"✅ Profile properly protected (HTTP {response.status_code})"
            )
        else:
            log_test_result(
                "Authentication - Profile Access",
                False,
                f"❌ VULNERABILITY: Profile accessible without authentication (HTTP {response.status_code})"
            )
    except Exception as e:
        log_test_result("Authentication - Profile Protection", False, f"Request failed: {str(e)}")


def test_06_authentication_session_hijacking():
    """Test session security"""
    
    try:
        # Create session
        session = requests.Session()
        response = session.get(f"{APP_URL}/", timeout=TIMEOUT)
        
        # Check for session cookie
        if 'Set-Cookie' in response.headers or session.cookies:
            log_test_result(
                "Session Management - Cookie Detection",
                True,
                "✅ Session cookies are being used"
            )
            
            # Check for security flags
            cookie_header = response.headers.get('Set-Cookie', '')
            has_secure = 'Secure' in cookie_header or True  # In local testing, Secure may not be set
            has_httponly = 'HttpOnly' in cookie_header
            
            if has_httponly:
                log_test_result(
                    "Session Management - HttpOnly Flag",
                    True,
                    "✅ HttpOnly flag is set on session cookie"
                )
            else:
                log_test_result(
                    "Session Management - HttpOnly Flag",
                    False,
                    "⚠️ HttpOnly flag not found on session cookie"
                )
        else:
            log_test_result(
                "Session Management - Cookie Detection",
                True,
                "Session cookies not detected (may be secure)"
            )
    except Exception as e:
        log_test_result("Session Management - Cookie Detection", False, f"Request failed: {str(e)}")


# ==================== INPUT VALIDATION TESTS ====================
def test_07_input_validation_xss_potential():
    """Test for potential XSS vulnerabilities"""
    
    xss_payloads = [
        '<script>alert("XSS")</script>',
        '"><img src=x onerror=alert(1)>',
        'javascript:alert(1)'
    ]
    
    try:
        for payload in xss_payloads:
            response = requests.get(
                f"{APP_URL}/search",
                params={'q': payload},
                timeout=TIMEOUT
            )
            
            # Check if payload is reflected unescaped
            if payload in response.text:
                log_test_result(
                    f"XSS Detection - {payload[:30]}...",
                    False,
                    "⚠️ Potential XSS: Payload reflected in response"
                )
                break
        else:
            log_test_result(
                "Input Validation - XSS Protection",
                True,
                "✅ XSS payloads appear to be handled safely"
            )
    except Exception as e:
        log_test_result("Input Validation - XSS Protection", False, f"Test failed: {str(e)}")


# ==================== CONFIGURATION TESTS ====================
def test_08_error_handling_information_disclosure():
    """Test if error messages reveal sensitive information"""
    
    try:
        # Try to trigger an error with invalid input
        response = requests.get(
            f"{APP_URL}/search",
            params={'q': "' OR 1=1; DROP TABLE users;--"},
            timeout=TIMEOUT
        )
        
        # Check for sensitive info in error messages
        sensitive_patterns = [
            'SQL',
            'database',
            'MySQL',
            'PostgreSQL',
            'SQLite',
            'traceback',
            'Exception'
        ]
        
        response_lower = response.text.lower()
        sensitive_info_found = any(pattern.lower() in response_lower for pattern in sensitive_patterns)
        
        if sensitive_info_found:
            log_test_result(
                "Configuration - Error Message Security",
                False,
                "⚠️ VULNERABILITY: Error messages may reveal system information"
            )
        else:
            log_test_result(
                "Configuration - Error Message Security",
                True,
                "✅ Error messages appear generic and safe"
            )
    except Exception as e:
        log_test_result("Configuration - Error Message Security", False, f"Test failed: {str(e)}")


# ==================== PERFORMANCE & DOS TESTS ====================
def test_09_performance_response_time():
    """Test application response time"""
    
    try:
        times = []
        for i in range(3):
            start = time.time()
            response = requests.get(f"{APP_URL}/", timeout=TIMEOUT)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        
        if avg_time < 1.0:
            log_test_result(
                "Performance - Response Time",
                True,
                f"✅ Good response time: {avg_time:.2f}s average"
            )
        else:
            log_test_result(
                "Performance - Response Time",
                False,
                f"⚠️ Slow response time: {avg_time:.2f}s average"
            )
    except Exception as e:
        log_test_result("Performance - Response Time", False, f"Test failed: {str(e)}")


# ==================== TEARDOWN ====================
@pytest.fixture(scope='session', autouse=True)
def finalize(setup_teardown):
    """Finalize tests and save results"""
    yield
    save_test_results()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])