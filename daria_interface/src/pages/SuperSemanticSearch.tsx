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

const SuperSemanticSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessions, setSessions] = useState<{ id: string; name: string }[]>([]);

  // Fetch available sessions on component mount
  React.useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await axios.get('/api/sessions');
        setSessions(response.data.map((session: any) => ({
          id: session.id,
          name: session.name || `Session ${session.id.slice(0, 8)}`
        })));
      } catch (err) {
        console.error('Error fetching sessions:', err);
      }
    };
    fetchSessions();
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/semantic_search', { 
        query,
        session_id: selectedSession || undefined // Only include if a session is selected
      });
      setResults(response.data.results || []);
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
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-4">Super Semantic Search</h1>
        <p className="text-gray-600 mb-4">
          Search across all interview transcripts using semantic understanding. Find relevant content based on meaning, not just keywords.
        </p>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSearch();
            }}
            placeholder="Search across all transcripts..."
            className="w-full border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={selectedSession || ''}
          onChange={(e) => setSelectedSession(e.target.value || null)}
          className="border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Sessions</option>
          {sessions.map(session => (
            <option key={session.id} value={session.id}>
              {session.name}
            </option>
          ))}
        </select>
        <button 
          onClick={handleSearch} 
          disabled={isLoading}
          className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300 transition-colors"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
          {error}
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
              <div className="flex justify-between items-start mb-2">
                <div className="font-mono whitespace-pre-line">{result.content}</div>
                {result.metadata?.session_id && (
                  <span className="ml-4 px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                    {sessions.find(s => s.id === result.metadata?.session_id)?.name || 'Unknown Session'}
                  </span>
                )}
              </div>
              
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
    </div>
  );
};

export default SuperSemanticSearch; 