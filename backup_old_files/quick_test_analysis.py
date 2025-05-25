#!/usr/bin/env python3
"""
Simple script to test the analysis functionality directly without the web interface.
"""

import os
import sys
from langchain_features.services.interview_service import InterviewService

def test_analysis():
    """Test the analysis functionality."""
    print("Testing analysis functionality...")
    
    # Initialize the interview service
    service = InterviewService(data_dir="data/interviews")
    
    # Simple test transcript
    transcript = """
    Interviewer: What do you think about our product?
    User: I like it but I find the interface confusing sometimes.
    Interviewer: Can you tell me more about what parts are confusing?
    User: The navigation menu has too many options and I often get lost.
    """
    
    # Test prompt
    prompt = "Analyze this interview and identify the key pain points mentioned by the user."
    
    try:
        # Generate analysis
        analysis = service.generate_analysis(transcript, prompt)
        print("\nAnalysis generated successfully:")
        print("-" * 50)
        print(analysis)
        print("-" * 50)
        print("\nTest completed successfully!")
        return True
    except Exception as e:
        print(f"\nError generating analysis: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_analysis()
    sys.exit(0 if success else 1) 