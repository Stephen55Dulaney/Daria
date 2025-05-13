import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import for OpenAI API
import openai
from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryCompanionService:
    """Service to handle Daria's memory companion functionality with LLM integration"""
    
    def __init__(self, llm_provider: str = "openai", model: str = "gpt-4o-mini"):
        """
        Initialize the memory companion service
        
        Args:
            llm_provider: The LLM provider to use ('openai' or 'anthropic')
            model: The specific model to use
        """
        self.llm_provider = llm_provider
        self.model = model
        self.project_data_file = "data/daria_memory.json"
        
        # Load API keys from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if self.llm_provider == "openai" and not self.openai_api_key:
            logger.warning("OpenAI API key not found in environment variables")
            
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            logger.warning("Anthropic API key not found in environment variables")
        
        # Ensure project data directory exists
        os.makedirs(os.path.dirname(self.project_data_file), exist_ok=True)
        
        # Load or create project data
        self.project_data = self._load_project_data()

    def _load_project_data(self) -> Dict[str, Any]:
        """Load project data from file or create default data if it doesn't exist"""
        try:
            with open(self.project_data_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default project data
            default_data = {
                "name": "Daria Interview Tool",
                "overview": "An AI-powered research interviewing platform with text-to-speech and speech-to-text capabilities for conducting and analyzing user interviews.",
                "currentSprint": "Database Implementation and AWS Deployment (Phase 2)",
                "timeline": [
                    {"date": "May 6, 2025", "event": "Released RC2 with improved interview flow and LangChain integration"},
                    {"date": "May 8, 2025", "event": "Created project journal system for continuity between sessions"},
                    {"date": "May 10, 2025", "event": "Started database schema implementation for core tables"},
                    {"date": "May 12, 2025", "event": "Began testing AWS deployment with simple components"}
                ],
                "opportunities": [
                    {"id": "OPP-001", "title": "Persistent Database for Interview Data", "priority": "High", 
                     "description": "Implement structured database to replace JSON file storage"},
                    {"id": "OPP-002", "title": "AWS Deployment Strategy", "priority": "Medium", 
                     "description": "Create deployment process for AWS with proper security and scaling"},
                    {"id": "OPP-003", "title": "Memory Companion Feature", "priority": "Medium", 
                     "description": "Implement Daria as project companion with persistent memory"},
                    {"id": "OPP-004", "title": "Sprint Engine Capabilities", "priority": "Low", 
                     "description": "Add full agile artifact generation for UX research sprints"}
                ],
                "conversation_history": []
            }
            
            # Save default data
            with open(self.project_data_file, 'w') as f:
                json.dump(default_data, f, indent=2)
                
            return default_data
    
    def _save_project_data(self):
        """Save project data to file"""
        with open(self.project_data_file, 'w') as f:
            json.dump(self.project_data, f, indent=2)
    
    def add_timeline_event(self, event: str) -> Dict[str, Any]:
        """Add a new event to the project timeline"""
        today = datetime.now().strftime("%b %d, %Y")
        new_event = {"date": today, "event": event}
        self.project_data["timeline"].append(new_event)
        self._save_project_data()
        return new_event
    
    def add_opportunity(self, title: str, description: str, priority: str = "Medium") -> Dict[str, Any]:
        """Add a new opportunity to the project"""
        # Generate a new opportunity ID
        opp_id = f"OPP-{len(self.project_data['opportunities']) + 1:03d}"
        
        new_opp = {
            "id": opp_id,
            "title": title,
            "description": description,
            "priority": priority
        }
        
        self.project_data["opportunities"].append(new_opp)
        self._save_project_data()
        return new_opp
    
    def update_sprint(self, sprint_name: str) -> Dict[str, Any]:
        """Update the current sprint"""
        self.project_data["currentSprint"] = sprint_name
        self._save_project_data()
        return {"currentSprint": sprint_name}
    
    def get_project_data(self) -> Dict[str, Any]:
        """Get all project data"""
        return self.project_data
    
    def add_conversation_entry(self, user_message: str, daria_response: str):
        """Add a conversation entry to the history"""
        if "conversation_history" not in self.project_data:
            self.project_data["conversation_history"] = []
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "daria_response": daria_response
        }
        
        self.project_data["conversation_history"].append(entry)
        
        # Keep only the last 20 conversation entries to prevent the context from growing too large
        if len(self.project_data["conversation_history"]) > 20:
            self.project_data["conversation_history"] = self.project_data["conversation_history"][-20:]
            
        self._save_project_data()
    
    def _create_system_prompt(self) -> str:
        """Create a system prompt for the LLM that includes Daria's character and project context"""
        return f"""You are Daria, an AI project companion for the Daria Interview Tool project.
You have a friendly, helpful personality and maintain continuity across different user sessions by remembering the project's history and status.

Your project memory contains the following information:

PROJECT NAME: {self.project_data["name"]}
PROJECT OVERVIEW: {self.project_data["overview"]}
CURRENT SPRINT: {self.project_data["currentSprint"]}

RECENT TIMELINE:
{self._format_timeline_for_prompt()}

IDENTIFIED OPPORTUNITIES:
{self._format_opportunities_for_prompt()}

GUIDELINES:
1. Always maintain your identity as Daria, the project companion
2. Reference specific details from the project memory to show continuity
3. Be proactive in suggesting next steps based on the current sprint and opportunities
4. If asked about something not in your memory, acknowledge that it's not in your records
5. When discussing technical aspects, be specific and reference the actual components of the Daria Interview Tool
6. Use a friendly, professional tone that balances technical expertise with accessibility

Answer questions about the project status, help the user decide what to work on next, and maintain context between sessions.
"""

    def _format_timeline_for_prompt(self) -> str:
        """Format the timeline events for inclusion in the prompt"""
        timeline_str = ""
        for event in self.project_data["timeline"][-5:]:  # Only include the 5 most recent events
            timeline_str += f"• {event['date']}: {event['event']}\n"
        return timeline_str
    
    def _format_opportunities_for_prompt(self) -> str:
        """Format the opportunities for inclusion in the prompt"""
        opps_str = ""
        for opp in self.project_data["opportunities"]:
            opps_str += f"• {opp['id']}: {opp['title']} ({opp['priority']} Priority) - {opp['description']}\n"
        return opps_str
    
    def _format_conversation_history(self) -> List[Dict[str, str]]:
        """Format the conversation history for the LLM"""
        messages = [{"role": "system", "content": self._create_system_prompt()}]
        
        # Add conversation history
        if "conversation_history" in self.project_data:
            for entry in self.project_data["conversation_history"]:
                messages.append({"role": "user", "content": entry["user_message"]})
                messages.append({"role": "assistant", "content": entry["daria_response"]})
                
        return messages
    
    async def get_response(self, user_message: str, provider: str = None, model: str = None) -> str:
        """Get a response from the LLM based on the user's message and project context"""
        # Use the provided provider and model if specified, otherwise use the default
        llm_provider = provider if provider else self.llm_provider
        model_name = model if model else self.model
        
        try:
            messages = self._format_conversation_history()
            messages.append({"role": "user", "content": user_message})
            
            if llm_provider == "openai":
                client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800
                )
                daria_response = response.choices[0].message.content
                
            elif llm_provider == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=self.anthropic_api_key)
                
                # Format messages for Claude
                system_prompt = messages[0]["content"]
                conversation = messages[1:]
                
                formatted_msgs = []
                for msg in conversation:
                    if msg["role"] == "user":
                        formatted_msgs.append({"role": "user", "content": msg["content"]})
                    else:
                        formatted_msgs.append({"role": "assistant", "content": msg["content"]})
                
                response = await client.messages.create(
                    model=model_name,
                    system=system_prompt,
                    messages=formatted_msgs,
                    max_tokens=800
                )
                daria_response = response.content[0].text
                
            else:
                daria_response = "I'm sorry, but I'm currently offline or the configured LLM provider is not supported."
            
            # Store the conversation
            self.add_conversation_entry(user_message, daria_response)
            
            return daria_response
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            return f"I'm having trouble connecting to my memory systems. Please try again later. (Error: {str(e)})"


# Create Flask Blueprint
memory_companion_bp = Blueprint('memory_companion', __name__)
memory_companion_service = MemoryCompanionService()


@memory_companion_bp.route('/api/memory_companion/chat', methods=['POST'])
def chat():
    """API endpoint for chatting with Daria Memory Companion"""
    data = request.json
    user_message = data.get('message', '')
    provider = data.get('provider', 'openai')
    model = data.get('model', 'gpt-4o-mini')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Use asyncio.run to run the async function in a synchronous context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(memory_companion_service.get_response(user_message, provider, model))
    finally:
        loop.close()
    
    return jsonify({'response': response})


@memory_companion_bp.route('/api/memory_companion/project_data', methods=['GET'])
def get_project_data():
    """API endpoint to get project data for the frontend"""
    return jsonify(memory_companion_service.get_project_data())


@memory_companion_bp.route('/api/memory_companion/timeline', methods=['POST'])
def add_timeline_event():
    """API endpoint to add a timeline event"""
    data = request.json
    event = data.get('event', '')
    
    if not event:
        return jsonify({'error': 'No event provided'}), 400
    
    new_event = memory_companion_service.add_timeline_event(event)
    return jsonify(new_event)


@memory_companion_bp.route('/api/memory_companion/opportunity', methods=['POST'])
def add_opportunity():
    """API endpoint to add an opportunity"""
    data = request.json
    title = data.get('title', '')
    description = data.get('description', '')
    priority = data.get('priority', 'Medium')
    
    if not title or not description:
        return jsonify({'error': 'Title and description are required'}), 400
    
    new_opp = memory_companion_service.add_opportunity(title, description, priority)
    return jsonify(new_opp)


@memory_companion_bp.route('/api/memory_companion/sprint', methods=['PUT'])
def update_sprint():
    """API endpoint to update the current sprint"""
    data = request.json
    sprint_name = data.get('sprint', '')
    
    if not sprint_name:
        return jsonify({'error': 'Sprint name is required'}), 400
    
    result = memory_companion_service.update_sprint(sprint_name)
    return jsonify(result)


@memory_companion_bp.route('/api/memory_companion/test', methods=['GET'])
def test_api():
    """Test endpoint to verify the Memory Companion API is working"""
    return jsonify({
        'status': 'success',
        'message': 'Memory Companion API is operational',
        'version': '1.0.0'
    }) 