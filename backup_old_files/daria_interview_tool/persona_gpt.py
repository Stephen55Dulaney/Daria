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
import re
import tiktoken # Import tiktoken for accurate token counting
import time
from botocore.config import Config

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

def _get_token_count(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Estimate token count for a given text and model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback for models not in tiktoken
        encoding = tiktoken.get_encoding("cl100k_base") 
    return len(encoding.encode(text))

def _summarize_transcript_for_persona(client: OpenAI, transcript: str, project_name: str, model: str = "gpt-3.5-turbo", max_input_tokens: int = 15000) -> str:
    """Helper function to summarize a single transcript for persona generation, handling long inputs by chunking."""
    if not transcript or len(transcript.strip()) < 50:
        return transcript

    # Estimate base prompt tokens (rough estimate)
    base_prompt_template = f"""Summarize the key points from this interview transcript relevant for creating a user persona for the project '{project_name}'. Focus on:
        - User's primary goals and motivations
        - Major pain points or frustrations mentioned
        - Key behaviors or workflows described
        - Technology usage and comfort level
        - Specific needs or desires expressed
        - Any standout quotes that capture the user's perspective.
        Keep the summary concise.

        Transcript:
        {{transcript_chunk}}

        Concise Summary:"""
    base_tokens = _get_token_count(base_prompt_template.format(transcript_chunk=""), model)
    output_tokens = 300 # Reserved for the output summary
    available_tokens_for_transcript = max_input_tokens - base_tokens - output_tokens

    transcript_tokens = _get_token_count(transcript, model)

    if transcript_tokens <= available_tokens_for_transcript:
        # Transcript fits, summarize directly
        logger.info(f"Transcript fits ({transcript_tokens} tokens), summarizing directly.")
        try:
            summary_prompt = base_prompt_template.format(transcript_chunk=transcript)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=output_tokens
            )
            summary = response.choices[0].message.content.strip()
            logger.info(f"Successfully summarized transcript (length: {len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"Error summarizing transcript (direct): {str(e)}. Returning original.")
            return transcript
    else:
        # Transcript too long, chunk and summarize
        logger.warning(f"Transcript too long ({transcript_tokens} tokens > {available_tokens_for_transcript}), chunking required.")
        chunks = []
        current_chunk = ""
        # Split by paragraph first for more logical breaks
        paragraphs = transcript.split('\n\n')
        for para in paragraphs:
            para_tokens = _get_token_count(para, model)
            current_chunk_tokens = _get_token_count(current_chunk, model)
            
            if current_chunk_tokens + para_tokens <= available_tokens_for_transcript:
                current_chunk += para + "\n\n"
            else:
                # If adding the paragraph exceeds limit, finalize the current chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Start new chunk with the current paragraph (if it fits alone, otherwise it gets skipped - could be improved)
                if para_tokens <= available_tokens_for_transcript:
                    current_chunk = para + "\n\n"
                else:
                     logger.warning(f"Paragraph too long ({para_tokens} tokens), skipping.")
                     current_chunk = "" # Reset chunk if para is too long
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        if not chunks:
            logger.error("Failed to create any valid chunks from the long transcript. Returning original.")
            return transcript

        logger.info(f"Split transcript into {len(chunks)} chunks.")
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i+1}/{len(chunks)}...")
            try:
                summary_prompt = base_prompt_template.format(transcript_chunk=chunk)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.3,
                    max_tokens=output_tokens
                )
                chunk_summary = response.choices[0].message.content.strip()
                chunk_summaries.append(chunk_summary)
                logger.info(f"Chunk {i+1} summarized.")
            except Exception as e:
                logger.error(f"Error summarizing chunk {i+1}: {str(e)}. Skipping chunk.")
                continue
        
        # Combine chunk summaries (could use another LLM call for better coherence, but simple join for now)
        final_summary = "\n\n---\n\n".join(chunk_summaries)
        logger.info(f"Combined {len(chunk_summaries)} chunk summaries into final summary (length: {len(final_summary)} chars).")
        return final_summary

def _synthesize_themes_from_summaries(client: OpenAI, summaries: List[str], project_name: str, model: str = "gpt-4") -> str:
    """Synthesize key themes, goals, pain points, etc., from multiple interview summaries."""
    if not summaries:
        return ""

    combined_summaries = "\n\n---INTERVIEW SUMMARY SEPARATOR---\n\n".join(summaries)
    
    synthesis_prompt = f"""Analyze the following interview summaries for the project '{project_name}'. 
    Identify the key recurring themes, patterns, goals, motivations, pain points, needs, preferences, and behaviors mentioned across these summaries. 
    For each key finding, provide 1-2 brief supporting example quotes *directly from the provided summaries*.
    Organize the output clearly with headings for each category (e.g., ## Key Goals, ## Common Pain Points).
    Be concise and focus only on the most prominent patterns found across multiple summaries.

    Interview Summaries:
    {combined_summaries}

    Synthesized Findings:"""
    
    try:
        # Check if we're using Claude model
        if model == "claude-3.7-sonnet":
            logger.info(f"Using Claude 3.7 Sonnet for theme synthesis")
            # Use Claude for synthesis instead of OpenAI
            system_prompt = """You are an expert UX researcher specializing in synthesizing interview data.
            Your task is to analyze interview summaries and identify key patterns, themes, and insights."""
            
            # Direct approach - don't try to interpret as JSON
            try:
                # Import needed here since AWS/boto3 is optional
                import boto3
                
                # Get AWS credentials
                aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
                aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                
                if not aws_access_key or not aws_secret_key:
                    raise ValueError("AWS credentials not found in environment variables")
                
                # Claude configuration
                region = 'us-east-2'
                model_id = 'arn:aws:bedrock:us-east-2:522814696964:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
                
                # Configure longer timeouts (300 seconds = 5 minutes)
                config = Config(
                    read_timeout=300,
                    connect_timeout=300,
                    retries={'max_attempts': 2}
                )
                
                # Initialize Bedrock client
                bedrock_runtime = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    config=config
                )
                
                # Create request body for a text response, not JSON
                body = json.dumps({
                    "messages": [
                        {"role": "user", "content": synthesis_prompt}
                    ],
                    "system": system_prompt,
                    "max_tokens": 2000,
                    "temperature": 0.5,
                    "top_p": 1.0,
                    "anthropic_version": "bedrock-2023-05-31"
                })
                
                logger.info(f"Sending theme synthesis request to Claude 3.7 Sonnet")
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
                logger.info(f"Received theme synthesis response from Claude in {response_time} seconds")
                
                # Parse the response - this should return Anthropic's standard format
                response_body = json.loads(response.get('body').read())
                
                # Extract content from Claude's response structure
                if 'content' in response_body and len(response_body['content']) > 0:
                    content = response_body['content'][0].get('text', '')
                    if content:
                        logger.info(f"Successfully extracted theme synthesis from Claude (length: {len(content)} chars)")
                        return content
                    else:
                        logger.error("Claude returned empty text content")
                else:
                    logger.error(f"Unexpected Claude response structure: {json.dumps(response_body)[:200]}")
                
                # Log the full raw response for debugging
                logger.error(f"Claude raw response: {json.dumps(response_body)[:500]}")
                return f"Error during Claude synthesis: Unexpected response format"
                
            except Exception as e:
                logger.error(f"Error in direct Claude theme synthesis: {str(e)}")
                return f"Error during Claude synthesis: {str(e)}"
        
        # Original OpenAI implementation for other models
        input_tokens = _get_token_count(synthesis_prompt, model)
        # Check if prompt is already too long before even requesting output
        # Use 8000 as a safer limit than 8192 for gpt-4 base
        if input_tokens > 8000:
             logger.error(f"Synthesis prompt alone ({input_tokens} tokens) exceeds model limit. Cannot synthesize.")
             return f"Error during synthesis: Combined summaries too long for synthesis model."
        # Leave ~500 tokens for synthesis output
        elif input_tokens > 7500:
             logger.warning(f"Synthesis prompt is very long ({input_tokens} tokens). Result might be truncated or fail.")

        response = client.chat.completions.create(
            model=model, 
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.5,
            max_tokens=500  # Further reduced for extreme conciseness
        )
        synthesized_themes = response.choices[0].message.content.strip()
        logger.info(f"Successfully synthesized themes from summaries (length: {len(synthesized_themes)} chars)")
        return synthesized_themes
    except Exception as e:
        logger.error(f"Error synthesizing themes from summaries: {str(e)}")
        return f"Error during synthesis: {str(e)}\n\nFalling back to combined summaries:\n{combined_summaries}"

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
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not client.api_key:
             raise ValueError("OpenAI API key not found.")

        # 1. Summarize each interview transcript (using helper function)
        summarized_texts = [
            _summarize_transcript_for_persona(client, text, project_name)
            for text in interview_texts
        ]
        logger.info(f"Generated {len(summarized_texts)} summaries.")

        # 2. Synthesize themes from the summaries (New Step)
        synthesized_findings = _synthesize_themes_from_summaries(client, summarized_texts, project_name, model=model)
        if not synthesized_findings or "Error during synthesis" in synthesized_findings:
             logger.error("Synthesis step failed or returned an error. Cannot generate persona.")
             raise Exception("Failed to synthesize themes from interview summaries.")

        # 3. Generate the final persona JSON using the synthesized findings
        final_system_message = f"""You are Thesia, an expert UX Research Assistant specializing in persona creation.
{PERSONA_ARCHITECT_SYSTEM_PROMPT}

Your task is to use the following synthesized findings (which include key themes and supporting quotes extracted from multiple interview summaries) to create a detailed persona.

The persona MUST follow this exact JSON structure:
{PERSONA_JSON_TEMPLATE}

Important guidelines:
1. Base the persona *only* on the provided synthesized findings.
2. Create a *fictional, representative* name for the persona (e.g., "Sarah the Strategist", "David the Developer"). Do NOT use names directly from the summaries/interviews.
3. Integrate the supporting quotes appropriately within the relevant sections (goals, pain_points, etc.).
4. Ensure all fields in the JSON structure are filled out plausibly based on the findings.
5. Keep the summary concise (under 600 characters).
6. Make the image prompt detailed and specific, reflecting the persona.
7. If the findings are sparse, make reasonable inferences but indicate where information was limited."""

        final_user_prompt = f"""Project: {project_name}

Synthesized Findings from Interviews:

{synthesized_findings}

Please generate the persona JSON based *only* on these findings."""

        logger.info(f"Generating final persona JSON using synthesized findings (length: {len(synthesized_findings)} chars)")

        # --- Bedrock/Claude logic --- 
        if model == "claude-3.7-sonnet":
            logger.info("Using Claude 3.7 Sonnet for persona generation")
            persona_data, model_info = generate_with_claude(final_system_message, final_user_prompt, project_name)
            # Add model info to the persona data
            persona_data["model_info"] = model_info
            return persona_data
            
        # --- OpenAI Final Persona Generation --- 
        else: 
            # *** Use gpt-4-turbo for the final generation step for larger context ***
            final_generation_model = "gpt-4-turbo" 
            logger.info(f"Using model '{final_generation_model}' for final JSON generation.")

            # Calculate input tokens for the final call
            final_messages = [
                {"role": "system", "content": final_system_message},
                {"role": "user", "content": final_user_prompt}
            ]
            # Use the *final generation* model for token calculation
            input_tokens_final = sum(_get_token_count(msg["content"], final_generation_model) for msg in final_messages) 
            input_tokens_final += len(final_messages) * 5 
            logger.info(f"Estimated input tokens for final generation: {input_tokens_final}")

            # Determine max_tokens dynamically based on the *final model's* limit
            # gpt-4-turbo has 128k context, output capped at 4096 by default 
            model_context_limit = 128000 
            # Let's target a reasonable max output, e.g., 4000 tokens, ensuring it fits
            # Calculate remaining tokens, leave buffer
            available_output_tokens = model_context_limit - input_tokens_final - 100 # Buffer
            
            if available_output_tokens < 500: # Check if input itself is too large even for turbo
                 logger.error(f"Input tokens ({input_tokens_final}) are too large even for {final_generation_model}")
                 raise ValueError(f"Input content is too long ({input_tokens_final} tokens) for the model.")
            
            # Cap the requested output tokens
            dynamic_max_tokens = min(available_output_tokens, 4000) 
            logger.info(f"Dynamically setting max_tokens for completion to: {dynamic_max_tokens}")

            response = client.chat.completions.create(
                model=final_generation_model, # Use the turbo model here
                messages=final_messages,
                temperature=0.7,
                max_tokens=dynamic_max_tokens, 
            )
            try:
                raw_content = response.choices[0].message.content
                logger.info(f"Received raw content for final persona (length: {len(raw_content)} chars)")
                try:
                    persona_data = json.loads(raw_content)
                except json.JSONDecodeError:
                    logger.warning("Direct JSON parsing failed for final persona, attempting to extract from markdown code block.")
                    match = re.search(r'```json\n(.*?)\n```', raw_content, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                        persona_data = json.loads(json_str)
                        logger.info("Successfully extracted JSON from markdown block.")
                    else:
                        logger.error("Could not extract JSON from final persona response.")
                        logger.error(f"Final Raw Response was: {raw_content}")
                        raise ValueError("Final response was not valid JSON and could not be extracted.") 

                required_fields = [
                    "name", "summary", "image_prompt", "demographics",
                    "background", "goals", "pain_points"
                ]
                for field in required_fields:
                    if field not in persona_data:
                        logger.error(f"Final persona JSON missing required field: {field}")
                        raise ValueError(f"Generated persona JSON is missing required field: {field}")
                
                logger.info("Successfully generated and validated final persona JSON.")
                # Add model info with dummy values
                persona_data["model_info"] = {
                    "model": "gpt-4-turbo",
                    "response_time": 0.0  # We don't have accurate timing
                }
                return persona_data
            except json.JSONDecodeError as e:
                logger.error(f"Fatal Error: Failed to parse final persona JSON: {str(e)}")
                logger.error(f"Final Raw Response was: {raw_content}")
                raise 
            except ValueError as e:
                 logger.error(f"Validation Error: {str(e)}")
                 logger.error(f"Final Raw Response was: {raw_content}")
                 raise
            except Exception as e: 
                 logger.error(f"Unexpected error processing final OpenAI response: {str(e)}")
                 logger.error(f"Final Raw Response was: {raw_content}")
                 raise
                 
    except Exception as e:
        logger.error(f"Error in generate_persona_from_interviews pipeline: {str(e)}")
        raise 

def generate_with_claude(system_prompt: str, user_prompt: str, project_name: str) -> tuple:
    """Generate persona using Claude 3.7 Sonnet via Amazon Bedrock"""
    try:
        # Get AWS credentials from environment variables
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not aws_access_key or not aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # Claude 3.7 Sonnet model config
        region = 'us-east-2'
        model_id = 'arn:aws:bedrock:us-east-2:522814696964:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
        
        # Initialize Bedrock client
        import boto3
        
        # Configure longer timeouts (300 seconds = 5 minutes)
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
        
        # Create request body
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        body = json.dumps({
            "messages": messages,
            "system": system_prompt,
            "max_tokens": 4000,
            "temperature": 0.7,
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
            persona_data = json.loads(content)
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
                persona_data = json.loads(content)
            except json.JSONDecodeError as e:
                # If it still fails, return an error structure
                logger.error(f"Failed to parse JSON after cleanup: {str(e)}")
                persona_data = {
                    "name": "Error generating persona",
                    "summary": f"Failed to parse JSON response: {str(e)}",
                    "demographics": {"age_range": "N/A", "gender": "N/A", "occupation": "N/A", "location": "N/A", "education": "N/A"},
                    "background": "Error occurred during persona generation",
                    "goals": [],
                    "pain_points": [],
                    "error": str(e),
                    "raw_response": content[:200] + "..." if len(content) > 200 else content  # Include truncated response for debugging
                }
        
        # Ensure required fields exist
        required_fields = [
            "name", "summary", "demographics",
            "background", "goals", "pain_points"
        ]
        for field in required_fields:
            if field not in persona_data:
                persona_data[field] = "Not provided" if field in ["name", "summary", "background"] else []
        
        # Create model info for debugging
        model_info = {
            "model": "claude-3.7-sonnet",
            "model_id": model_id,
            "response_time": response_time,
            "start_time": start_time,
            "end_time": end_time
        }
        
        return persona_data, model_info
    except Exception as e:
        logger.error(f"Error in generate_with_claude: {str(e)}")
        basic_persona = {
            "name": "Error in Claude Generation",
            "summary": f"An error occurred while generating the persona: {str(e)}",
            "demographics": {"age_range": "N/A", "gender": "N/A", "occupation": "N/A", "location": "N/A", "education": "N/A"},
            "background": "Error occurred during persona generation with Claude.",
            "goals": [],
            "pain_points": []
        }
        error_info = {
            "model": "claude-3.7-sonnet", 
            "error": str(e)
        }
        return basic_persona, error_info 