import React, { useState } from 'react';
import axios from 'axios';

interface SearchResult {
  content: string;
  // Add other properties if needed, e.g., score, metadata, etc.
}

const SemanticSearchTab: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);

  const handleSearch = async () => {
    const response = await axios.post('/api/semantic_search', { query });
    setResults(response.data);
  };

  const docs = Array.isArray(results) ? results : (results.documents && Array.isArray(results.documents[0]) ? results.documents[0] : []);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSearch();
        }}
        placeholder="Search transcript..."
        className="border p-2 rounded"
      />
      <button onClick={handleSearch} className="bg-blue-500 text-white px-4 py-2 rounded ml-2">
        Search
      </button>
      <div className="mt-4">
        {docs.length === 0 ? (
          <div>No results found.</div>
        ) : (
          docs.map((result, index) => (
            <div key={index}>{result}</div>
          ))
        )}
      </div>
    </div>
  );
};

export default SemanticSearchTab;
