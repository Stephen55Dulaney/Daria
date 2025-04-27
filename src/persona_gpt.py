"""
Persona generation module using Thesia, the Persona Architect GPT.
"""
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv
from .thesia_resources import get_complete_system_prompt

# Load environment variables
load_dotenv()

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

def generate_persona_from_interviews(
    interview_texts: List[str],
    project_name: str,
    model: str = "gpt-4"
) -> Dict[str, Any]:
    """
    Generate a persona from a list of interview transcripts.
    
    Args:
        interview_texts (List[str]): List of interview transcripts
        project_name (str): Name of the project
        model (str): Model to use for generation (default: gpt-4)
        
    Returns:
        Dict[str, Any]: Generated persona data
    """
    try:
        # Combine interview texts with clear separation
        combined_text = "\n\n---INTERVIEW SEPARATOR---\n\n".join(interview_texts)
        
        # Create system message with instructions
        system_message = f"""You are Thesia, an expert UX Research Assistant specializing in persona creation.
{PERSONA_ARCHITECT_SYSTEM_PROMPT}

Your task is to analyze the provided interview transcripts and create a detailed persona that represents the key patterns and insights found across the interviews.

The persona should follow this exact JSON structure:
{PERSONA_JSON_TEMPLATE}

Important guidelines:
1. Focus on patterns and themes that appear across multiple interviews
2. Use direct quotes from the interviews to support your insights
3. Make the persona specific and actionable
4. Ensure all fields in the JSON structure are filled out
5. Keep the summary concise (under 600 characters)
6. Make the image prompt detailed and specific
7. Include 3-5 items for each list (goals, pain points, etc.)"""

        if model == "claude-3.7-sonnet":
            import boto3
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            region = 'us-east-2'
            model_arn = 'arn:aws:bedrock:us-east-2:522814696964:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
            if not aws_access_key or not aws_secret_key:
                logger.error("AWS credentials not found for Bedrock call, falling back to GPT-4")
                model = "gpt-4"  # fallback
            else:
                bedrock_runtime = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                user_prompt = f"Project: {project_name}\n\nInterview Transcripts:\n\n{combined_text}"
                messages = [{"role": "user", "content": user_prompt}]
                body = json.dumps({
                    "messages": messages,
                    "system": system_message,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "top_p": 1,
                    "anthropic_version": "bedrock-2023-05-31"
                })
                try:
                    response = bedrock_runtime.invoke_model(
                        body=body,
                        modelId=model_arn,
                        accept="application/json",
                        contentType="application/json"
                    )
                    response_body = json.loads(response.get('body').read())
                    content = ''
                    if 'content' in response_body:
                        content_list = response_body['content']
                        if isinstance(content_list, list) and len(content_list) > 0:
                            content = content_list[0].get('text', '')
                    if not content:
                        logger.error("Empty response from Claude 3.7 Sonnet (Bedrock), falling back to GPT-4")
                        model = "gpt-4"  # fallback
                    else:
                        try:
                            persona_data = json.loads(content)
                            # Validate required fields
                            required_fields = [
                                "name", "summary", "image_prompt", "demographics",
                                "background", "goals", "pain_points"
                            ]
                            for field in required_fields:
                                if field not in persona_data:
                                    raise ValueError(f"Missing required field: {field}")
                            return persona_data
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing persona JSON from Claude: {str(e)}. Falling back to GPT-4.")
                            logger.error(f"Raw response: {content}")
                            model = "gpt-4"  # fallback
                except Exception as e:
                    logger.error(f"Error generating persona with Claude 3.7 Sonnet (Bedrock): {str(e)}. Falling back to GPT-4.")
                    model = "gpt-4"  # fallback
        else:
            # Use OpenAI client for OpenAI models
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Project: {project_name}\n\nInterview Transcripts:\n\n{combined_text}"}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={ "type": "json_object" }
            )
            try:
                persona_data = json.loads(response.choices[0].message.content)
                # Validate required fields
                required_fields = [
                    "name", "summary", "image_prompt", "demographics",
                    "background", "goals", "pain_points"
                ]
                for field in required_fields:
                    if field not in persona_data:
                        raise ValueError(f"Missing required field: {field}")
                return persona_data
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing persona JSON: {str(e)}")
                logger.error(f"Raw response: {response.choices[0].message.content}")
                raise
    except Exception as e:
        logger.error(f"Error generating persona: {str(e)}")
        raise 