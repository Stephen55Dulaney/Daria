"""
Persona generation module using Thesia, the Persona Architect GPT.
"""
import json
import logging
from typing import List, Dict, Any
from .thesia_resources import get_complete_system_prompt

# Configure logger
logger = logging.getLogger(__name__)

# Use the complete system prompt from thesia_resources
PERSONA_ARCHITECT_SYSTEM_PROMPT = get_complete_system_prompt()

# Enhanced JSON template for the persona
PERSONA_JSON_TEMPLATE = """{
    "name": "Persona name (with role)",
    "summary": "Concise summary background (less than 600 characters)",
    "image_prompt": "Detailed prompt for AI image generation",
    "demographics": {
        "age_range": "Age range",
        "gender": "Gender",
        "occupation": "Occupation",
        "location": "Location",
        "education": "Education level"
    },
    "background": "More detailed background and context",
    "goals": [
        {
            "goal": "Primary goal",
            "motivation": "Why this goal is important",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "pain_points": [
        {
            "pain_point": "Description of the pain point",
            "impact": "How it affects the user",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "behaviors": [
        {
            "behavior": "Specific behavior",
            "frequency": "How often this occurs",
            "context": "When/where this happens",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "technology": {
        "devices": ["Device 1", "Device 2"],
        "software": ["Software 1", "Software 2"],
        "comfort_level": "Description of tech comfort level",
        "supporting_quotes": ["Quote 1", "Quote 2"]
    },
    "needs": [
        {
            "need": "Specific need",
            "priority": "High, Medium, or Low",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "preferences": [
        {
            "preference": "Specific preference",
            "reason": "Why this preference exists",
            "supporting_quotes": ["Quote 1", "Quote 2"]
        }
    ],
    "key_quotes": ["Important quote 1", "Important quote 2"],
    "opportunities": [
        {
            "opportunity": "Design or product opportunity",
            "impact": "Potential impact for the user",
            "implementation": "Suggestion for implementation"
        }
    ]
}"""

def generate_persona_architect_prompt(interviews: List[Dict[str, Any]]) -> str:
    """Generate the analysis prompt for Thesia."""
    prompt = f"""You are Thesia, an expert UX researcher specializing in persona creation. Your task is to analyze the following interviews and create a detailed, evidence-based persona.

Focus only on the interviewee's responses, not the interviewer's questions. Extract insights, behaviors, and patterns from what the interviewee actually said.

For each interview, I will provide:
1. Project context
2. Interview metadata
3. Transcript (focusing only on interviewee responses)
4. Analysis (if available)

Please analyze the interviews and generate a detailed persona in the following JSON format:

{PERSONA_JSON_TEMPLATE}

Ensure all insights are supported by direct quotes from the interviewee's responses. Do not include any quotes from the interviewer (Daria)."""

    # Add each interview's data
    for interview in interviews:
        prompt += "\n\nInterview Data:"
        
        # Add project context
        prompt += f"\nProject: {interview.get('project_name', 'Unknown Project')}"
        prompt += f"\nType: {interview.get('interview_type', 'Unknown Type')}"
        
        # Add metadata if available
        metadata = interview.get('metadata', {})
        if metadata:
            prompt += "\nMetadata:"
            for key, value in metadata.items():
                prompt += f"\n- {key}: {value}"
            
            if 'technology' in metadata:
                prompt += "\nTechnology Usage:"
                prompt += f"\n- Primary Device: {metadata['technology'].get('primaryDevice', 'Unknown')}"
                prompt += f"\n- Operating System: {metadata['technology'].get('operatingSystem', 'Unknown')}"
                prompt += f"\n- Browser Preference: {metadata['technology'].get('browserPreference', 'Unknown')}"
                prompt += f"\n- Technical Proficiency: {metadata['technology'].get('technicalProficiency', 'Unknown')}"
        
        # Handle transcript - extract only interviewee responses
        transcript = interview.get('transcript', '')
        if isinstance(transcript, str):
            # Split into lines and filter for interviewee responses
            lines = transcript.split('\n')
            interviewee_responses = []
            for line in lines:
                if line.startswith('You:'):
                    response = line[4:].strip()  # Remove 'You: ' prefix
                    if response and not response.startswith('Daria:'):  # Extra check to ensure no Daria responses
                        interviewee_responses.append(response)
            
            prompt += "\nInterviewee Responses:"
            for response in interviewee_responses:
                prompt += f"\n- {response}"
        else:
            prompt += "\nInterviewee Responses:"
            for message in transcript[:5]:  # Limit to first 5 messages
                if isinstance(message, dict) and message.get('speaker') == 'You':
                    prompt += f"\n- {message.get('text', '')[:100]}..."  # Limit message length
        
        # Handle analysis - limit to first 300 characters
        if 'analysis' in interview:
            analysis = interview['analysis']
            if isinstance(analysis, dict):
                content = analysis.get('content', '')
                prompt += f"\n\nAnalysis: {content[:300]}..."
            else:
                prompt += f"\n\nAnalysis: {str(analysis)[:300]}..."
    
    # Add the JSON template at the end
    prompt += f"""

Please analyze the interviews and generate a detailed persona in the following JSON format:

{PERSONA_JSON_TEMPLATE}

Ensure all insights are supported by quotes from the interviewee's responses only. Do not include any quotes from the interviewer (Daria). Use the metadata provided to inform the persona's demographics and technology usage sections."""
    
    return prompt

def generate_persona_with_architect(openai_client, interviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a persona using Thesia, the Persona Architect GPT.
    
    Args:
        openai_client: OpenAI client instance
        interviews: List of interview data objects
        
    Returns:
        dict: The generated persona data
    """
    analysis_prompt = generate_persona_architect_prompt(interviews)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-0125-preview",  # Use GPT-4-turbo-preview with 128k context length
            messages=[
                {"role": "system", "content": PERSONA_ARCHITECT_SYSTEM_PROMPT},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7
        )
        
        # Extract the response content
        analysis = response.choices[0].message.content
        
        # Log the response for debugging
        logger.info(f"Raw response from GPT: {analysis[:200]}...")  # Log first 200 chars
        
        # Parse the JSON response
        try:
            # Try to find JSON content within the response
            start_idx = analysis.find('{')
            end_idx = analysis.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = analysis[start_idx:end_idx]
                
                # Clean up the JSON string
                json_str = json_str.replace('...', '')  # Remove any ellipsis
                json_str = json_str.replace('\n', ' ')  # Replace newlines with spaces
                
                # Try to parse the cleaned JSON
                try:
                    persona_data = json.loads(json_str)
                    
                    # Validate the persona data structure
                    required_fields = ['name', 'summary', 'demographics', 'technology']
                    for field in required_fields:
                        if field not in persona_data:
                            raise ValueError(f"Missing required field in persona data: {field}")
                    
                    return persona_data
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing cleaned JSON: {str(e)}")
                    logger.error(f"Cleaned JSON string: {json_str[:500]}...")
                    raise ValueError(f"Error parsing JSON response: {str(e)}")
            else:
                raise ValueError("No valid JSON object found in response")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.error(f"Response content: {analysis[:500]}...")  # Log first 500 chars
            raise ValueError(f"Error parsing JSON response: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error generating persona: {str(e)}")
        raise 