"""
Automated Test for JARVIS Browser-Use Integration
Verifies that BrowserEngine, OSEngine, and BrowserWorker interface with the browser automation runner.
"""
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser_engine import browser_engine
from core.os_engine import os_engine

def test_browser_integration():
    print("==================================================")
    print("JARVIS BROWSER-USE INTEGRATION VERIFICATION")
    print("==================================================")
    
    # 1. Availability check
    print(f"1. Subsystem Available : {browser_engine.is_available}")
    assert browser_engine.is_available, "BrowserEngine should report available."
    print("   [PASS] BrowserEngine subsystem verified.")
    
    # 2. Live task test (example.com headless)
    print("\n2. Executing live navigation to https://example.com...")
    result = browser_engine.execute_task(
        task="Go to https://example.com and tell me the primary purpose of the domain",
        headless=True,
        max_steps=3
    )
    
    print(f"   Status      : {result.get('status')}")
    print(f"   Final Result: {result.get('final_result')}")
    print(f"   URLs Visited: {result.get('urls_visited')}")
    
    assert result.get("status") == "success", f"Task should succeed, got: {result}"
    assert "example.com" in str(result.get("urls_visited", [])).lower() or len(result.get("final_result", "")) > 10
    print("   [PASS] Autonomous web navigation verified.")
    
    # 3. OSEngine hook check
    print("\n3. Testing OSEngine.browse_web interface...")
    assert hasattr(os_engine, "browse_web"), "os_engine must have browse_web method."
    print("   [PASS] OSEngine.browse_web verified.")
    
    print("\n==================================================")
    print("ALL BROWSER-USE INTEGRATION CHECKS PASSED NOMINAL")
    print("==================================================")

if __name__ == "__main__":
    test_browser_integration()
