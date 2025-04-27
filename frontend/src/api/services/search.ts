import axios from 'axios'

export interface SearchParams {
  query: string
  type: string
}

export interface SearchResult {
  chunk_id: string
  content: string
  interview_id: string
  interviewee_name: string
  metadata: {
    emotion: 'positive' | 'negative' | 'neutral'
    emotion_intensity: number
    insight_tags: string[]
    related_feature: string | null
    themes: string[]
  }
  project_name: string
  similarity: number
  timestamp: string
  transcript_name: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
}

// Create an axios instance with default config
const api = axios.create({
  // For development, we'll use the Vite dev server proxy
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
})

const searchAPI = {
  search: async (params: SearchParams): Promise<SearchResponse> => {
    try {
      const response = await api.post<SearchResponse>('/api/search/advanced', params)
      console.log('Search API Response:', response.data) // Debug log
      return response.data
    } catch (error) {
      console.error('Search API Error:', error)
      throw error
    }
  },
}

export default searchAPI 