import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from langchain_features.models import ResearchPlan

# In-memory store for research plans
research_plans = {}

class ResearchService:
    """Service for generating research plans using LangChain"""
    
    @staticmethod
    def create_plan(title: str, description: str) -> ResearchPlan:
        """Create a new research plan"""
        plan = ResearchPlan.create(title, description)
        research_plans[plan.id] = plan
        return plan
    
    @staticmethod
    def get_plan(plan_id: str) -> Optional[ResearchPlan]:
        """Get a research plan by ID"""
        return research_plans.get(plan_id)
    
    @staticmethod
    def list_plans() -> List[ResearchPlan]:
        """List all research plans"""
        return list(research_plans.values())
    
    @staticmethod
    def generate_plan(plan_id: str, research_brief: str) -> Dict[str, Any]:
        """Generate a research plan based on a research brief"""
        plan = research_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        # Create prompt for research plan generation
        prompt_template = """
        You are Daria, an expert UX researcher specializing in creating comprehensive research plans.
        
        Based on the following research brief, create a detailed research plan that includes:
        1. Objectives - Clear, measurable research goals
        2. Methodology - The research methods to be used
        3. Timeline - A realistic schedule for the research
        4. Questions - Specific questions to ask during interviews or surveys
        
        RESEARCH BRIEF:
        {brief}
        
        Generate a structured research plan in JSON format with these sections:
        - objectives: [list of research goals]
        - methodology: string describing the approach
        - timeline: {key_milestone: timeframe}
        - questions: [{category: string, questions: [list of questions]}]
        
        The response must be valid JSON.
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Generate the research plan
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        result = llm.predict(prompt.format(brief=research_brief))
        
        try:
            # Parse the JSON response
            research_data = json.loads(result)
            
            # Update the plan
            plan.objectives = research_data.get("objectives", [])
            plan.methodology = research_data.get("methodology", "")
            plan.timeline = research_data.get("timeline", {})
            plan.questions = research_data.get("questions", [])
            plan.updated_at = datetime.now()
            
            return {
                "status": "success",
                "plan": {
                    "id": plan.id,
                    "title": plan.title,
                    "description": plan.description,
                    "objectives": plan.objectives,
                    "methodology": plan.methodology,
                    "timeline": plan.timeline,
                    "questions": plan.questions
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
    def generate_interview_script(plan_id: str, participant_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate an interview script based on a research plan"""
        plan = research_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        # Default participant info if none provided
        if not participant_info:
            participant_info = {
                "role": "Generic participant",
                "experience": "Unknown",
                "industry": "General"
            }
        
        # Extract questions from the research plan
        all_questions = []
        for category in plan.questions:
            if isinstance(category, dict) and "questions" in category:
                all_questions.extend(category["questions"])
        
        # Create prompt for interview script generation
        prompt_template = """
        You are Daria, an expert UX researcher preparing for an interview.
        
        Based on the research plan objectives and questions, create a personalized interview script for a participant with the following characteristics:
        
        PARTICIPANT INFORMATION:
        Role: {role}
        Experience: {experience}
        Industry: {industry}
        
        RESEARCH OBJECTIVES:
        {objectives}
        
        RESEARCH QUESTIONS:
        {questions}
        
        Create an interview script that includes:
        1. Introduction - A brief welcome and explanation of the interview purpose
        2. Warm-up questions - Easy questions to build rapport
        3. Main questions - The core research questions, adapted to this participant
        4. Follow-up prompts - Suggested follow-up questions based on possible responses
        5. Conclusion - Closing remarks and next steps
        
        Format the script as a conversation guide with clear sections.
        """
        
        # Format the objectives and questions as text
        objectives_text = "\n".join([f"- {obj}" for obj in plan.objectives])
        questions_text = "\n".join([f"- {q}" for q in all_questions])
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Generate the interview script
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        result = llm.predict(prompt.format(
            role=participant_info["role"],
            experience=participant_info["experience"],
            industry=participant_info["industry"],
            objectives=objectives_text,
            questions=questions_text
        ))
        
        return {
            "status": "success",
            "script": result,
            "plan_id": plan_id,
            "participant_info": participant_info
        }
    
    @staticmethod
    def save_plan(plan_id: str) -> Dict[str, Any]:
        """Save the research plan to a file"""
        plan = research_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        # Create directory if it doesn't exist
        os.makedirs("research_plans", exist_ok=True)
        
        # Generate filename
        filename = f"research_plans/research_plan_{plan_id}.json"
        
        # Prepare data for serialization
        plan_data = {
            "id": plan.id,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "title": plan.title,
            "description": plan.description,
            "objectives": plan.objectives,
            "methodology": plan.methodology,
            "timeline": plan.timeline,
            "questions": plan.questions
        }
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(plan_data, f, indent=2)
        
        return {
            "status": "success",
            "message": "Research plan saved successfully",
            "filename": filename
        } 