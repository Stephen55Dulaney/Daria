import os
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Check if API key is set
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")

try:
    # Initialize the LLM
    llm = ChatOpenAI(
        temperature=0.7,
        model="gpt-3.5-turbo",
    )
    
    # Create a conversation chain with memory
    conversation = ConversationChain(
        llm=llm, 
        memory=ConversationBufferMemory(),
        verbose=True
    )
    
    # Test the conversation
    response = conversation.predict(input="Hello, I'm testing if LangChain works in DARIA.")
    print("\nLangChain is working correctly!")
    print(f"Response: {response}\n")
    
except Exception as e:
    print(f"Error with LangChain: {e}") 