import os
import yaml
import datetime
import shutil
from typing import Dict, List, Any, Optional

class PromptConfig:
    """Represents a configurable prompt for an AI agent."""
    
    def __init__(self, 
                 agent_name: str, 
                 version: str = "v1.0",
                 description: str = "",
                 role: str = "",
                 tone: str = "",
                 core_objectives: List[str] = None,
                 contextual_instructions: str = "",
                 dynamic_prompt_prefix: str = "",
                 analysis_prompt: str = "",
                 example_questions: List[str] = None,
                 evaluation_notes: List[str] = None):
        """Initialize a prompt configuration."""
        self.agent_name = agent_name
        self.version = version
        self.description = description
        self.role = role
        self.tone = tone
        self.core_objectives = core_objectives or []
        self.contextual_instructions = contextual_instructions
        self.dynamic_prompt_prefix = dynamic_prompt_prefix
        self.analysis_prompt = analysis_prompt
        self.example_questions = example_questions or []
        self.evaluation_notes = evaluation_notes or []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptConfig':
        """Create a PromptConfig instance from a dictionary."""
        return cls(
            agent_name=data.get('agent_name', ''),
            version=data.get('version', 'v1.0'),
            description=data.get('description', ''),
            role=data.get('role', ''),
            tone=data.get('tone', ''),
            core_objectives=data.get('core_objectives', []),
            contextual_instructions=data.get('contextual_instructions', ''),
            dynamic_prompt_prefix=data.get('dynamic_prompt_prefix', ''),
            analysis_prompt=data.get('analysis_prompt', ''),
            example_questions=data.get('example_questions', []),
            evaluation_notes=data.get('evaluation_notes', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the PromptConfig to a dictionary."""
        return {
            'agent_name': self.agent_name,
            'version': self.version,
            'description': self.description,
            'role': self.role,
            'tone': self.tone,
            'core_objectives': self.core_objectives,
            'contextual_instructions': self.contextual_instructions,
            'dynamic_prompt_prefix': self.dynamic_prompt_prefix,
            'analysis_prompt': self.analysis_prompt,
            'example_questions': self.example_questions,
            'evaluation_notes': self.evaluation_notes
        }


class PromptManager:
    """Manages prompt configurations for AI agents."""
    
    def __init__(self, prompt_dir: str = "langchain_features/prompt_manager/prompts"):
        """Initialize the prompt manager with a directory for prompt files."""
        self.prompt_dir = prompt_dir
        self.history_dir = os.path.join(prompt_dir, ".history")
        
        # Ensure directories exist
        os.makedirs(self.prompt_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
    
    def get_prompt_file_path(self, agent_name: str) -> str:
        """Get the file path for an agent's prompt configuration."""
        return os.path.join(self.prompt_dir, f"{agent_name.lower()}.yml")
    
    def list_agents(self) -> List[str]:
        """List all available agent prompt configurations."""
        agent_files = [f for f in os.listdir(self.prompt_dir) 
                      if f.endswith('.yml') and not f.startswith('.')]
        return [os.path.splitext(f)[0] for f in agent_files]
    
    def load_prompt_config(self, agent_name: str) -> Optional[PromptConfig]:
        """Load a prompt configuration for an agent."""
        file_path = self.get_prompt_file_path(agent_name)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                print(f"DEBUG: Loaded YAML for {agent_name}, keys: {list(data.keys())}")
                if 'analysis_prompt' in data:
                    print(f"DEBUG: Found analysis_prompt in YAML: {data['analysis_prompt'][:50]}...")
                data['agent_name'] = agent_name  # Ensure agent_name is set
                return PromptConfig.from_dict(data)
        except Exception as e:
            print(f"Error loading prompt config for {agent_name}: {e}")
            return None
    
    def save_prompt_config(self, config: PromptConfig) -> bool:
        """Save a prompt configuration and create a backup."""
        file_path = self.get_prompt_file_path(config.agent_name)
        
        # Create backup if file exists
        if os.path.exists(file_path):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                self.history_dir, 
                f"{config.agent_name.lower()}_{timestamp}.yml"
            )
            shutil.copy2(file_path, backup_path)
        
        # Save the updated config
        try:
            with open(file_path, 'w') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving prompt config for {config.agent_name}: {e}")
            return False
    
    def create_default_prompt(self, agent_name: str) -> PromptConfig:
        """Create a default prompt configuration for a new agent."""
        return PromptConfig(
            agent_name=agent_name,
            version="v1.0",
            description=f"{agent_name} is an AI assistant.",
            role="Assistant",
            tone="Helpful, friendly",
            core_objectives=["Assist users effectively"],
            contextual_instructions="Provide helpful responses to user queries.",
            dynamic_prompt_prefix=f"You are {agent_name}, a helpful AI assistant.",
            analysis_prompt="Analyze the conversation to identify key insights, user needs, pain points, and opportunities for improvement.",
            example_questions=["How can I help you today?"],
            evaluation_notes=["Initial version"]
        )
    
    def create_prompt_config(self, agent_name: str) -> PromptConfig:
        """Create or load a prompt configuration for an agent."""
        config = self.load_prompt_config(agent_name)
        if config is None:
            config = self.create_default_prompt(agent_name)
            self.save_prompt_config(config)
        return config

    def get_version_history(self, agent_name: str) -> List[str]:
        """Get the version history for an agent's prompt configuration."""
        history_files = [f for f in os.listdir(self.history_dir) 
                        if f.startswith(f"{agent_name.lower()}_") and f.endswith('.yml')]
        return sorted(history_files, reverse=True)

    def load_prompt_version(self, history_file: str) -> Optional[PromptConfig]:
        """Load a specific version of a prompt configuration."""
        file_path = os.path.join(self.history_dir, history_file)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                agent_name = history_file.split('_')[0]
                data['agent_name'] = agent_name
                return PromptConfig.from_dict(data)
        except Exception as e:
            print(f"Error loading prompt version {history_file}: {e}")
            return None 