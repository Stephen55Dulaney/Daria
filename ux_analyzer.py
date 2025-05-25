from enum import Enum
from typing import List, Dict, Any, Optional
from openai import OpenAI
import json
import os
from datetime import datetime

class InsightType(Enum):
    BEHAVIORAL = "behavioral"  # What users do
    ATTITUDINAL = "attitudinal"  # What users think/feel
    PAIN_POINT = "pain_point"  # User frustrations
    OPPORTUNITY = "opportunity"  # Potential improvements
    THEME = "theme"  # Recurring patterns
    FEATURE_REQUEST = "feature_request"  # Explicit requests
    WORKFLOW = "workflow"  # Process insights

class UXAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the UX analyzer with OpenAI"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Define analysis prompts
        self.prompts = {
            "theme_identification": """
            Analyze this interview segment and identify key UX themes.
            Consider:
            - User goals and needs
            - Pain points and frustrations 
            - Workflow patterns
            - Mental models
            - Feature requests or implied needs
            
            Format your response as JSON with:
            {
                "primary_theme": str,
                "sub_themes": List[str],
                "supporting_quotes": List[str],
                "confidence": float (0-1)
            }
            """,
            
            "pain_point_detection": """
            Identify user pain points and frustrations in this segment.
            Look for:
            - Explicit complaints
            - Workarounds
            - Negative emotional language
            - Process inefficiencies
            - Feature gaps
            
            Format your response as JSON with:
            {
                "pain_point": str,
                "severity": int (1-5),
                "impact_area": str,
                "supporting_quotes": List[str],
                "potential_solution": str
            }
            """,
            
            "opportunity_extraction": """
            Extract product/feature opportunities from this segment.
            Consider:
            - Unmet needs
            - Feature requests
            - Process improvements
            - Integration possibilities
            - New use cases
            
            Format your response as JSON with:
            {
                "opportunity": str,
                "value_proposition": str,
                "user_benefit": str,
                "supporting_quotes": List[str],
                "implementation_complexity": int (1-5)
            }
            """,
            
            "insight_classification": """
            Classify the type of UX insight in this segment.
            Categories:
            - Behavioral (what users do)
            - Attitudinal (what users think/feel)
            - Pain Point (user frustrations)
            - Opportunity (potential improvements)
            - Theme (recurring patterns)
            
            Format your response as JSON with:
            {
                "insight_type": str,
                "summary": str,
                "supporting_quotes": List[str],
                "confidence": float (0-1),
                "context": {
                    "user_type": str,
                    "scenario": str,
                    "feature": str
                }
            }
            """
        }

    async def analyze_text(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze text using specified prompt template"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert UX researcher skilled at analyzing user interviews and extracting meaningful insights."},
                    {"role": "user", "content": f"{self.prompts[analysis_type]}\n\nText to analyze:\n{text}"}
                ],
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error analyzing text: {str(e)}")
            return None

    async def extract_insights(self, text: str) -> List[Dict[str, Any]]:
        """Extract all types of insights from text"""
        insights = []
        
        analysis_types = ["theme_identification", "pain_point_detection", 
                         "opportunity_extraction", "insight_classification"]
        
        for analysis_type in analysis_types:
            result = await self.analyze_text(text, analysis_type)
            if result:
                if analysis_type == "theme_identification":
                    insights.append({
                        "type": InsightType.THEME.value,
                        "content": result["primary_theme"],
                        "confidence": result["confidence"],
                        "supporting_quotes": result["supporting_quotes"],
                        "context": {"sub_themes": result["sub_themes"]},
                        "metadata": {"analysis_type": analysis_type}
                    })
                
                elif analysis_type == "pain_point_detection":
                    insights.append({
                        "type": InsightType.PAIN_POINT.value,
                        "content": result["pain_point"],
                        "confidence": result["severity"] / 5.0,
                        "supporting_quotes": result["supporting_quotes"],
                        "context": {
                            "impact_area": result["impact_area"],
                            "potential_solution": result["potential_solution"]
                        },
                        "metadata": {"analysis_type": analysis_type}
                    })
                
                elif analysis_type == "opportunity_extraction":
                    insights.append({
                        "type": InsightType.OPPORTUNITY.value,
                        "content": result["opportunity"],
                        "confidence": 1.0 - (result["implementation_complexity"] / 5.0),
                        "supporting_quotes": result["supporting_quotes"],
                        "context": {
                            "value_proposition": result["value_proposition"],
                            "user_benefit": result["user_benefit"]
                        },
                        "metadata": {"analysis_type": analysis_type}
                    })
                
                elif analysis_type == "insight_classification":
                    insights.append({
                        "type": result["insight_type"].upper(),
                        "content": result["summary"],
                        "confidence": result["confidence"],
                        "supporting_quotes": result["supporting_quotes"],
                        "context": result["context"],
                        "metadata": {"analysis_type": analysis_type}
                    })
        
        return insights

    def generate_affinity_diagram(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate affinity diagram from insights"""
        grouped_insights = {}
        for insight in insights:
            insight_type = insight["type"]
            if insight_type not in grouped_insights:
                grouped_insights[insight_type] = []
            grouped_insights[insight_type].append({
                "content": insight["content"],
                "confidence": insight["confidence"],
                "supporting_quotes": insight["supporting_quotes"],
                "context": insight["context"]
            })
        
        return {
            "name": "Research Insights",
            "children": [
                {
                    "name": insight_type.capitalize(),
                    "children": [
                        {
                            "name": insight["content"],
                            "confidence": insight["confidence"],
                            "quotes": insight["supporting_quotes"],
                            "context": insight["context"]
                        }
                        for insight in insights_list
                    ]
                }
                for insight_type, insights_list in grouped_insights.items()
            ]
        }

    async def analyze_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a complete interview and generate insights"""
        try:
            # Extract transcript text
            transcript = interview_data.get("transcript", "")
            if not transcript:
                return {"error": "No transcript found in interview data"}

            # Extract insights
            insights = await self.extract_insights(transcript)

            # Generate affinity diagram
            affinity_diagram = self.generate_affinity_diagram(insights)

            # Return complete analysis
            return {
                "interview_id": interview_data.get("id"),
                "analysis_date": datetime.now().isoformat(),
                "insights": insights,
                "affinity_diagram": affinity_diagram,
                "metadata": {
                    "project_name": interview_data.get("project_name"),
                    "interview_type": interview_data.get("interview_type"),
                    "date": interview_data.get("date")
                }
            }

        except Exception as e:
            print(f"Error analyzing interview: {str(e)}")
            return {"error": str(e)} 