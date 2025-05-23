"""Fix script for the interview agent"""

import sys
import re

def fix_interview_agent():
    """Fix the interview agent to use our adapter"""
    try:
        with open('langchain_features/services/interview_agent.py', 'r') as f:
            content = f.read()
        
        # Add import for our adapter
        if "from openai_langchain_adapter import OpenAILangChainAdapter" not in content:
            content = re.sub(
                r'from langchain.prompts import',
                'from openai_langchain_adapter import OpenAILangChainAdapter\nfrom langchain.prompts import',
                content
            )
        
        # Replace the LLM initialization
        content = re.sub(
            r'self\.llm = .*',
            'self.llm = OpenAILangChainAdapter(model_name="gpt-4", temperature=0.7)',
            content
        )
        
        with open('langchain_features/services/interview_agent.py', 'w') as f:
            f.write(content)
        
        print("Successfully fixed interview_agent.py")
        return True
    except Exception as e:
        print(f"Error fixing interview_agent.py: {str(e)}")
        return False

if __name__ == "__main__":
    fix_interview_agent()
