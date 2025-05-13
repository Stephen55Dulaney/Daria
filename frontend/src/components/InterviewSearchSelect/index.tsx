import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Checkbox, Tag } from 'antd';

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

interface InterviewSearchSelectProps {
  onSelectionChange: (selectedInterviewIds: string[]) => void;
  selectedInterviewIds?: string[];
}

const InterviewSearchSelect: React.FC<InterviewSearchSelectProps> = ({ 
  onSelectionChange,
  selectedInterviewIds = []
}) => {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Interview[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<string[]>(selectedInterviewIds);

  useEffect(() => {
    // Fetch all interviews for selection
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

  // Update parent component when selection changes
  useEffect(() => {
    onSelectionChange(selected);
  }, [selected, onSelectionChange]);

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

  const handleSelect = (id: string) => {
    setSelected(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id);
      } else {
        return [...prev, id];
      }
    });
  };

  const renderInterviewCard = (interview: Interview) => {
    // Get top 1-2 emotions for display
    const topEmotions = interview.emotions?.slice(0, 2).map(e => e.name) || [];
    const allTags = [...(interview.themes || []), ...(interview.insights || []), ...topEmotions];
    const isSelected = selected.includes(interview.id);

    return (
      <div 
        key={interview.id} 
        className={`bg-white rounded-lg shadow p-4 flex flex-col justify-between min-h-[180px] transition-all duration-200 hover:shadow-lg border-2 ${isSelected ? 'border-indigo-500' : 'border-transparent'}`}
        onClick={() => handleSelect(interview.id)}
      >
        <div className="flex items-start">
          <Checkbox 
            checked={isSelected} 
            className="mt-1 mr-3" 
            onChange={() => handleSelect(interview.id)}
            onClick={(e) => e.stopPropagation()}
          />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-semibold">{interview.project_name}</span>
              <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">{interview.status}</span>
            </div>
            <h3 className="text-md font-bold mb-1">{interview.project_name}</h3>
            <div className="text-sm text-gray-500 mb-1">{interview.type}</div>
            <div className="text-xs text-gray-400 mb-1">{interview.created_at.split('T')[0]}</div>
            <div className="text-gray-700 text-sm mb-3 line-clamp-2">{interview.preview}</div>
            
            {/* Semantic Tags Section */}
            <div className="flex flex-wrap gap-1 mb-2">
              {allTags.slice(0, 3).map((tag, index) => (
                <Tag key={`${tag}-${index}`} color="blue">{tag}</Tag>
              ))}
              {allTags.length > 3 && <Tag>...</Tag>}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const displayInterviews = searchResults || interviews;

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      {/* Search Form */}
      <div className="mb-4">
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
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Search
          </button>
        </form>
        
        {searchResults !== null && (
          <div className="flex justify-between items-center my-2">
            <p className="text-sm text-gray-600">
              Found {searchResults.length} match{searchResults.length !== 1 ? 'es' : ''} 
              {search ? ` for "${search}"` : ''}
            </p>
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
        )}
      </div>

      {/* Selected Count */}
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700">
          {selected.length} interview{selected.length !== 1 ? 's' : ''} selected
        </p>
      </div>
      
      {/* Interview Cards */}
      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
          <p className="mt-2 text-gray-600">Loading interviews...</p>
        </div>
      ) : error ? (
        <div className="text-center text-red-500 py-8">{error}</div>
      ) : searching ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
          <p className="mt-2 text-gray-600">Searching...</p>
        </div>
      ) : displayInterviews.length === 0 ? (
        <div className="text-center py-8 bg-white rounded-lg border border-gray-100">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 mx-auto text-gray-400 mb-3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <p className="text-gray-500">No interviews found</p>
          {search && <p className="text-sm text-gray-400 mt-1">Try adjusting your search terms</p>}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {displayInterviews.map(renderInterviewCard)}
        </div>
      )}
    </div>
  );
};

export default InterviewSearchSelect; 