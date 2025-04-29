import boto3
import json
import os
from dotenv import load_dotenv
from typing import Dict, Optional, List, Any

# Load environment variables
load_dotenv()

class AnthropicTest:
    def __init__(self):
        # Load AWS credentials from environment variables
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region = 'us-east-2'  # Updated to us-east-2
        
        # Model ARN
        self.model_id = 'arn:aws:bedrock:us-east-2:522814696964:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
        
        # Initialize Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region
        )

    def test_model(self, interviews: Optional[List[Dict[str, Any]]] = None) -> Dict:
        """Generate a persona using Claude 3.7 Sonnet."""
        try:
            # Create system prompt
            system_prompt = """You are an expert UX researcher specializing in persona creation. Your task is to analyze interview data and create detailed, evidence-based personas.

Generate a persona in the following JSON format:
{
    "name": "Persona Name",
    "summary": "Brief summary of the persona",
    "demographics": {
        "age_range": "e.g., 25-35",
        "gender": "e.g., Female",
        "occupation": "e.g., UX Researcher",
        "location": "e.g., San Francisco, CA",
        "education": "e.g., Master's in HCI"
    },
    "goals": [
        {
            "goal": "Specific goal",
            "motivation": "Why this goal is important",
            "supporting_quotes": ["Relevant quote from interview"]
        }
    ],
    "pain_points": [
        {
            "pain_point": "Specific pain point",
            "impact": "How this affects the user",
            "supporting_quotes": ["Relevant quote from interview"]
        }
    ],
    "behaviors": [
        {
            "behavior": "Specific behavior",
            "frequency": "How often this occurs",
            "context": "When/where this happens",
            "supporting_quotes": ["Relevant quote from interview"]
        }
    ],
    "technology": {
        "devices": ["List of devices used"],
        "software": ["List of software used"],
        "comfort_level": "User's comfort with technology",
        "supporting_quotes": ["Relevant quotes about technology usage"]
    },
    "key_quotes": ["Most important quotes from interviews"]
}

For each section, provide at least 4 distinct observations supported by quotes from the interviews."""

            # Create user message with interview data
            if interviews:
                interview_text = "\n\n".join([
                    f"Interview {i+1}:\n{interview.get('transcript', '')}"
                    for i, interview in enumerate(interviews)
                ])
                user_message = f"Please analyze these interviews and generate a detailed persona:\n\n{interview_text}"
            else:
                # Use sample data for testing
                user_message = """Please analyze this sample interview data and generate a user persona:
                
                Interview Transcript:
                Interviewer: What are your main goals when using technology?
                User: I want to stay organized and efficient in my work. I use various apps to manage my tasks.
                
                Generate a detailed persona focusing on all the specified sections."""

            # Prepare the request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            }

            # Make the API call
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            # Parse and return the response
            response_body = json.loads(response['body'].read())
            
            # Extract the content from the response
            content = response_body.get('content', [{}])[0].get('text', '{}')
            
            try:
                # Try to parse the content as JSON
                persona_data = json.loads(content)
                
                # Ensure all required sections exist
                required_sections = {
                    'name': 'Generated Persona',
                    'summary': 'Persona generated from interview data',
                    'demographics': {
                        'age_range': 'N/A',
                        'gender': 'N/A',
                        'occupation': 'N/A',
                        'location': 'N/A',
                        'education': 'N/A'
                    },
                    'goals': [],
                    'pain_points': [],
                    'behaviors': [],
                    'technology': {
                        'devices': [],
                        'software': [],
                        'comfort_level': 'Not specified',
                        'supporting_quotes': []
                    },
                    'key_quotes': []
                }
                
                # Update with actual data where available
                for key, default_value in required_sections.items():
                    if key not in persona_data:
                        persona_data[key] = default_value
                
                return {
                    "success": True,
                    "model": "Claude 3.7 Sonnet",
                    "response": persona_data
                }
            except json.JSONDecodeError:
                # If parsing fails, return the default structure
                return {
                    "success": True,
                    "model": "Claude 3.7 Sonnet",
                    "response": required_sections
                }

        except Exception as e:
            return {
                "success": False,
                "model": "Claude 3.7 Sonnet",
                "error": str(e)
            }

def main():
    """Run test for Claude 3.7 Sonnet."""
    tester = AnthropicTest()
    
    print("Testing Claude 3.7 Sonnet Integration\n")
    print("Make sure you have set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file\n")
    
    result = tester.test_model()
    
    if result.get("success"):
        print("✓ Test successful")
        print("Response:", result["response"])
    else:
        print("✗ Test failed")
        print("Error:", result.get("error"))
    
    print("\n")

if __name__ == "__main__":
    main() 