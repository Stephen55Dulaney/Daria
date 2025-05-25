import type { NextApiRequest, NextApiResponse } from 'next';
import { LLMAnalyzer } from '../../core/llm_analyzer';

// Initialize analyzer
const llmAnalyzer = new LLMAnalyzer();

type SearchResponse = {
  insights: any[];
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

    // Extract insights from the query
    const insights = await llmAnalyzer.extract_insights(query);

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