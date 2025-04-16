"""
Google AI integration module for persona generation.
"""
import os
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

class GeminiPersonaGenerator:
    def __init__(self, api_key: str = None):
        """Initialize Gemini Pro model for persona generation."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable.")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-pro')
        logger.info("Initialized Gemini Pro model")
        
    def generate_persona(self, interviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a persona using Gemini Pro model.
        
        Args:
            interviews: List of interview data objects
            
        Returns:
            dict: Generated persona data
        """
        # Create the prompt with the same structure as our GPT version
        prompt = self._create_prompt(interviews)
        
        try:
            # Generate the response
            response = self.model.generate_content(prompt)
            
            # Parse the JSON response
            try:
                persona_data = json.loads(response.text)
                return persona_data
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Gemini response as JSON: {e}")
                raise ValueError(f"Invalid JSON response from Gemini: {e}")
                
        except Exception as e:
            logger.error(f"Error generating persona with Gemini: {e}")
            raise
            
    def _create_prompt(self, interviews: List[Dict[str, Any]]) -> str:
        """Create a structured prompt for persona generation."""
        prompt = """You are Thesia, an expert UX researcher specializing in creating evidence-based user personas. Your task is to analyze these interviews and create a detailed, nuanced persona that feels like a real person.

CORE PRINCIPLES:
1. Base ALL insights on direct evidence from the interviews
2. Focus on understanding the user's goals, motivations, and challenges
3. Look for patterns in behaviors and needs
4. Support every insight with relevant quotes
5. Create a persona that feels authentic and nuanced

ANALYSIS APPROACH:
1. First, identify the user's primary goals and motivations
2. Then, analyze their behaviors and habits
3. Next, understand their pain points and challenges
4. Finally, identify opportunities to help them

Please create a comprehensive persona and return it as a JSON object with the following structure:

{
    "demographics": {
        "age_range": "Age range",
        "gender": "Gender",
        "occupation": "Occupation",
        "location": "Location",
        "education": "Education level"
    },
    "goals": [
        {
            "goal": "Primary goal",
            "motivation": "Why this goal is important",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        },
        {
            "goal": "Secondary goal",
            "motivation": "Why this goal is important",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "behaviors": [
        {
            "behavior": "Specific behavior",
            "frequency": "How often this occurs",
            "context": "When/where this happens",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        },
        {
            "behavior": "Another behavior",
            "frequency": "How often this occurs",
            "context": "When/where this happens",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "pain_points": [
        {
            "pain_point": "Description of the pain point",
            "impact": "How it affects the user",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        },
        {
            "pain_point": "Another pain point",
            "impact": "How it affects the user",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "needs": [
        {
            "need": "Specific need",
            "priority": "High, Medium, or Low",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        },
        {
            "need": "Another need",
            "priority": "High, Medium, or Low",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "preferences": [
        {
            "preference": "Specific preference",
            "reason": "Why this preference exists",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        },
        {
            "preference": "Another preference",
            "reason": "Why this preference exists",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "opportunities": [
        {
            "opportunity": "Design or product opportunity",
            "impact": "Potential impact for the user",
            "implementation": "Suggestion for implementation"
        }
    ],
    "technology": {
        "comfort_level": "Technical proficiency level",
        "devices": ["Device 1", "Device 2"],
        "software": ["Software 1", "Software 2"],
        "supporting_quotes": ["Quote 1", "Quote 2"]
    },
    "metadata": {
        "interview_dates": ["Date 1", "Date 2"],
        "interview_types": ["Type 1", "Type 2"],
        "researcher_notes": "Any additional context from researchers"
    }
}

Interview Data:
"""
        # Add interview data to the prompt
        for interview in interviews:
            prompt += f"\nInterview from {interview.get('date', 'unknown date')}:\n"
            prompt += f"Type: {interview.get('interview_type', 'unknown type')}\n"
            prompt += f"Researcher: {interview.get('researcher', {}).get('name', 'unknown')}\n"
            prompt += f"Transcript: {interview.get('transcript', '')}\n"
            prompt += f"Analysis: {interview.get('analysis', '')}\n"
            
        return prompt 