import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Tag } from 'antd';

interface Interview {
  id: string;
  title: string;
  participant_name: string;
  project_name: string;
  created_at: string;
  preview: string;
  type: string;
  status: string;
  themes?: string[];
  insights?: string[];
  emotions?: { name: string; count: number; avg_intensity: number }[];
}

const InterviewArchive: React.FC = () => {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Interview[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    // Fetch all interviews for archive
    axios.get('/api/search/exact?q=')
      .then(res => {
        setInterviews(res.data.interviews || []);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load interviews');
        setLoading(false);
      });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    axios.get(`/api/search/exact?q=${encodeURIComponent(search)}`)
      .then(res => {
        setSearchResults(res.data.interviews || []);
        setSearching(false);
      })
      .catch(() => {
        setError('Search failed');
        setSearching(false);
      });
  };

  const handleClearSearch = () => {
    setSearch('');
    setSearchResults(null);
  };

  const handleCopyLink = (id: string) => {
    const url = `${window.location.origin}/transcript/${id}`;
    navigator.clipboard.writeText(url);
    alert('Link copied to clipboard!');
  };

  const handleDelete = (id: string) => {
    alert('Delete feature not implemented yet.');
  };

  const renderCard = (interview: Interview) => {
    // Get top 1-2 emotions for display
    const topEmotions = interview.emotions?.slice(0, 2).map(e => e.name) || [];
    const allTags = [...(interview.themes || []), ...(interview.insights || []), ...topEmotions];

    return (
      <div key={interview.id} className="bg-white rounded-lg shadow p-6 flex flex-col justify-between min-h-[250px] transition-all duration-200 hover:shadow-lg">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-semibold">{interview.project_name}</span>
            <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">{interview.status}</span>
          </div>
          <h3 className="text-lg font-bold mb-1">{interview.project_name}</h3>
          <div className="text-sm text-gray-500 mb-1">{interview.type}</div>
          <div className="text-xs text-gray-400 mb-1">{interview.created_at.split('T')[0]}</div>
          <div className="text-gray-700 text-sm mb-3 line-clamp-3">{interview.preview}</div>
          
          {/* Semantic Tags Section */}
          <div className="flex flex-wrap gap-1 mb-3">
            {allTags.slice(0, 5).map((tag, index) => ( // Limit displayed tags
              <Tag key={`${tag}-${index}`} color="blue">{tag}</Tag>
            ))}
            {allTags.length > 5 && <Tag>...</Tag>}
          </div>
        </div>
        
        {/* Action Icons */}
        <div className="flex gap-4 mt-auto border-t pt-3 text-gray-500 text-xl justify-between">
          <Link to={`/transcript/${interview.id}`} title="View Full Interview" className="hover:text-indigo-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-7.5A2.25 2.25 0 0017.25 4.5h-10.5A2.25 2.25 0 004.5 6.75v10.5A2.25 2.25 0 006.75 19.5h7.5" /><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 17.25L21 21.75M21 21.75L16.5 26.25M21 21.75H9" /></svg>
          </Link>
          <button title="View Analysis (not implemented)" className="hover:text-indigo-600 transition-colors" disabled>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18" /><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15.75V12m3 3.75V9m3 6.75V6" /></svg>
          </button>
          <Link to={`/annotated-transcript/${interview.id}`} title="View Annotated Transcript" className="hover:text-indigo-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6v-1.5A2.25 2.25 0 0013.5 2.25h-3A2.25 2.25 0 008.25 4.5V6m7.5 0v1.5m0-1.5h-7.5m7.5 0h1.5A2.25 2.25 0 0121 8.25v11.25A2.25 2.25 0 0118.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6h1.5m0 0V4.5A2.25 2.25 0 018.25 2.25h3A2.25 2.25 0 0113.5 4.5V6" /></svg>
          </Link>
          <button title="Copy Link" onClick={() => handleCopyLink(interview.id)} className="hover:text-indigo-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7.5 3.75A2.25 2.25 0 006.75 21h10.5A2.25 2.25 0 0019.5 18.75V8.25A2.25 2.25 0 0017.25 6H6.75A2.25 2.25 0 004.5 8.25v10.5z" /></svg>
          </button>
          <button title="Delete (not implemented)" onClick={() => handleDelete(interview.id)} className="hover:text-red-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Interview Archive</h1>
        <p className="text-sm text-gray-600">
          Total interviews: {interviews.length}
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12">Loading...</div>
      ) : error ? (
        <div className="text-center text-red-500 py-12">{error}</div>
      ) : (
        <div className="space-y-8">
          {/* All Interviews Section - Always shown first */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            {interviews.map(renderCard)}
          </div>

          {/* Search Section */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  className="border rounded px-3 py-2 w-full pr-10 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Search interviews..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
              <button 
                type="submit" 
                className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Search
              </button>
            </form>
          </div>

          {/* Search Results Section - Only shown when there are search results */}
          {searchResults !== null && (
            <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Search Results</h2>
                  <p className="text-sm text-gray-600">
                    Found {searchResults.length} match{searchResults.length !== 1 ? 'es' : ''} for "{search}"
                  </p>
                </div>
                <button
                  onClick={handleClearSearch}
                  className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <span>Clear search</span>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {searching ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
                  <p className="mt-2 text-gray-600">Searching...</p>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="text-center py-8 bg-white rounded-lg border border-gray-100">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 mx-auto text-gray-400 mb-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  <p className="text-gray-500">No results found for "{search}"</p>
                  <p className="text-sm text-gray-400 mt-1">Try adjusting your search terms</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                  {searchResults.map(renderCard)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default InterviewArchive; 