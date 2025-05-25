from typing import List, Dict, Any, Optional
import openai
import json
from dataclasses import dataclass
from enum import Enum
import os

class InsightType(Enum):
    BEHAVIORAL = "behavioral"  # What users do
    ATTITUDINAL = "attitudinal"  # What users think/feel
    PAIN_POINT = "pain_point"  # User frustrations
    OPPORTUNITY = "opportunity"  # Potential improvements
    THEME = "theme"  # Recurring patterns
    FEATURE_REQUEST = "feature_request"  # Explicit requests
    WORKFLOW = "workflow"  # Process insights

@dataclass
class UXInsight:
    type: InsightType
    content: str
    confidence: float
    supporting_quotes: List[str]
    context: Dict[str, Any]
    metadata: Dict[str, Any]

class LLMAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM analyzer with OpenAI GPT-4"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        openai.api_key = self.api_key
        
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
    
    def analyze_text(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze text using specified prompt template"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert UX researcher skilled at analyzing user interviews and extracting meaningful insights."},
                    {"role": "user", "content": f"{self.prompts[analysis_type]}\n\nText to analyze:\n{text}"}
                ],
                temperature=0.2  # Lower temperature for more focused analysis
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error analyzing text: {str(e)}")
            return None
    
    def extract_insights(self, text: str) -> List[UXInsight]:
        """Extract all types of insights from text"""
        insights = []
        
        # Run all analysis types
        analysis_types = ["theme_identification", "pain_point_detection", 
                         "opportunity_extraction", "insight_classification"]
        
        for analysis_type in analysis_types:
            result = self.analyze_text(text, analysis_type)
            if result:
                # Convert result to UXInsight based on type
                if analysis_type == "theme_identification":
                    insights.append(UXInsight(
                        type=InsightType.THEME,
                        content=result["primary_theme"],
                        confidence=result["confidence"],
                        supporting_quotes=result["supporting_quotes"],
                        context={"sub_themes": result["sub_themes"]},
                        metadata={"analysis_type": analysis_type}
                    ))
                
                elif analysis_type == "pain_point_detection":
                    insights.append(UXInsight(
                        type=InsightType.PAIN_POINT,
                        content=result["pain_point"],
                        confidence=result["severity"] / 5.0,
                        supporting_quotes=result["supporting_quotes"],
                        context={
                            "impact_area": result["impact_area"],
                            "potential_solution": result["potential_solution"]
                        },
                        metadata={"analysis_type": analysis_type}
                    ))
                
                elif analysis_type == "opportunity_extraction":
                    insights.append(UXInsight(
                        type=InsightType.OPPORTUNITY,
                        content=result["opportunity"],
                        confidence=1.0 - (result["implementation_complexity"] / 5.0),
                        supporting_quotes=result["supporting_quotes"],
                        context={
                            "value_proposition": result["value_proposition"],
                            "user_benefit": result["user_benefit"]
                        },
                        metadata={"analysis_type": analysis_type}
                    ))
                
                elif analysis_type == "insight_classification":
                    insights.append(UXInsight(
                        type=InsightType[result["insight_type"].upper()],
                        content=result["summary"],
                        confidence=result["confidence"],
                        supporting_quotes=result["supporting_quotes"],
                        context=result["context"],
                        metadata={"analysis_type": analysis_type}
                    ))
        
        return insights
    
    def generate_affinity_diagram(self, insights: List[UXInsight]) -> Dict[str, Any]:
        """Generate affinity diagram from insights"""
        # Group insights by type
        grouped_insights = {}
        for insight in insights:
            if insight.type.value not in grouped_insights:
                grouped_insights[insight.type.value] = []
            grouped_insights[insight.type.value].append({
                "content": insight.content,
                "confidence": insight.confidence,
                "supporting_quotes": insight.supporting_quotes,
                "context": insight.context
            })
        
        # Create affinity diagram structure
        affinity_diagram = {
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
        
        return affinity_diagram 