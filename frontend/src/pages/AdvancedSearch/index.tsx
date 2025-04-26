import React, { useState } from 'react'
import searchAPI, { SearchResult } from '../../api/services/search'
import { Link } from 'react-router-dom'

const AdvancedSearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState('semantic')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const searchTypes = [
    {
      value: 'semantic',
      label: 'Semantic Search',
      description: 'Find relevant content based on meaning, not just exact matches'
    },
    {
      value: 'exact',
      label: 'Exact Match',
      description: 'Search for exact text matches'
    },
    {
      value: 'tag',
      label: 'Tag Search',
      description: 'Search across emotions, insights, and themes'
    }
  ]

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query')
      return
    }

    setIsLoading(true)
    setError(null)
    setResults([])

    try {
      const response = await searchAPI.search({
        query: searchQuery,
        type: searchType,
      })
      
      if (response && response.results && Array.isArray(response.results)) {
        setResults(response.results)
      } else {
        console.error('Invalid response format:', response)
        setError('Received invalid response format from server')
      }
    } catch (error) {
      console.error('Search failed:', error)
      setError('Failed to perform search. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const renderThemes = (themes: string[] | undefined) => {
    if (!themes || themes.length === 0) return null
    return (
      <div>
        <div className="text-sm font-medium text-gray-700 mb-1">Themes:</div>
        <div className="flex flex-wrap gap-2">
          {themes.map((theme, i) => (
            <span key={i} className="px-3 py-1 bg-purple-100 text-purple-800 text-sm rounded-full border border-purple-200">
              {theme}
            </span>
          ))}
        </div>
      </div>
    )
  }

  const renderInsights = (insights: string[] | undefined) => {
    if (!insights || insights.length === 0) return null
    return (
      <div>
        <div className="text-sm font-medium text-gray-700 mb-1">Insights:</div>
        <div className="flex flex-wrap gap-2">
          {insights.map((insight, i) => (
            <span key={i} className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full border border-blue-200">
              {insight}
            </span>
          ))}
        </div>
      </div>
    )
  }

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
      <div>
        <div className="text-sm font-medium text-gray-700 mb-1">Emotion:</div>
        <span className={`px-3 py-1 ${colorClass} text-sm rounded-full border inline-flex items-center gap-1`}>
          <span className="capitalize">{emotion}</span>
          {intensityStars && (
            <span className="text-yellow-500 ml-1">{intensityStars}</span>
          )}
        </span>
      </div>
    )
  }

  const renderFeatureBadge = (feature: string | null | undefined) => {
    if (!feature) return null
    return (
      <div>
        <div className="text-sm font-medium text-gray-700 mb-1">Related Feature:</div>
        <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-sm rounded-full border border-indigo-200">
          {feature}
        </span>
      </div>
    )
  }

  const renderSearchResults = () => {
    if (isLoading) {
      return (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Searching...</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="bg-red-50 text-red-700 p-4 rounded-md">
          {error}
        </div>
      )
    }

    if (results.length > 0) {
      return (
        <div className="space-y-6">
          <h2 className="text-xl font-bold">Search Results ({results.length} found)</h2>
          {results.map((result, index) => (
            <div key={result.chunk_id} className="bg-white rounded-lg shadow p-6">
              <div className="mb-4">
                <h3 className="text-lg font-medium text-indigo-600 hover:text-indigo-800">
                  {result.interviewee_name || 'Untitled Interview'}
                </h3>
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <div className="flex items-center space-x-4">
                    <span>Time Stamp: {result.timestamp || 'No Date'}</span>
                    <span>Similarity: {(result.similarity * 100).toFixed(2)}%</span>
                  </div>
                  {result.interview_id && (
                    <Link
                      to={`/annotated-transcript/${result.interview_id}?timestamp=${encodeURIComponent(result.timestamp)}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      View Annotated Transcript
                    </Link>
                  )}
                </div>
              </div>
              
              <div className="prose prose-sm max-w-none mb-4">
                <p className="text-gray-700">{result.content || 'No content available'}</p>
              </div>
              
              <div className="space-y-4 mt-4">
                {result.metadata.emotion && renderEmotionBadge(result.metadata.emotion, result.metadata.emotion_intensity)}
                {result.metadata.themes && result.metadata.themes.length > 0 && renderThemes(result.metadata.themes)}
                {result.metadata.insight_tags && result.metadata.insight_tags.length > 0 && renderInsights(result.metadata.insight_tags)}
                {result.metadata.related_feature && renderFeatureBadge(result.metadata.related_feature)}
              </div>

              <div className="mt-4 flex justify-between items-center">
                <div className="text-sm text-gray-500">
                  Project: {result.project_name || 'Unknown Project'}
                </div>
                <div className="flex space-x-4">
                  {result.interview_id && (
                    <Link
                      to={`/interview/${result.interview_id}`}
                      className="text-sm text-indigo-600 hover:text-indigo-800"
                    >
                      View Full Interview
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )
    }

    return searchQuery && !isLoading && !error && (
      <div className="bg-blue-50 text-blue-700 p-4 rounded-md">
        No results found. Try adjusting your search terms or using a different search type.
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Advanced Interview Search</h1>
      
      {/* Search Form */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Query
          </label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Try 'Show me moments of user frustration' or 'Positive stories with innovation'"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Type
          </label>
          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {searchTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <p className="mt-2 text-sm text-gray-500">
            {searchTypes.find(t => t.value === searchType)?.description}
          </p>
        </div>

        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Search Results */}
      {renderSearchResults()}
    </div>
  )
}

export default AdvancedSearch 