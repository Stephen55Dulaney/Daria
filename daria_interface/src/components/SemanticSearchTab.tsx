import React, { useState } from 'react';
import axios from 'axios';

interface SearchResult {
  content: string;
  metadata?: {
    session_id: string;
    themes?: string[];
    insight_tags?: string[];
    emotion?: string;
    emotion_intensity?: number;
    sentiment_score?: number;
  };
  score?: number;
}

interface SemanticSearchTabProps {
  sessionId: string;
}

const SemanticSearchTab: React.FC<SemanticSearchTabProps> = ({ sessionId }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [debugInfo, setDebugInfo] = useState<{
    rawResults?: SearchResult[];
    currentSessionId?: string;
  }>({});

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setError(null);
    try {
      console.log('Searching with session ID:', sessionId);
      const response = await axios.post('/api/semantic_search', { query, session_id: sessionId });
      const allResults = response.data.results || [];
      setTotalResults(allResults.length);
      
      // Store debug info
      setDebugInfo({
        rawResults: allResults,
        currentSessionId: sessionId
      });
      
      // Filter results to only include those from the current session
      const filteredResults = allResults.filter(
        (result: SearchResult) => result.metadata?.session_id === sessionId
      );
      console.log('Filtered results:', filteredResults);
      setResults(filteredResults);
    } catch (err) {
      setError('Failed to perform search. Please try again.');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getEmotionColor = (emotion?: string) => {
    if (!emotion) return 'gray';
    const colors: { [key: string]: string } = {
      positive: 'green',
      negative: 'red',
      neutral: 'gray',
      frustration: 'orange'
    };
    return colors[emotion] || 'gray';
  };

  return (
    <div className="p-4">
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch();
          }}
          placeholder="Search transcript..."
          className="flex-1 border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button 
          onClick={handleSearch} 
          disabled={isLoading}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300 transition-colors"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {totalResults > 0 && results.length === 0 && (
        <div className="mb-4 p-3 bg-yellow-100 text-yellow-700 rounded">
          Found {totalResults} results across all sessions, but none in the current session.
          <div className="text-xs mt-2">
            Current session ID: {sessionId}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {results.length === 0 && !isLoading && !error ? (
          <div className="text-gray-500 text-center py-8">
            No results found. Try a different search term.
          </div>
        ) : (
          results.map((result, index) => (
            <div key={index} className="bg-white rounded-lg shadow p-4 border border-gray-200">
              <div className="font-mono whitespace-pre-line mb-3">{result.content}</div>
              
              <div className="flex flex-wrap gap-2 mb-2">
                {result.metadata?.themes?.map((theme, i) => (
                  <span key={`theme-${i}`} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                    {theme}
                  </span>
                ))}
                {result.metadata?.insight_tags?.map((tag, i) => (
                  <span key={`insight-${i}`} className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                    {tag}
                  </span>
                ))}
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-500">
                {result.metadata?.emotion && (
                  <span className={`px-2 py-1 bg-${getEmotionColor(result.metadata.emotion)}-100 text-${getEmotionColor(result.metadata.emotion)}-800 rounded`}>
                    {result.metadata.emotion}
                  </span>
                )}
                {result.score !== undefined && (
                  <span>Relevance: {(result.score * 100).toFixed(1)}%</span>
                )}
                {result.metadata?.sentiment_score !== undefined && (
                  <span>Sentiment: {(result.metadata.sentiment_score * 100).toFixed(1)}%</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Debug Information */}
      {process.env.NODE_ENV === 'development' && debugInfo.rawResults && (
        <div className="mt-8 p-4 bg-gray-100 rounded">
          <h3 className="font-bold mb-2">Debug Information</h3>
          <div className="text-xs">
            <div>Current Session ID: {debugInfo.currentSessionId}</div>
            <div>Total Results: {debugInfo.rawResults.length}</div>
            <div>Filtered Results: {results.length}</div>
            <div className="mt-2">
              <div className="font-semibold">Raw Results:</div>
              <pre className="whitespace-pre-wrap">
                {JSON.stringify(debugInfo.rawResults, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SemanticSearchTab;
