"""Mock OpenAI Provider for DARIA compatibility"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class MockOpenAIProvider:
    """A mock OpenAI provider that returns predefined responses"""
    
    def __init__(self):
        self.model = "gpt-4"
        logger.info("Initialized MockOpenAIProvider with model=gpt-4")
    
    def complete(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return a mock completion response"""
        logger.info(f"Mock completion for prompt: {prompt[:50]}...")
        return {
            "choices": [
                {
                    "text": "I am a mock response from the interview AI.",
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 10,
                "total_tokens": len(prompt.split()) + 10
            }
        }
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Return a mock chat response"""
        logger.info(f"Mock chat with {len(messages)} messages")
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I am a mock response from the interview AI."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                "completion_tokens": 10,
                "total_tokens": sum(len(m.get("content", "").split()) for m in messages) + 10
            }
        }

# Create a singleton instance
provider = MockOpenAIProvider()
