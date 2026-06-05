"""
Validation Engine — JARVIS Neural Health Audit
Automated testing node for self-healing verification.
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

class TestEngine:
    """
    Executes automated tests to verify the integrity 
    of code modifications and system performance.
    """

    def run_tests(self):
        """
        Run the project-wide test suite using pytest.
        Returns: (Success Boolean, Stdout/Error Message)
        """
        try:
            logger.info("Test Engine: Initiating Neural Health Audit...")
            # Running with -v for verbosity and -q to suppress extra info if needed
            result = subprocess.run(
                ["pytest"],
                capture_output=True,
                text=True
            )
            
            success = (result.returncode == 0)
            status_msg = result.stdout if success else result.stderr
            
            if success:
                logger.info("✅ Test Engine: Audit Passed.")
            else:
                logger.warning("❌ Test Engine: Audit Failed.")
                
            return success, status_msg

        except Exception as e:
            logger.error(f"Test Engine: Execution Error: {e}")
            return False, str(e)
