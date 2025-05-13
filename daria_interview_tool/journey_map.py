"""
Journey Map Generation Module

This module provides functions to generate structured JSON data for journey maps
based on interview data from the Daria Interview Tool.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from openai import OpenAI
import os
import time
import boto3
from botocore.config import Config

# Configure logging
logger = logging.getLogger(__name__)

def generate_journey_map_json(interviews: List[Dict], project_name: str, model: str = 'gpt-4') -> Dict[str, Any]:
    """
    Generate a journey map as structured JSON based on interview data.
    
    Args:
        interviews: List of interview data dictionaries
        project_name: Name of the project
        model: Model to use for generation ('gpt-4' or 'claude-3.7-sonnet')
        
    Returns:
        Dictionary containing the structured journey map data
    """
    try:
        # Extract relevant content from interviews
        interview_content = []
        for interview in interviews:
            # Extract transcript or relevant chunks
            transcript = interview.get('transcript', '')
            
            # If transcript is empty, try getting from chunks
            if not transcript and 'chunks' in interview:
                transcript = ' '.join([chunk.get('text', '') for chunk in interview.get('chunks', [])])
            
            # Add the transcript to interview content
            if transcript:
                content = {
                    'id': interview.get('id'),
                    'transcript': transcript,
                    'project_name': interview.get('project_name', project_name),
                    'date': interview.get('date', datetime.now().isoformat()),
                }
                interview_content.append(content)
        
        if not interview_content:
            raise ValueError("No valid interview content found")
            
        # Create the prompt for the model
        prompt = create_journey_map_prompt(interview_content, project_name)
        
        # Model info for debugging
        model_info = {
            "model": model,
            "start_time": time.time()
        }
        
        # Call appropriate model based on selection
        if model == 'claude-3.7-sonnet':
            logger.info(f"Using Claude 3.7 Sonnet to generate journey map for project: {project_name}")
            result, model_info = generate_with_claude(prompt, project_name)
        else:
            logger.info(f"Using GPT-4 to generate journey map for project: {project_name}")
            result = generate_with_openai(prompt)
            model_info["end_time"] = time.time()
            model_info["response_time"] = round(model_info["end_time"] - model_info["start_time"], 2)
        
        # Add metadata
        result["id"] = str(uuid.uuid4())
        result["project_name"] = project_name
        result["created_at"] = datetime.now().isoformat()
        result["model_info"] = model_info
        
        # Ensure the journey_map has the required keys with appropriate defaults
        result.setdefault("title", f"Journey Map for {project_name}")
        result.setdefault("projectName", project_name)
        result.setdefault("stages", [])
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating journey map: {str(e)}")
        # Return a basic error structure that won't break the frontend
        return {
            "id": str(uuid.uuid4()),
            "title": f"Journey Map for {project_name}",
            "projectName": project_name,
            "created_at": datetime.now().isoformat(),
            "error": str(e),
            "stages": []
        }

def generate_with_openai(prompt: str) -> Dict[str, Any]:
    """Generate journey map using OpenAI API"""
    try:
        # Initialize OpenAI client with API key from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        client = OpenAI(api_key=api_key)
        
        # Call OpenAI API to generate the journey map structure
        logger.info("Calling OpenAI API to generate journey map")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a UX research expert specializing in journey mapping. Your task is to analyze interview transcripts and create a structured journey map. You MUST return only valid JSON, with no additional text before or after. The JSON structure must exactly match the format provided in the prompt."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5  # Lower temperature for more deterministic output
        )
        logger.info("Successfully received response from OpenAI API")
        
        # Extract and parse the generated JSON
        result = response.choices[0].message.content
        
        try:
            # Try to parse the JSON directly
            journey_map = json.loads(result)
        except json.JSONDecodeError as e:
            # If direct parsing fails, try to clean up the JSON
            logger.warning(f"JSON parsing error: {str(e)}")
            logger.warning("Attempting to fix malformed JSON...")
            
            # Try to extract JSON if it's wrapped in markdown code blocks
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            # Try to find JSON boundaries if the model adds text before/after JSON
            elif "{" in result and "}" in result:
                start_idx = result.find("{")
                end_idx = result.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
            # Try again to parse the cleaned JSON
            try:
                journey_map = json.loads(result)
            except json.JSONDecodeError as e:
                # If it still fails, return an error structure
                logger.error(f"Failed to parse JSON after cleanup: {str(e)}")
                journey_map = {
                    "title": "Error generating journey map",
                    "projectName": "Error",
                    "stages": [],
                    "error": str(e),
                    "raw_response": result[:200] + "..." if len(result) > 200 else result  # Include truncated response for debugging
                }
        
        return journey_map
    except Exception as e:
        logger.error(f"Error in generate_with_openai: {str(e)}")
        raise e

def generate_with_claude(prompt: str, project_name: str) -> tuple:
    """Generate journey map using Claude 3.7 Sonnet via Amazon Bedrock"""
    try:
        # Get AWS credentials from environment variables
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not aws_access_key or not aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # Claude 3.7 Sonnet model config
        region = 'us-east-2'
        model_id = 'arn:aws:bedrock:us-east-2:522814696964:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
        
        # Initialize Bedrock client with increased timeout
        config = Config(
            read_timeout=300,
            connect_timeout=300,
            retries={'max_attempts': 2}
        )
        
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            config=config
        )
        
        # Create system prompt
        system_prompt = """You are a UX research expert specializing in journey mapping. Your task is to analyze interview transcripts and create a structured journey map. 
You MUST return only valid JSON, with no additional text before or after. The JSON structure must exactly match the format provided in the prompt."""
        
        # Create request body
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        body = json.dumps({
            "messages": messages,
            "system": system_prompt,
            "max_tokens": 4000,
            "temperature": 0.5,
            "top_p": 1.0,
            "anthropic_version": "bedrock-2023-05-31"
        })
        
        logger.info(f"Sending request to Claude 3.7 Sonnet for project: {project_name}")
        start_time = time.time()
        
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            body=body, 
            modelId=model_id,
            accept="application/json", 
            contentType="application/json"
        )
        
        end_time = time.time()
        response_time = round(end_time - start_time, 2)
        
        logger.info(f"Received response from Claude 3.7 Sonnet in {response_time} seconds")
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        
        # Extract content
        content = response_body.get('content', [{}])[0].get('text', '')
        
        # Try to parse the JSON
        try:
            # Try to parse the JSON directly
            journey_map = json.loads(content)
        except json.JSONDecodeError as e:
            # If direct parsing fails, try to clean up the JSON
            logger.warning(f"JSON parsing error: {str(e)}")
            logger.warning("Attempting to fix malformed JSON...")
            
            # Try to extract JSON if it's wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            # Try to find JSON boundaries if the model adds text before/after JSON
            elif "{" in content and "}" in content:
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    content = content[start_idx:end_idx]
                
            # Try again to parse the cleaned JSON
            try:
                journey_map = json.loads(content)
            except json.JSONDecodeError as e:
                # If it still fails, return an error structure
                logger.error(f"Failed to parse JSON after cleanup: {str(e)}")
                journey_map = {
                    "title": "Error generating journey map",
                    "projectName": "Error",
                    "stages": [],
                    "error": str(e),
                    "raw_response": content[:200] + "..." if len(content) > 200 else content  # Include truncated response for debugging
                }
        
        # Create model info for debugging
        model_info = {
            "model": "claude-3.7-sonnet",
            "model_id": model_id,
            "response_time": response_time,
            "start_time": start_time,
            "end_time": end_time
        }
        
        return journey_map, model_info
    except Exception as e:
        logger.error(f"Error in generate_with_claude: {str(e)}")
        return {
            "title": f"Error generating journey map with Claude",
            "projectName": project_name,
            "stages": [],
            "error": str(e)
        }, {"model": "claude-3.7-sonnet", "error": str(e)}

def create_journey_map_prompt(interviews: List[Dict], project_name: str) -> str:
    """
    Create a prompt for the OpenAI API to generate a journey map.
    
    Args:
        interviews: List of interview data dictionaries
        project_name: Name of the project
        
    Returns:
        String containing the prompt for the OpenAI API
    """
    prompt = f"""
Analyze the following interview transcripts for the project "{project_name}" and create a detailed journey map.

The journey map should be returned as a JSON object with the following structure:

```json
{{
  "title": "Journey Map for [Project Name]",
  "projectName": "[Project Name]",
  "stages": [
    {{
      "id": "stage-1",
      "stageName": "Stage Name",
      "stageDescription": "Description of this stage",
      "userActions": [
        {{ "action": "Action description", "description": "Details about the action" }}
      ],
      "userGoals": [
        {{ "goal": "Goal description", "description": "Details about the goal" }}
      ],
      "emotions": [
        {{ "name": "Emotion name", "intensity": 7, "description": "Description of the emotion" }}
      ],
      "touchpoints": [
        {{ "name": "Touchpoint name", "description": "Description of the touchpoint" }}
      ],
      "painPoints": [
        {{ 
          "painPoint": "Description of pain point", 
          "impact": "Impact of the pain point",
          "supporting_quotes": ["Quote from interview"]
        }}
      ],
      "needs": [
        {{ 
          "need": "User need", 
          "priority": "High/Medium/Low",
          "supporting_quotes": ["Quote from interview"]
        }}
      ],
      "opportunities": [
        {{ "opportunity": "Improvement opportunity", "impact": "Potential impact" }}
      ]
    }}
  ],
  "experienceCurve": [
    {{ "stage": "Stage Name", "emotion": "Primary emotion", "intensity": 7 }}
  ]
}}
```

For each stage in the journey:
1. Identify the key actions users take
2. Identify their goals and motivations
3. Capture their emotional state (with intensity from 1-10)
4. List relevant touchpoints
5. Document pain points with supporting quotes
6. Identify user needs and their priorities
7. Suggest opportunities for improvement

Interview Transcripts:
"""

    # Add interview transcripts to the prompt
    for i, interview in enumerate(interviews, 1):
        prompt += f"\n\nINTERVIEW {i}:\n"
        prompt += f"Date: {interview.get('date', 'Unknown')}\n"
        
        # Truncate transcript if it's too long
        transcript = interview.get('transcript', '')
        if len(transcript) > 4000:
            prompt += f"{transcript[:4000]}...[transcript truncated for length]"
        else:
            prompt += transcript
    
    # Add final instruction
    prompt += """

Based on these interviews, create a comprehensive journey map following the JSON structure described above.
Make sure to:
1. Identify distinct stages in the user journey
2. Extract concrete actions, goals, emotions, pain points, and needs
3. Use actual quotes from the interviews when available
4. Provide actionable opportunities for improvement
5. Return ONLY valid JSON following exactly the structure provided, without any explanations or markdown
6. Do not include any text before or after the JSON output
"""

    return prompt 