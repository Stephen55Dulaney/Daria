"""
Persona Architect GPT module that provides customized prompts for persona generation.
"""
import json
from openai import OpenAI

# The specialized system prompt for the Persona Architect GPT
PERSONA_ARCHITECT_SYSTEM_PROMPT = """You are Persona Architect GPT, an expert UX researcher specialized in creating evidence-based user personas from research data. Your responses should:

1. ALWAYS base persona details on provided research data, never invent demographic information without evidence
2. ORGANIZE persona reports with clear, consistent sections
3. HIGHLIGHT direct quotes and specific data points to support insights
4. ENSURE personas are realistic, nuanced, and avoid stereotypes
5. FOCUS on goals, pain points, and behaviors rather than just demographics
6. ADAPT tone and formatting to match the intended audience (stakeholders, designers, developers)
7. INCLUDE actionable insights for product/service improvements
8. MAINTAIN a professional, analytical tone while making personas feel like real people

When analyzing raw data, look for:
- Patterns across multiple participants
- Emotional inflections and word choice
- Contradictions between stated preferences and behaviors
- Underlying motivations and unstated needs

Format personas with these sections:
- Name and Role
- Summary background one or two paragraphs totaling less than 600 characters
- Image prompt to generate a AI generated persona picture
- Key Demographics (evidence-based)
- Background & Context
- Goals & Motivations
- Pain Points & Challenges
- Behaviors & Habits
- Technology Usage
- Quotes & Evidence
- Opportunities & Recommendations

For follow-up questions, provide additional depth rather than contradicting the initial persona.
"""

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

def generate_persona_architect_prompt(interviews):
    """
    Generate the prompt for the Persona Architect GPT.
    
    Args:
        interviews (list): List of interview data objects
        
    Returns:
        str: Formatted prompt for the Persona Architect GPT
    """
    analysis_prompt = f"""As Persona Architect GPT, analyze these {len(interviews)} interviews and create a detailed, evidence-based user persona. 
Focus on extracting specific, actionable insights from the interviews.

For each interview, I'll provide:
1. The interview transcript
2. The individual analysis
3. The interview date and type

Please create a comprehensive persona and return it as a valid JSON object with the following structure:

{PERSONA_JSON_TEMPLATE}

Interview Data:
{json.dumps(interviews, indent=2)}

Please ensure your response is a valid JSON object with all the sections and fields as shown above. Include specific quotes from the interviews to support each insight. 
Format the image_prompt to create a realistic portrait of this persona that captures their demographic characteristics and overall mood.
"""
    return analysis_prompt

def generate_persona_with_architect(openai_client, interviews):
    """
    Generate a persona using the Persona Architect GPT.
    
    Args:
        openai_client: OpenAI client instance
        interviews (list): List of interview data objects
        
    Returns:
        dict: The generated persona data
    """
    analysis_prompt = generate_persona_architect_prompt(interviews)
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": PERSONA_ARCHITECT_SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt}
        ],
        temperature=0.7
    )
    
    # Extract the response content
    analysis = response.choices[0].message.content
    
    # Parse the JSON response
    try:
        persona_data = json.loads(analysis)
        return persona_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON response: {str(e)}") 