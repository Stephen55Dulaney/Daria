import os
import yaml
import json
import shutil
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define evaluation rubric categories and descriptions
EVALUATION_RUBRIC = {
    "clarity": "How clear and understandable is the agent's response? (1-5)",
    "relevance": "How relevant is the response to the user's query? (1-5)",
    "accuracy": "How accurate and factually correct is the information provided? (1-5)",
    "helpfulness": "How helpful is the response in addressing the user's needs? (1-5)",
    "completeness": "How complete is the response in addressing all aspects of the query? (1-5)"
}

class PromptManager:
    """
    Manager for LangChain prompts that provides functionality for:
    - Loading prompt templates
    - Creating and versioning prompt templates
    - Evaluating prompt performance
    - Tracking prompt usage and feedback
    """
    
    def __init__(self, prompt_dir: str = None, history_dir: str = None):
        """
        Initialize the PromptManager with directories for prompts and history
        
        Args:
            prompt_dir: Directory where prompt YAML files are stored
            history_dir: Directory where prompt history is stored
        """
        base_dir = Path(__file__).parent
        self.prompt_dir = Path(prompt_dir) if prompt_dir else base_dir / "prompts"
        self.history_dir = Path(history_dir) if history_dir else self.prompt_dir / ".history"
        
        # Create directories if they don't exist
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # Track feedback for prompts
        self.feedback_file = self.prompt_dir / "feedback.json"
        self._load_feedback()
    
    def _load_feedback(self):
        """Load feedback data from JSON file"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    self.feedback = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error loading feedback file. Creating new feedback tracking.")
                self.feedback = []
        else:
            self.feedback = []
    
    def _save_feedback(self):
        """Save feedback data to JSON file"""
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback, f, indent=2)
    
    def get_available_agents(self) -> List[str]:
        """
        Get a list of all available agent names from prompt files
        
        Returns:
            List of agent names (without file extensions)
        """
        agent_files = list(self.prompt_dir.glob("*.yml"))
        return [file.stem for file in agent_files]
    
    def load_prompt(self, agent_name: str) -> Dict[str, Any]:
        """
        Load a prompt template for a specific agent
        
        Args:
            agent_name: Name of the agent (without file extension)
            
        Returns:
            Dictionary containing the prompt template configuration
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        prompt_file = self.prompt_dir / f"{agent_name.lower()}.yml"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def save_prompt(self, agent_name: str, config: Dict[str, Any], create_version: bool = True) -> str:
        """
        Save a prompt template for a specific agent
        
        Args:
            agent_name: Name of the agent (without file extension)
            config: Dictionary containing the prompt template configuration
            create_version: Whether to create a versioned backup
            
        Returns:
            Path to the saved prompt file
        """
        prompt_file = self.prompt_dir / f"{agent_name.lower()}.yml"
        
        # Create a version backup if requested
        if create_version and prompt_file.exists():
            self._create_version_backup(agent_name)
        
        # Update version if not specified
        if 'version' not in config and prompt_file.exists():
            try:
                with open(prompt_file, 'r') as f:
                    old_config = yaml.safe_load(f)
                    if 'version' in old_config:
                        # Increment version (format: v1.0 -> v1.1)
                        version_str = old_config['version']
                        if version_str.startswith('v'):
                            major, minor = version_str[1:].split('.')
                            new_version = f"v{major}.{int(minor) + 1}"
                            config['version'] = new_version
            except Exception as e:
                logger.warning(f"Error updating version: {str(e)}")
                # Default to v1.0 if can't parse version
                config['version'] = 'v1.0'
        elif 'version' not in config:
            config['version'] = 'v1.0'
        
        # Ensure agent_name is in the config
        config['agent_name'] = agent_name
        
        with open(prompt_file, 'w') as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False)
        
        return str(prompt_file)
    
    def _create_version_backup(self, agent_name: str) -> str:
        """
        Create a versioned backup of a prompt template
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to the backup file
        """
        prompt_file = self.prompt_dir / f"{agent_name.lower()}.yml"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.history_dir / f"{agent_name.lower()}_{timestamp}.yml"
        
        shutil.copy2(prompt_file, backup_file)
        logger.info(f"Created backup of {agent_name} prompt at {backup_file}")
        
        return str(backup_file)
    
    def get_prompt_history(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get the version history for a specific agent's prompt
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of dictionaries containing version history information
        """
        history_files = sorted(self.history_dir.glob(f"{agent_name.lower()}_*.yml"))
        history = []
        
        for file in history_files:
            try:
                with open(file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Extract timestamp from filename
                timestamp_str = file.stem.split('_', 1)[1]
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                history.append({
                    'version': config.get('version', 'unknown'),
                    'timestamp': timestamp.isoformat(),
                    'filename': file.name
                })
            except Exception as e:
                logger.warning(f"Error loading history file {file}: {str(e)}")
        
        return history
    
    def create_prompt_template(self, agent_name: str, role: str, description: str, 
                              tone: str, core_objectives: List[str],
                              contextual_instructions: str,
                              dynamic_prompt_prefix: str,
                              analysis_prompt: str = "") -> Dict[str, Any]:
        """
        Create a new prompt template with standard fields
        
        Args:
            agent_name: Name of the agent
            role: Role of the agent
            description: Description of the agent
            tone: Tone of the agent
            core_objectives: List of core objectives
            contextual_instructions: Contextual instructions
            dynamic_prompt_prefix: Dynamic prompt prefix
            analysis_prompt: Analysis-specific prompt for research and evaluation
            
        Returns:
            Dictionary containing the prompt template configuration
        """
        template = {
            'agent_name': agent_name,
            'version': 'v1.0',
            'description': description,
            'role': role,
            'tone': tone,
            'core_objectives': core_objectives,
            'contextual_instructions': contextual_instructions,
            'dynamic_prompt_prefix': dynamic_prompt_prefix,
            'analysis_prompt': analysis_prompt,
            'evaluation_metrics': [],
            'evaluation_notes': [f"Initial version created on {datetime.now().strftime('%Y-%m-%d')}"]
        }
        
        return template
    
    def add_feedback(self, agent_name: str, session_id: str, score: int, 
                    notes: str, version: str = None, evaluation_metrics: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Add feedback for a prompt version
        
        Args:
            agent_name: Name of the agent
            session_id: ID of the session where the prompt was used
            score: Score (1-5) for the prompt performance
            notes: Notes or comments about the prompt performance
            version: Version of the prompt (if None, current version will be used)
            evaluation_metrics: Detailed evaluation metrics using rubric categories (1-5 for each category)
            
        Returns:
            The feedback entry that was added
        """
        if version is None:
            try:
                config = self.load_prompt(agent_name)
                version = config.get('version', 'unknown')
            except FileNotFoundError:
                version = 'unknown'
        
        # Create a timestamp for the feedback
        timestamp = datetime.now().isoformat()
        
        # Default metrics if not provided
        if evaluation_metrics is None:
            evaluation_metrics = {}
        
        feedback_entry = {
            'agent': agent_name,
            'version': version,
            'session_id': session_id,
            'score': score,
            'notes': notes,
            'timestamp': timestamp,
            'evaluation_metrics': evaluation_metrics
        }
        
        self.feedback.append(feedback_entry)
        self._save_feedback()
        
        logger.info(f"Added feedback for {agent_name} (v{version}): score={score}")
        
        return feedback_entry
    
    def get_feedback(self, agent_name: str = None, version: str = None) -> List[Dict[str, Any]]:
        """
        Get feedback for a specific agent and/or version
        
        Args:
            agent_name: Name of the agent (if None, all agents)
            version: Version of the prompt (if None, all versions)
            
        Returns:
            List of feedback entries
        """
        if agent_name is None and version is None:
            return self.feedback
        
        filtered_feedback = self.feedback.copy()
        
        if agent_name is not None:
            filtered_feedback = [f for f in filtered_feedback if f['agent'] == agent_name]
        
        if version is not None:
            filtered_feedback = [f for f in filtered_feedback if f['version'] == version]
        
        return filtered_feedback
    
    def get_prompt_performance(self, agent_name: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent's prompt
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing performance metrics
        """
        feedback = self.get_feedback(agent_name)
        
        if not feedback:
            return {
                'agent': agent_name,
                'total_sessions': 0,
                'average_score': None,
                'by_version': {},
                'score_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                'evaluation_metrics': {}
            }
        
        # Calculate overall metrics
        total_sessions = len(feedback)
        average_score = sum(f['score'] for f in feedback) / total_sessions
        
        # Calculate score distribution
        score_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for entry in feedback:
            score = entry['score']
            if score in score_distribution:
                score_distribution[score] += 1
        
        # Calculate metrics by version
        versions = {}
        for entry in feedback:
            version = entry['version']
            if version not in versions:
                versions[version] = {
                    'sessions': 0,
                    'scores': [],
                    'average_score': 0,
                    'score_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                    'evaluation_metrics': {}
                }
            
            versions[version]['sessions'] += 1
            versions[version]['scores'].append(entry['score'])
            
            # Update score distribution for this version
            score = entry['score']
            if score in versions[version]['score_distribution']:
                versions[version]['score_distribution'][score] += 1
            
            # Collect evaluation metrics
            if 'evaluation_metrics' in entry and entry['evaluation_metrics']:
                for metric, value in entry['evaluation_metrics'].items():
                    if metric not in versions[version]['evaluation_metrics']:
                        versions[version]['evaluation_metrics'][metric] = []
                    versions[version]['evaluation_metrics'][metric].append(value)
        
        # Calculate aggregate evaluation metrics across all versions
        all_metrics = {}
        for entry in feedback:
            if 'evaluation_metrics' in entry and entry['evaluation_metrics']:
                for metric, value in entry['evaluation_metrics'].items():
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(value)
        
        # Calculate average scores by version
        for version in versions:
            versions[version]['average_score'] = sum(versions[version]['scores']) / len(versions[version]['scores'])
            
            # Calculate average for each evaluation metric
            for metric, values in versions[version]['evaluation_metrics'].items():
                if values:
                    versions[version]['evaluation_metrics'][metric] = sum(values) / len(values)
        
        # Calculate overall averages for evaluation metrics
        evaluation_metrics = {}
        for metric, values in all_metrics.items():
            if values:
                evaluation_metrics[metric] = sum(values) / len(values)
        
        return {
            'agent': agent_name,
            'total_sessions': total_sessions,
            'average_score': average_score,
            'by_version': versions,
            'score_distribution': score_distribution,
            'evaluation_metrics': evaluation_metrics
        }
    
    def get_evaluation_rubric(self) -> Dict[str, str]:
        """
        Get the evaluation rubric used for prompt evaluation
        
        Returns:
            Dictionary containing evaluation categories and their descriptions
        """
        return EVALUATION_RUBRIC
    
    def get_improvement_recommendations(self, agent_name: str) -> List[str]:
        """
        Generate improvement recommendations based on feedback
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of improvement recommendations
        """
        feedback = self.get_feedback(agent_name)
        performance = self.get_prompt_performance(agent_name)
        
        if not feedback or performance['total_sessions'] < 3:
            return ["Not enough feedback to generate improvement recommendations."]
        
        recommendations = []
        
        # Check overall score
        if performance['average_score'] < 3.5:
            recommendations.append("The prompt's overall performance is below average. Consider a major revision.")
        
        # Check evaluation metrics
        eval_metrics = performance['evaluation_metrics']
        for metric, score in eval_metrics.items():
            if score < 3.0:
                metric_description = EVALUATION_RUBRIC.get(metric, metric)
                recommendations.append(f"Low score in '{metric}' ({score:.1f}/5). Consider improving: {metric_description}")
        
        # Check for consistency
        if len(performance['by_version']) > 1:
            versions = list(performance['by_version'].keys())
            latest_version = versions[-1]  # Assume versions are added in chronological order
            latest_score = performance['by_version'][latest_version]['average_score']
            
            prev_version = versions[-2]
            prev_score = performance['by_version'][prev_version]['average_score']
            
            if latest_score < prev_score:
                recommendations.append(f"The latest version ({latest_version}) performs worse than the previous version ({prev_version}). Consider reverting or reviewing recent changes.")
        
        # Add generic recommendation if none found
        if not recommendations:
            recommendations.append("The prompt is performing well. No specific improvements needed.")
        
        return recommendations
    
    def get_langchain_prompt(self, agent_name: str):
        """
        Get a LangChain prompt template from the agent configuration
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            LangChain prompt template
        """
        try:
            from langchain.prompts import ChatPromptTemplate
            from langchain.prompts.chat import SystemMessage, HumanMessagePromptTemplate
        except ImportError:
            raise ImportError("LangChain is not installed. Please install it using `pip install langchain`")
        
        config = self.load_prompt(agent_name)
        system_message = config.get('dynamic_prompt_prefix', '')
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}")
        ])


def get_prompt_manager(prompt_dir: str = None, history_dir: str = None) -> PromptManager:
    """Helper function to get a PromptManager instance"""
    return PromptManager(prompt_dir, history_dir) 