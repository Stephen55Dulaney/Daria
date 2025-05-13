"""
LangChain-powered Interview Agent

This module provides a LangChain-based intelligent interview agent with conversation
memory and customized character prompts.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import json
import uuid

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import ConversationChain, LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterviewAgent:
    """LangChain-powered Interview Agent with conversation memory"""
    
    def __init__(
        self,
        character_name: str,
        system_prompt: str,
        session_id: str = None,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        verbose: bool = False
    ):
        """
        Initialize the Interview Agent
        
        Args:
            character_name: Name of the character/persona
            system_prompt: System prompt for the LLM
            session_id: Unique identifier for this conversation session
            model_name: LLM model to use
            temperature: Temperature setting for LLM response generation
            verbose: Enable verbose output for debugging
        """
        self.character_name = character_name
        self.system_prompt = system_prompt
        self.session_id = session_id or str(uuid.uuid4())
        self.model_name = model_name
        self.temperature = temperature
        self.verbose = verbose
        
        # Initialize LangChain components
        self._initialize_chain()
        
        logger.info(f"Initialized InterviewAgent for character '{character_name}' with session_id '{self.session_id}'")
    
    def _initialize_chain(self):
        """Initialize the LangChain conversation chain"""
        # Initialize chat model
        try:
            from langchain_community.chat_models import ChatOpenAI
        except ImportError:
            from langchain.chat_models import ChatOpenAI
            
        self.llm = ChatOpenAI(
            model_name=self.model_name,
            temperature=self.temperature,
            verbose=self.verbose
        )
        
        # Fix prompt and memory compatibility
        from langchain.chains import LLMChain
        
        # Initialize conversation memory with correct keys
        self.memory = ConversationBufferMemory(
            input_key="input",
            memory_key="history"
        )
        
        # Initialize prompt template with correct variables
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.system_prompt),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
        
        # Use LLMChain instead of ConversationChain for better compatibility
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=self.verbose
        )
        
        logger.info(f"LangChain chain initialized for session '{self.session_id}'")
    
    def generate_response(self, user_input: str) -> str:
        """
        Generate a response to the user's input
        
        Args:
            user_input: The user's message/question
            
        Returns:
            str: The agent's response
        """
        try:
            logger.info(f"Generating response for input: '{user_input}'")
            # Add "Continue the interview" instruction to ensure we get appropriate follow-up questions
            prompt_suffix = "Continue the interview by asking an appropriate follow-up question or introducing a new relevant topic."
            full_input = f"{user_input}\n\n{prompt_suffix}"
            
            response = self.chain.run(input=full_input)
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question. Error: {str(e)}"
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history
        
        Returns:
            List[Dict[str, str]]: List of message dictionaries with 'role' and 'content'
        """
        messages = self.memory.chat_memory.messages
        history = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                history.append({"role": "system", "content": msg.content})
        
        return history
    
    def save_conversation(self, filepath: str) -> bool:
        """
        Save the conversation history to a file
        
        Args:
            filepath: Path to save the conversation
            
        Returns:
            bool: Success status
        """
        try:
            history = self.get_conversation_history()
            with open(filepath, 'w') as f:
                json.dump({
                    "session_id": self.session_id,
                    "character_name": self.character_name,
                    "conversation": history
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            return False 