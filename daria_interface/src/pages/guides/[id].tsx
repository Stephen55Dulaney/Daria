import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

interface DiscussionGuide {
  id: string;
  title: string;
  project: string;
  interview_type: string;
  sessions: string[];
  created_at: string;
  updated_at: string;
  status: string;
  character_select?: string;
}

const GuideDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [guide, setGuide] = useState<DiscussionGuide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGuide = async () => {
      try {
        const response = await axios.get<{ guide: DiscussionGuide }>(`http://127.0.0.1:5025/api/discussion_guide/${id}`);
        setGuide(response.data.guide);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch guide');
      } finally {
        setLoading(false);
      }
    };
    fetchGuide();
  }, [id]);

  if (loading) return <div className="p-4">Loading guide...</div>;
  if (error) return <div className="p-4 text-red-600">Error: {error}</div>;
  if (!guide) return <div className="p-4">Guide not found.</div>;

  return (
    <div className="p-6 max-w-2xl mx-auto bg-white rounded shadow">
      <button onClick={() => navigate(-1)} className="mb-4 text-violet-700 hover:underline">&larr; Back to Guides</button>
      <h1 className="text-3xl font-bold mb-2">{guide.title}</h1>
      <div className="mb-2 text-gray-600">Project: {guide.project}</div>
      <div className="mb-2 text-gray-600">Type: {guide.interview_type}</div>
      <div className="mb-2 text-gray-600">Status: {guide.status}</div>
      {guide.character_select && <div className="mb-2">Character: {guide.character_select}</div>}
      <div className="mb-2">Created: {new Date(guide.created_at).toLocaleString()}</div>
      <div className="mb-2">Last Updated: {new Date(guide.updated_at).toLocaleString()}</div>
      <div className="mb-2">Guide ID: <span className="font-mono text-xs">{guide.id}</span></div>
      <div className="mt-4">
        <h2 className="text-xl font-semibold mb-2">Sessions</h2>
        {guide.sessions.length === 0 ? (
          <div className="text-gray-500">No sessions linked to this guide.</div>
        ) : (
          <ul className="list-disc pl-6">
            {guide.sessions.map(sessionId => (
              <li key={sessionId} className="font-mono text-xs">{sessionId}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default GuideDetailPage; 