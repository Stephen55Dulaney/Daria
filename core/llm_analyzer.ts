import { Configuration, OpenAIApi } from 'openai';

export enum InsightType {
  BEHAVIORAL = 'behavioral',
  ATTITUDINAL = 'attitudinal',
  PAIN_POINT = 'pain_point',
  OPPORTUNITY = 'opportunity',
  THEME = 'theme',
  FEATURE_REQUEST = 'feature_request',
  WORKFLOW = 'workflow'
}

export interface UXInsight {
  type: InsightType;
  content: string;
  confidence: number;
  supporting_quotes: string[];
  context: Record<string, any>;
  metadata: Record<string, any>;
}

export class LLMAnalyzer {
  private openai: OpenAIApi;
  private prompts: Record<string, string>;

  constructor() {
    const configuration = new Configuration({
      apiKey: process.env.OPENAI_API_KEY,
    });
    this.openai = new OpenAIApi(configuration);

    this.prompts = {
      theme_identification: `
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
      `,
      pain_point_detection: `
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
      `,
      opportunity_extraction: `
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
      `,
      insight_classification: `
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
      `
    };
  }

  async analyze_text(text: string, analysis_type: string): Promise<any> {
    try {
      const response = await this.openai.createChatCompletion({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: "You are an expert UX researcher skilled at analyzing user interviews and extracting meaningful insights."
          },
          {
            role: "user",
            content: `${this.prompts[analysis_type]}\n\nText to analyze:\n${text}`
          }
        ],
        temperature: 0.2
      });

      return JSON.parse(response.data.choices[0].message?.content || '{}');
    } catch (error) {
      console.error('Error analyzing text:', error);
      return null;
    }
  }

  async extract_insights(text: string): Promise<UXInsight[]> {
    const insights: UXInsight[] = [];
    const analysis_types = [
      "theme_identification",
      "pain_point_detection",
      "opportunity_extraction",
      "insight_classification"
    ];

    for (const analysis_type of analysis_types) {
      const result = await this.analyze_text(text, analysis_type);
      if (result) {
        switch (analysis_type) {
          case "theme_identification":
            insights.push({
              type: InsightType.THEME,
              content: result.primary_theme,
              confidence: result.confidence,
              supporting_quotes: result.supporting_quotes,
              context: { sub_themes: result.sub_themes },
              metadata: { analysis_type }
            });
            break;

          case "pain_point_detection":
            insights.push({
              type: InsightType.PAIN_POINT,
              content: result.pain_point,
              confidence: result.severity / 5.0,
              supporting_quotes: result.supporting_quotes,
              context: {
                impact_area: result.impact_area,
                potential_solution: result.potential_solution
              },
              metadata: { analysis_type }
            });
            break;

          case "opportunity_extraction":
            insights.push({
              type: InsightType.OPPORTUNITY,
              content: result.opportunity,
              confidence: 1.0 - (result.implementation_complexity / 5.0),
              supporting_quotes: result.supporting_quotes,
              context: {
                value_proposition: result.value_proposition,
                user_benefit: result.user_benefit
              },
              metadata: { analysis_type }
            });
            break;

          case "insight_classification":
            insights.push({
              type: InsightType[result.insight_type.toUpperCase() as keyof typeof InsightType],
              content: result.summary,
              confidence: result.confidence,
              supporting_quotes: result.supporting_quotes,
              context: result.context,
              metadata: { analysis_type }
            });
            break;
        }
      }
    }

    return insights;
  }

  generate_affinity_diagram(insights: UXInsight[]) {
    const grouped_insights: Record<string, any[]> = {};
    
    for (const insight of insights) {
      if (!grouped_insights[insight.type]) {
        grouped_insights[insight.type] = [];
      }
      grouped_insights[insight.type].push({
        content: insight.content,
        confidence: insight.confidence,
        supporting_quotes: insight.supporting_quotes,
        context: insight.context
      });
    }

    return {
      name: "Research Insights",
      children: Object.entries(grouped_insights).map(([insight_type, insights_list]) => ({
        name: insight_type.charAt(0).toUpperCase() + insight_type.slice(1),
        children: insights_list.map(insight => ({
          name: insight.content,
          confidence: insight.confidence,
          quotes: insight.supporting_quotes,
          context: insight.context
        }))
      }))
    };
  }
} 