"""
Prompt Generator for CursorAI.

This module handles the generation of structured prompts for CursorAI based on
research data stored in the DARIA database.
"""

import logging
from typing import Dict, List, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptGenerator:
    """
    Class for generating structured prompts for CursorAI based on research data.
    """
    
    def __init__(self, db_interface=None):
        """
        Initialize the PromptGenerator.
        
        Args:
            db_interface: Interface to the database modules (can be None for testing).
        """
        self.db = db_interface
    
    def generate_cursor_prompt(self, opportunity_id: str, persona_id: Optional[str] = None,
                               user_story_ids: Optional[List[str]] = None) -> Dict:
        """
        Generate a complete structured prompt for CursorAI based on an opportunity.
        
        Args:
            opportunity_id: ID of the opportunity to generate a prompt for.
            persona_id: Optional ID of the persona to include.
            user_story_ids: Optional list of user story IDs to include.
            
        Returns:
            Dict containing the generated prompt and metadata.
        """
        # Get opportunity data
        opportunity = self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError(f"Opportunity with ID {opportunity_id} not found.")
        
        # Get persona data if provided
        persona = None
        if persona_id:
            persona = self._get_persona(persona_id)
        
        # Get user stories if provided
        user_stories = []
        if user_story_ids:
            for story_id in user_story_ids:
                story = self._get_user_story(story_id)
                if story:
                    user_stories.append(story)
        
        # Get insights related to the opportunity
        insights = self._get_insights_for_opportunity(opportunity_id)
        
        # Generate the prompt content
        prompt_content = self._format_prompt(opportunity, persona, user_stories, insights)
        
        # Create metadata
        metadata = {
            "opportunity_id": opportunity_id,
            "persona_id": persona_id,
            "user_story_ids": user_story_ids,
            "insight_count": len(insights)
        }
        
        return {
            "prompt_content": prompt_content,
            "metadata": metadata
        }
    
    def _get_opportunity(self, opportunity_id: str) -> Optional[Dict]:
        """
        Get opportunity data from the database.
        
        Args:
            opportunity_id: ID of the opportunity to retrieve.
            
        Returns:
            Opportunity data or None if not found.
        """
        if self.db and hasattr(self.db, 'opportunities'):
            return self.db.opportunities.get_opportunity(opportunity_id)
        
        # Return mock data for testing
        return {
            "opportunity_id": opportunity_id,
            "title": "Improve childcare provider search experience",
            "description": "Users struggle to find local childcare options they trust.",
            "impacted_persona": "working_parent",
            "priority_score": 85,
            "sprint_id": "sprint_123"
        }
    
    def _get_persona(self, persona_id: str) -> Optional[Dict]:
        """
        Get persona data from the database.
        
        Args:
            persona_id: ID of the persona to retrieve.
            
        Returns:
            Persona data or None if not found.
        """
        if self.db and hasattr(self.db, 'personas'):
            return self.db.personas.get_persona(persona_id)
        
        # Return mock data for testing
        return {
            "persona_id": persona_id,
            "name": "Time-pressed Parent",
            "description": "Working parents with limited digital literacy who need childcare solutions",
            "demographics": {
                "age_range": "30-45",
                "occupation": "Full-time professional",
                "tech_literacy": "Moderate"
            },
            "pain_points": [
                "Limited time to research options",
                "Concerns about safety and quality",
                "Difficulty comparing options efficiently"
            ]
        }
    
    def _get_user_story(self, story_id: str) -> Optional[Dict]:
        """
        Get user story data from the database.
        
        Args:
            story_id: ID of the user story to retrieve.
            
        Returns:
            User story data or None if not found.
        """
        if self.db and hasattr(self.db, 'agile_artifacts'):
            return self.db.agile_artifacts.get_artifact(story_id)
        
        # Return mock data for testing
        return {
            "artifact_id": story_id,
            "type": "user_story",
            "title": "Find trusted childcare providers",
            "description": "As a working parent, I want to view nearby trusted childcare providers so that I can choose safe options quickly.",
            "acceptance_criteria": [
                "Show providers within 5 miles by default",
                "Display ratings prominently",
                "Allow filtering by availability"
            ],
            "opportunity_id": "opportunity_456"
        }
    
    def _get_insights_for_opportunity(self, opportunity_id: str) -> List[Dict]:
        """
        Get research insights related to an opportunity.
        
        Args:
            opportunity_id: ID of the opportunity to get insights for.
            
        Returns:
            List of insight data related to the opportunity.
        """
        if self.db and hasattr(self.db, 'insights'):
            return self.db.insights.get_insights_by_opportunity(opportunity_id)
        
        # Return mock data for testing
        return [
            {
                "insight_id": "insight_1",
                "description": "Users feel overwhelmed by long forms and complex filtering options",
                "source_session_id": "session_123",
                "sentiment": "negative",
                "opportunity_id": opportunity_id
            },
            {
                "insight_id": "insight_2",
                "description": "Users trust peer reviews more than certification badges",
                "source_session_id": "session_124",
                "sentiment": "positive",
                "opportunity_id": opportunity_id
            },
            {
                "insight_id": "insight_3",
                "description": "Users want to see availability information upfront",
                "source_session_id": "session_125",
                "sentiment": "neutral",
                "opportunity_id": opportunity_id
            }
        ]
    
    def _format_prompt(self, opportunity: Dict, persona: Optional[Dict],
                      user_stories: List[Dict], insights: List[Dict]) -> str:
        """
        Format the prompt content based on the provided data.
        
        Args:
            opportunity: Opportunity data.
            persona: Persona data or None.
            user_stories: List of user story data.
            insights: List of insight data.
            
        Returns:
            Formatted prompt content as a string.
        """
        # Format target user section
        target_user = "[No specific target user identified]"
        if persona:
            target_user = persona.get('description', persona.get('name', target_user))
        
        # Format problem summary
        problem_summary = opportunity.get('description', "")
        
        # Format user story section
        user_story_text = ""
        if user_stories:
            story = user_stories[0]
            user_story_text = story.get('description', "")
        else:
            user_story_text = f"As a user impacted by '{opportunity.get('title', '')}', I want a solution that addresses {problem_summary} so that I can achieve my goals more effectively."
        
        # Format insights section
        insights_text = ""
        for i, insight in enumerate(insights[:5]):  # Limit to top 5 insights
            insights_text += f"- {insight.get('description', '')}\n"
        
        if not insights_text:
            insights_text = "- [No specific research insights available]"
        
        # Format ethical considerations
        ethical_considerations = """- Respect privacy by avoiding unnecessary data collection.
- Ensure design is usable for users with varying levels of ability and tech literacy.
- Avoid bias in recommendation algorithms and presentation.
- Provide clear consent mechanisms for any data sharing."""
        
        # Build the complete prompt
        prompt = f"""Design a user interface prototype based on the following research-based opportunity:

**Target User:** {target_user}

**Problem Summary:** {problem_summary}

**User Story:**
{user_story_text}

**Key Insights from Research:**
{insights_text}

**Ethical Considerations:**
{ethical_considerations}

**Requested Deliverables:**
- A wireframe or low-fidelity UI sketch that addresses the core user needs
- Include core components that directly address the identified insights
- Design should support multiple platforms/devices with focus on accessibility
- Consider the entire user journey, not just individual screens

Generate the design using Figma-compatible format if possible, and return the code or markup that can be rendered by React or HTML/CSS.
"""
        return prompt
    
    def save_prompt_to_database(self, opportunity_id: str, prompt_data: Dict,
                               prompt_type: str = "ui_design") -> Dict:
        """
        Save a generated prompt to the database.
        
        Args:
            opportunity_id: ID of the opportunity this prompt is for.
            prompt_data: Data returned from generate_cursor_prompt.
            prompt_type: Type of prompt (e.g., 'ui_design', 'code_implementation').
            
        Returns:
            The saved prompt data from the database.
        """
        if self.db and hasattr(self.db, 'cursor_prompts'):
            return self.db.cursor_prompts.create_prompt(
                opportunity_id=opportunity_id,
                prompt_content=prompt_data['prompt_content'],
                prompt_type=prompt_type,
                metadata=prompt_data['metadata']
            )
        
        # For testing without a database
        return {
            "prompt_id": "mock_prompt_id",
            "opportunity_id": opportunity_id,
            "prompt_content": prompt_data['prompt_content'],
            "prompt_type": prompt_type,
            "generated_at": "2023-01-01T00:00:00",
            "status": "created",
            "metadata": prompt_data['metadata']
        } 