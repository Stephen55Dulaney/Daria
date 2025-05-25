import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from langchain_features.models import DiscoveryPlan

# In-memory store for discovery plans
discovery_plans = {}

class DiscoveryService:
    """Service for generating discovery plans using LangChain"""
    
    @staticmethod
    def create_plan(title: str, description: str) -> DiscoveryPlan:
        """Create a new discovery plan"""
        plan = DiscoveryPlan.create(title, description)
        discovery_plans[plan.id] = plan
        return plan
    
    @staticmethod
    def get_plan(plan_id: str) -> Optional[DiscoveryPlan]:
        """Get a discovery plan by ID"""
        return discovery_plans.get(plan_id)
    
    @staticmethod
    def list_plans() -> List[DiscoveryPlan]:
        """List all discovery plans"""
        return list(discovery_plans.values())
    
    @staticmethod
    def generate_plan(plan_id: str, interview_transcripts: List[str]) -> Dict[str, Any]:
        """Generate a discovery plan based on interview transcripts"""
        plan = discovery_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
            
        # Combine all transcripts
        combined_transcript = "\n\n".join([f"INTERVIEW {i+1}:\n{transcript}" 
                                          for i, transcript in enumerate(interview_transcripts)])
        
        # Create prompt for discovery plan generation
        prompt_template = """
        You are Daria, an expert UX researcher specializing in creating insightful discovery plans.
        
        A discovery plan identifies key findings, themes, and next steps based on user interviews.
        
        Based on the following interview transcripts, create a comprehensive discovery plan that includes:
        1. Key findings - The most important insights from the interviews
        2. Themes - Recurring patterns across interviews
        3. Next steps - Recommendations for further research or actions
        
        INTERVIEW TRANSCRIPTS:
        {transcripts}
        
        Generate a structured discovery plan in JSON format with these sections:
        - key_findings: [list of findings]
        - themes: [list of themes with supporting quotes]
        - next_steps: [list of recommended actions]
        
        The response must be valid JSON.
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Generate the discovery plan
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        result = llm.predict(prompt.format(transcripts=combined_transcript))
        
        try:
            # Parse the JSON response
            discovery_data = json.loads(result)
            
            # Update the plan
            plan.key_findings = discovery_data.get("key_findings", [])
            plan.themes = discovery_data.get("themes", [])
            plan.next_steps = discovery_data.get("next_steps", [])
            plan.updated_at = datetime.now()
            
            return {
                "status": "success",
                "plan": {
                    "id": plan.id,
                    "title": plan.title,
                    "description": plan.description,
                    "key_findings": plan.key_findings,
                    "themes": plan.themes,
                    "next_steps": plan.next_steps
                }
            }
        except json.JSONDecodeError:
            # If the model didn't return valid JSON, try to extract useful information
            return {
                "status": "error",
                "error": "Failed to parse AI response as JSON",
                "raw_output": result
            }
    
    @staticmethod
    def save_plan(plan_id: str) -> Dict[str, Any]:
        """Save the discovery plan to a file"""
        plan = discovery_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        # Create directory if it doesn't exist
        os.makedirs("discovery_plans", exist_ok=True)
        
        # Generate filename
        filename = f"discovery_plans/discovery_plan_{plan_id}.json"
        
        # Prepare data for serialization
        plan_data = {
            "id": plan.id,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "title": plan.title,
            "description": plan.description,
            "key_findings": plan.key_findings,
            "themes": plan.themes,
            "next_steps": plan.next_steps
        }
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(plan_data, f, indent=2)
        
        return {
            "status": "success",
            "message": "Discovery plan saved successfully",
            "filename": filename
        } 