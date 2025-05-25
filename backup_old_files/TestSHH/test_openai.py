import os
import openai

# Set API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")

try:
    # Initialize the client
    client = openai.OpenAI(api_key=api_key)
    
    # Call the API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello from DARIA!"}
        ]
    )
    
    print("\nOpenAI API is working correctly!")
    print(f"Response: {response.choices[0].message.content}\n")
    
except Exception as e:
    print(f"Error with OpenAI: {e}") 