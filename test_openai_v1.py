#!/usr/bin/env python3
"""
Simple script to test OpenAI API v1.0+ directly.
"""

import os
import sys
from openai import OpenAI

def test_openai_v1():
    """Test OpenAI API v1.0+ for analysis."""
    print("Testing OpenAI API v1.0+ analysis functionality...")
    
    # Make sure OpenAI API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return False
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Simple test transcript
    transcript = """
    Interviewer: What do you think about our product?
    User: I like it but I find the interface confusing sometimes.
    Interviewer: Can you tell me more about what parts are confusing?
    User: The navigation menu has too many options and I often get lost.
    """
    
    # Test prompt
    prompt = """
    Analyze this interview and identify the key pain points mentioned by the user.
    
    INTERVIEW TRANSCRIPT:
    """ + transcript + """
    
    ANALYSIS:
    """
    
    try:
        # Call OpenAI API directly with v1.0+ syntax
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interview analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        # Extract the analysis text with v1.0+ syntax
        analysis = response.choices[0].message.content.strip()
        
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
    success = test_openai_v1()
    sys.exit(0 if success else 1) 