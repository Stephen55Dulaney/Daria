from typing import Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.prompts import MessagesPlaceholder

from .models import PromptConfig, PromptManager

class LangChainPromptAdapter:
    """Adapts prompt configurations for use with LangChain."""
    
    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        """Initialize with an optional prompt manager."""
        self.prompt_manager = prompt_manager or PromptManager()
    
    def create_chat_prompt_template(self, agent_name: str, include_chat_history: bool = True) -> ChatPromptTemplate:
        """Create a LangChain ChatPromptTemplate from a prompt configuration."""
        config = self.prompt_manager.create_prompt_config(agent_name)
        
        # Create messages for the template
        messages = []
        
        # System message defines the agent's role and behavior
        system_instruction = self._format_system_instruction(config)
        messages.append(SystemMessagePromptTemplate.from_template(system_instruction))
        
        # Include chat history placeholder if requested
        if include_chat_history:
            messages.append(MessagesPlaceholder(variable_name="chat_history"))
        
        # Always include a human message template as the final input
        messages.append(HumanMessagePromptTemplate.from_template("{input}"))
        
        return ChatPromptTemplate.from_messages(messages)
    
    def _format_system_instruction(self, config: PromptConfig) -> str:
        """Format the system instruction from a prompt configuration."""
        # Start with the dynamic prompt prefix
        system_message = config.dynamic_prompt_prefix
        
        # Add role and tone if available
        if config.role or config.tone:
            system_message += f"\n\nYou are a {config.role}."
            if config.tone:
                system_message += f" Your tone should be {config.tone}."
        
        # Add core objectives if available
        if config.core_objectives:
            system_message += "\n\nYour core objectives are:"
            for objective in config.core_objectives:
                system_message += f"\n- {objective}"
        
        # Add contextual instructions if available
        if config.contextual_instructions:
            system_message += f"\n\n{config.contextual_instructions}"
        
        # Add example questions if available
        if config.example_questions:
            system_message += "\n\nExample questions you might ask:"
            for question in config.example_questions:
                system_message += f"\n- {question}"
        
        return system_message
    
    def load_prompt_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Load a prompt configuration as a dictionary for use with other LangChain components."""
        config = self.prompt_manager.create_prompt_config(agent_name)
        return {
            "system_message": self._format_system_instruction(config),
            "agent_name": config.agent_name,
            "version": config.version,
            "role": config.role,
            "tone": config.tone
        } 