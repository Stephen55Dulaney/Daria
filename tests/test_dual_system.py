import unittest
import subprocess
import requests
import time
import signal
import os
import sys
import json
from threading import Thread

class DualSystemTest(unittest.TestCase):
    """Test the dual system setup with both Daria and Remote Interview System"""
    
    @classmethod
    def setUpClass(cls):
        """Start both server processes"""
        print("Starting test servers...")
        
        # Start Daria on port 5003
        cls.daria_process = subprocess.Popen(
            [sys.executable, "run_daria.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start Remote Interview System on port 5001
        cls.remote_process = subprocess.Popen(
            [sys.executable, "run_remote_interview.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for servers to start
        time.sleep(5)
        
        print("Test servers started")
    
    @classmethod
    def tearDownClass(cls):
        """Stop server processes"""
        print("Stopping test servers...")
        
        # Terminate processes
        cls.daria_process.terminate()
        cls.remote_process.terminate()
        
        # Wait for processes to exit
        cls.daria_process.wait()
        cls.remote_process.wait()
        
        print("Test servers stopped")
    
    def test_daria_server(self):
        """Test that Daria server is running on port 5003"""
        try:
            response = requests.get("http://localhost:5003/")
            self.assertEqual(response.status_code, 200)
            print("Daria server is running")
        except requests.exceptions.ConnectionError:
            self.fail("Daria server is not running on port 5003")
    
    def test_remote_interview_server(self):
        """Test that Remote Interview System is running on port 5001"""
        try:
            response = requests.get("http://localhost:5001/")
            self.assertEqual(response.status_code, 200)
            print("Remote Interview System is running")
        except requests.exceptions.ConnectionError:
            self.fail("Remote Interview System is not running on port 5001")
    
    def test_langchain_features(self):
        """Test that LangChain features are accessible"""
        try:
            response = requests.get("http://localhost:5003/langchain/")
            self.assertEqual(response.status_code, 200)
            print("LangChain features are accessible")
        except requests.exceptions.ConnectionError:
            self.fail("LangChain features are not accessible")
    
    def test_create_interview(self):
        """Test creating an interview session"""
        try:
            data = {
                "title": "Test Interview",
                "prompt": "This is a test interview prompt"
            }
            response = requests.post(
                "http://localhost:5003/langchain/interview/create",
                json=data
            )
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(result["status"], "success")
            self.assertIn("session_id", result)
            print(f"Interview created successfully with ID: {result['session_id']}")
        except requests.exceptions.ConnectionError:
            self.fail("Failed to create interview")

if __name__ == "__main__":
    unittest.main() 