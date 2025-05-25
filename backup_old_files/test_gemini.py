"""
Test script to verify Gemini API connectivity.
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

def test_gemini_connection():
    """Test connection to Gemini API."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ Error: GEMINI_API_KEY not found in .env file")
            return False
            
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Test with a simple prompt
        prompt = "Generate a short test response to verify connectivity."
        response = model.generate_content(prompt)
        
        print("✅ Successfully connected to Gemini API!")
        print("\nTest Response:")
        print("-" * 50)
        print(response.text)
        print("-" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Gemini API: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Gemini API Connection...")
    test_gemini_connection() 