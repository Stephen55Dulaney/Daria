"""
Discovery GPT module for handling UX research project planning conversations.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import traceback

logger = logging.getLogger(__name__)

class DiscoveryGPT:
    def __init__(self, openai_client):
        self.client = openai_client
        self.conversation_state = {}
        
    def get_system_prompt(self) -> str:
        return """You are a UX Research Planning Assistant, trained in Deloitte's Customer Practice methodology. 
        Your role is to help plan UX discovery projects by gathering information through conversation.
        
        Follow these guidelines:
        1. Ask one question at a time
        2. Use natural, conversational language
        3. Follow Deloitte's discovery framework stages in order:
           - Project Context (name, description, background)
           - Industry Context (sector, market conditions)
           - Research Objectives (goals, questions to answer)
           - Stakeholder Identification (roles, involvement)
           - Timeline Planning (start, end, milestones)
           - Methodology Selection (interview types, analysis methods)
        4. Validate responses before moving to next stage
        5. Store key information for the final project plan
        
        Required information to gather:
        - Project name and description
        - Industry context and sector
        - Primary research objectives (3-5)
        - Key stakeholders (2-5)
        - Timeline constraints
        - Preferred research methods
        
        Format your responses conversationally but maintain structure in the stored data.
        After each user response, determine which stage we're in and what information is still needed.
        Only move to the next stage when you have all required information for the current stage."""

    async def process_message(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a message in the discovery conversation.
        
        Args:
            message: The user's message
            conversation_history: List of previous messages
            
        Returns:
            Dict containing:
            - response: Assistant's response
            - isComplete: Whether the discovery process is complete
            - project: Project data if complete
        """
        try:
            logger.info(f"Processing message: {message}")
            logger.info(f"Conversation history length: {len(conversation_history)}")
            
            # Format conversation for the LLM
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                *[{
                    "role": m["role"],
                    "content": m["content"]
                } for m in conversation_history],
                {"role": "user", "content": message}
            ]
            
            # Get response from GPT
            logger.info("Sending request to GPT-4")
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            logger.info(f"Received response from GPT-4: {assistant_message[:100]}...")
            
            # Check if we have all required information
            is_complete = self._check_completion(conversation_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_message}
            ])
            
            result = {
                "response": assistant_message,
                "isComplete": is_complete,
            }
            
            # If complete, generate project data
            if is_complete:
                logger.info("Conversation complete, generating project data")
                project_data = await self._generate_project_data(
                    conversation_history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": assistant_message}
                    ]
                )
                result["project"] = project_data
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
            
    def _check_completion(self, conversation: List[Dict[str, Any]]) -> bool:
        """Check if we have gathered all required information."""
        try:
            required_info = {
                "project_name": False,
                "industry": False,
                "objectives": False,
                "stakeholders": False,
                "timeline": False
            }
            
            # Analyze conversation to check for required information
            conversation_text = " ".join([m["content"].lower() for m in conversation])
            
            # More sophisticated checks for each requirement
            if any(phrase in conversation_text for phrase in ["project name", "project is called", "name of the project"]):
                required_info["project_name"] = True
                
            if any(phrase in conversation_text for phrase in ["industry", "sector", "market"]):
                required_info["industry"] = True
                
            if any(phrase in conversation_text for phrase in ["objective", "goal", "aim", "purpose"]):
                required_info["objectives"] = True
                
            if any(phrase in conversation_text for phrase in ["stakeholder", "participant", "user", "client", "team member"]):
                required_info["stakeholders"] = True
                
            if any(phrase in conversation_text for phrase in ["timeline", "deadline", "duration", "schedule", "start date", "end date"]):
                required_info["timeline"] = True
                
            completion_status = all(required_info.values())
            logger.info(f"Completion check: {required_info}")
            return completion_status
            
        except Exception as e:
            logger.error(f"Error in completion check: {str(e)}")
            return False
            
    async def _generate_project_data(
        self, 
        conversation: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate structured project data from the conversation."""
        try:
            # Ask GPT to structure the conversation data
            messages = [
                {
                    "role": "system",
                    "content": """Extract and structure the project information from the conversation.
                    Return a JSON object with the following structure:
                    {
                        "name": "Project name",
                        "industry": "Industry name",
                        "objectives": ["objective 1", "objective 2"],
                        "stakeholders": [
                            {
                                "name": "Stakeholder name/role",
                                "role": "Role description",
                                "involvement": "Level of involvement"
                            }
                        ],
                        "timeline": {
                            "start_date": "YYYY-MM-DD",
                            "end_date": "YYYY-MM-DD",
                            "milestones": [
                                {
                                    "name": "Milestone name",
                                    "date": "YYYY-MM-DD",
                                    "deliverables": ["deliverable 1"]
                                }
                            ]
                        }
                    }
                    
                    Guidelines:
                    1. Extract actual values from the conversation
                    2. Use reasonable defaults for dates if specific dates aren't mentioned
                    3. Ensure all required fields are present
                    4. Format dates as YYYY-MM-DD
                    5. Include at least one milestone
                    """
                },
                *[{
                    "role": m["role"],
                    "content": m["content"]
                } for m in conversation],
                {
                    "role": "user",
                    "content": "Please structure the project information from our conversation."
                }
            ]
            
            logger.info("Generating structured project data")
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0,
                max_tokens=1000
            )
            
            # Parse the response as JSON
            response_text = response.choices[0].message.content
            logger.info(f"Received structured data response: {response_text[:100]}...")
            
            project_data = json.loads(response_text)
            
            # Add generated ID and creation timestamp
            project_data["id"] = str(uuid.uuid4())
            project_data["created_at"] = datetime.now().isoformat()
            
            logger.info(f"Successfully generated project data with ID: {project_data['id']}")
            return project_data
            
        except Exception as e:
            logger.error(f"Error generating project data: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise 