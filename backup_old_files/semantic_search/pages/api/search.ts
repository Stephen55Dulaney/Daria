import type { NextApiRequest, NextApiResponse } from 'next';
import { ResearchAnalyzer } from '@core/research_analyzer';
import { LLMAnalyzer, UXInsight } from '@core/llm_analyzer';

// Initialize analyzers
const researchAnalyzer = new ResearchAnalyzer();
const llmAnalyzer = new LLMAnalyzer();

type SearchResponse = {
  insights: UXInsight[];
  affinity_diagram: any;
  total_results: number;
  message?: string;
  error?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<SearchResponse>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ 
      insights: [], 
      affinity_diagram: null,
      total_results: 0,
      message: 'Method not allowed' 
    });
  }

  try {
    const { query } = req.body;

    if (!query) {
      return res.status(400).json({ 
        insights: [],
        affinity_diagram: null,
        total_results: 0,
        message: 'Query is required' 
      });
    }

    // Perform semantic search
    const searchResults = await researchAnalyzer.semantic_search(
      query,
      { analyze_results: true }
    );

    // Extract insights from search results
    const insights: UXInsight[] = [];
    for (const result of searchResults) {
      const textInsights = await llmAnalyzer.extract_insights(result.content);
      insights.push(...textInsights);
    }

    // Generate affinity diagram
    const affinityDiagram = llmAnalyzer.generate_affinity_diagram(insights);

    return res.status(200).json({
      insights,
      affinity_diagram: affinityDiagram,
      total_results: insights.length,
    });

  } catch (error) {
    console.error('Search error:', error);
    return res.status(500).json({ 
      insights: [],
      affinity_diagram: null,
      total_results: 0,
      message: 'Internal server error',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
} 