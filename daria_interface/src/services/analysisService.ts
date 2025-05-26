import api from './api';

export interface ResearchAssistant {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
}

export interface DiscussionGuide {
  id: string;
  title: string;
  description?: string;
}

export interface Session {
  id: string;
  title: string;
  date: string;
  guideId: string;
}

export interface AnalysisResult {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  assistantId: string;
}

export const analysisService = {
  // Get all research assistants
  getResearchAssistants: async (): Promise<ResearchAssistant[]> => {
    const response = await api.get('/research-assistants');
    return response.data;
  },

  // Get all discussion guides
  getDiscussionGuides: async (): Promise<DiscussionGuide[]> => {
    const response = await api.get('/discussion-guides');
    return response.data;
  },

  // Get sessions for a specific guide
  getSessionsByGuide: async (guideId: string): Promise<Session[]> => {
    const response = await api.get(`/guides/${guideId}/sessions`);
    return response.data;
  },

  // Run analysis
  runAnalysis: async (
    guideId: string,
    sessionId: string,
    assistantId: string
  ): Promise<AnalysisResult> => {
    const response = await api.post('/analysis', {
      guideId,
      sessionId,
      assistantId,
    });
    return response.data;
  },

  // Save analysis to gallery
  saveToGallery: async (analysis: AnalysisResult): Promise<AnalysisResult> => {
    const response = await api.post('/gallery/analysis', analysis);
    return response.data;
  },

  // Get saved analyses
  getSavedAnalyses: async (): Promise<AnalysisResult[]> => {
    const response = await api.get('/gallery/analysis');
    return response.data;
  },
}; 