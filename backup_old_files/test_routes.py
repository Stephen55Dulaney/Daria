#!/usr/bin/env python3
"""
Test script to verify that the LangChain routes are properly registered and working.
"""

import sys
import requests
import time
from pathlib import Path
import logging
import subprocess
import signal
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Port for testing
TEST_PORT = 5035

def start_server():
    """Start the server in a subprocess for testing."""
    logger.info(f"Starting test server on port {TEST_PORT}")
    process = subprocess.Popen(
        ["python", "run_interview_api.py", "--use-langchain", "--port", str(TEST_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid  # So we can kill the process group later
    )
    
    # Wait for server to start
    time.sleep(5)
    return process

def stop_server(process):
    """Stop the server subprocess."""
    if process:
        logger.info("Stopping test server")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except:
                pass

def test_routes():
    """Test each LangChain route to ensure it's working."""
    base_url = f"http://localhost:{TEST_PORT}"
    
    # Define routes to test
    routes = [
        "/api/health",  # Basic health check
        "/langchain/dashboard",  # LangChain dashboard
        "/langchain/interview/setup",  # Interview setup page
        "/direct_dashboard"  # Our direct debug route
    ]
    
    success_count = 0
    failure_count = 0
    
    for route in routes:
        url = f"{base_url}{route}"
        try:
            logger.info(f"Testing route: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ SUCCESS: {route} - {response.status_code}")
                success_count += 1
            else:
                logger.error(f"❌ FAILED: {route} - {response.status_code}")
                failure_count += 1
        except Exception as e:
            logger.error(f"❌ ERROR: {route} - {str(e)}")
            failure_count += 1
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info(f"SUMMARY: {success_count} successes, {failure_count} failures")
    logger.info("="*50)
    
    return success_count, failure_count

if __name__ == "__main__":
    process = None
    try:
        # Start the server
        process = start_server()
        
        # Run the tests
        success_count, failure_count = test_routes()
        
        # Exit with appropriate status code
        sys.exit(1 if failure_count > 0 else 0)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted")
    finally:
        # Clean up
        if process:
            stop_server(process) 