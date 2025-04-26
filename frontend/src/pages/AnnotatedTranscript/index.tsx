import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import axios from 'axios'

interface TranscriptChunk {
  id: string
  timestamp: string
  text: string
  emotion?: 'positive' | 'negative' | 'neutral' | string
  emotion_intensity?: number
  themes?: string[]
  insight_tags?: string[]
  related_feature?: string | null
  entries?: Array<{
    speaker: string
    timestamp: string
    text: string
  }>
  metadata?: {
    project_name?: string
    emotion?: string
    emotion_intensity?: number
    insight_tags?: string[]
    related_feature?: string | null
    themes?: string[]
  }
}

interface PaginationInfo {
  current_page: number
  total_pages: number
  total_chunks: number
  items_per_page: number
}

interface AnnotatedTranscriptProps {
  interviewee_name: string
  project_name: string
  date: string
  chunks: TranscriptChunk[]
  pagination: PaginationInfo
}

const AnnotatedTranscript: React.FC = () => {
  const { transcriptId } = useParams<{ transcriptId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const targetTimestamp = searchParams.get('timestamp')
  const currentPage = parseInt(searchParams.get('page') || '1')
  
  const [transcript, setTranscript] = useState<AnnotatedTranscriptProps | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTranscript = async (page: number) => {
    try {
      console.log('Fetching transcript:', transcriptId, 'page:', page);
      const response = await axios.get(`http://127.0.0.1:5003/annotated-transcript/${transcriptId}/${page}`, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      if (response.data.error) {
        setError(response.data.error);
      } else {
        console.log('Full transcript response:', response.data);
        console.log('First chunk:', response.data.chunks?.[0]);
        console.log('Transcript metadata:', response.data.metadata);
        setTranscript(response.data);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load transcript';
      setError(errorMessage);
      console.error('Error fetching transcript:', {
        error: err,
        message: errorMessage,
        status: err.response?.status,
        data: err.response?.data
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (transcriptId) {
      fetchTranscript(currentPage);
    }
  }, [transcriptId, currentPage]);

  useEffect(() => {
    if (targetTimestamp && !isLoading && transcript) {
      const element = document.getElementById(`timestamp-${targetTimestamp}`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
        element.classList.add('bg-yellow-50')
      }
    }
  }, [targetTimestamp, isLoading, transcript]);

  const handlePageChange = (newPage: number) => {
    setSearchParams({ page: newPage.toString(), ...(targetTimestamp ? { timestamp: targetTimestamp } : {}) });
  };

  const renderPagination = () => {
    if (!transcript?.pagination) return null;
    const { current_page, total_pages } = transcript.pagination;

    return (
      <div className="flex justify-center items-center space-x-4 mt-8">
        <button
          onClick={() => handlePageChange(current_page - 1)}
          disabled={current_page <= 1}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <span className="text-sm text-gray-600">
          Page {current_page} of {total_pages}
        </span>
        <button
          onClick={() => handlePageChange(current_page + 1)}
          disabled={current_page >= total_pages}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    );
  };

  const renderEmotionBadge = (emotion: string | undefined, intensity: number | undefined) => {
    if (!emotion) return null
    
    const emotionColors = {
      positive: 'bg-green-100 text-green-800 border-green-200',
      negative: 'bg-red-100 text-red-800 border-red-200',
      neutral: 'bg-gray-100 text-gray-800 border-gray-200'
    }

    const intensityStars = intensity ? '★'.repeat(intensity) : ''
    const colorClass = emotionColors[emotion as keyof typeof emotionColors] || emotionColors.neutral

    return (
      <span className={`px-3 py-1 ${colorClass} text-sm rounded-full border inline-flex items-center gap-1`}>
        <span className="capitalize">{emotion}</span>
        {intensityStars && (
          <span className="text-yellow-500 ml-1">{intensityStars}</span>
        )}
      </span>
    )
  }

  const renderThemes = (themes: string[] | undefined) => {
    if (!themes || themes.length === 0) return null;
    return (
      <div className="space-y-1">
        <div className="text-sm font-medium text-gray-700">Themes:</div>
        <div className="flex flex-wrap gap-2">
          {themes.map((theme, i) => (
            <span 
              key={i} 
              className="px-3 py-1 bg-purple-100 text-purple-800 text-sm rounded-full border border-purple-200 hover:bg-purple-200 transition-colors"
            >
              {theme}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderInsightTags = (insights: string[] | undefined) => {
    if (!insights || insights.length === 0) return null;

    // Color mapping for different types of insights
    const insightColors: { [key: string]: string } = {
      pain_point: 'bg-red-100 text-red-800 border-red-200 hover:bg-red-200',
      opportunity: 'bg-green-100 text-green-800 border-green-200 hover:bg-green-200',
      need: 'bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-200',
      quote: 'bg-purple-100 text-purple-800 border-purple-200 hover:bg-purple-200',
      behavior: 'bg-orange-100 text-orange-800 border-orange-200 hover:bg-orange-200',
      preference: 'bg-indigo-100 text-indigo-800 border-indigo-200 hover:bg-indigo-200',
      feedback: 'bg-teal-100 text-teal-800 border-teal-200 hover:bg-teal-200'
    };

    const getInsightColor = (insight: string): string => {
      // Check if the insight starts with any of our known types
      const type = Object.keys(insightColors).find(key => insight.toLowerCase().startsWith(key));
      return type ? insightColors[type] : insightColors.feedback; // Default to feedback style
    };

    return (
      <div className="space-y-1">
        <div className="text-sm font-medium text-gray-700">Insights:</div>
        <div className="flex flex-wrap gap-2">
          {insights.map((insight, i) => (
            <span 
              key={i} 
              className={`px-3 py-1 text-sm rounded-full border transition-colors ${getInsightColor(insight)}`}
            >
              {insight}
            </span>
          ))}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error || !transcript) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 text-red-700 p-4 rounded-md">
          {error || 'Failed to load transcript'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Back Link */}
      <Link
        to="/advanced-search"
        className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6"
      >
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          fill="none" 
          viewBox="0 0 24 24" 
          strokeWidth={1.5} 
          stroke="currentColor" 
          className="w-5 h-5 mr-2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to Advanced Search
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">{transcript.interviewee_name}</h1>
        <div className="text-gray-600">
          <p>{transcript.project_name}</p>
          <p>{transcript.date}</p>
        </div>
      </div>

      {/* Top Pagination */}
      <div className="mb-3">
        {renderPagination()}
      </div>

      {/* Transcript Chunks */}
      <div className="space-y-8">
        {transcript.chunks.map((chunk) => (
          <div 
            key={chunk.id}
            id={`timestamp-${chunk.timestamp}`}
            className="bg-white rounded-lg shadow p-6 transition-colors duration-300"
          >
            {/* Timestamp */}
            <div className="text-sm text-gray-500 mb-2">
              {chunk.timestamp}
            </div>

            {/* Content */}
            <div className="prose prose-sm max-w-none mb-4">
              <p className="text-gray-700">{chunk.text}</p>
            </div>

            {/* Entries */}
            {chunk.entries && chunk.entries.length > 0 && (
              <div className="space-y-2 mb-4">
                {chunk.entries.map((entry, index) => (
                  <div key={index} className="pl-4 border-l-2 border-gray-200">
                    <div className="text-sm text-gray-500">{entry.speaker} • {entry.timestamp}</div>
                    <div className="text-gray-700">{entry.text}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Metadata */}
            <div className="space-y-3">
              {chunk.emotion && (
                <div className="space-y-1">
                  <div className="text-sm font-medium text-gray-700">Emotion:</div>
                  {renderEmotionBadge(chunk.emotion, chunk.emotion_intensity)}
                </div>
              )}
              
              {chunk.themes && chunk.themes.length > 0 && renderThemes(chunk.themes)}
              
              {chunk.insight_tags && chunk.insight_tags.length > 0 && renderInsightTags(chunk.insight_tags)}

              {chunk.related_feature && (
                <div className="space-y-1">
                  <div className="text-sm font-medium text-gray-700">Related Feature:</div>
                  <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-sm rounded-full border border-indigo-200">
                    {chunk.related_feature}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {renderPagination()}
    </div>
  )
}

export default AnnotatedTranscript 