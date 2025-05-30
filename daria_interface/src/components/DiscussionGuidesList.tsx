import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DiscussionGuideCard from './DiscussionGuideCard';
import { useNavigate } from 'react-router-dom';

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
  interviewee?: {
    name: string;
    role: string;
    email: string;
  };
  options?: {
    record_transcript: boolean;
    analysis: boolean;
    use_tts: boolean;
  };
  expiration_date?: string;
}

interface DiscussionGuidesResponse {
  guides: DiscussionGuide[];
  success: boolean;
}

const DiscussionGuidesList: React.FC = () => {
  const [guides, setGuides] = useState<DiscussionGuide[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchGuides = async () => {
      try {
        const response = await axios.get<DiscussionGuidesResponse>('http://127.0.0.1:5025/api/discussion_guides');
        setGuides(response.data.guides);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch discussion guides');
      } finally {
        setLoading(false);
      }
    };

    fetchGuides();
  }, []);

  const handleViewGuide = (guideId: string) => {
    navigate(`/guides/${guideId}`);
  };

  const handleDeleteGuide = async (guideId: string) => {
    if (!window.confirm('Are you sure you want to delete this guide?')) {
      return;
    }

    try {
      await axios.delete(`http://127.0.0.1:5025/api/discussion_guide/${guideId}`);
      setGuides(guides.filter(g => g.id !== guideId));
    } catch (err: any) {
      console.error('Failed to delete guide:', err);
      alert('Failed to delete guide: ' + (err.message || 'Unknown error'));
    }
  };

  if (loading) return <div className="p-4">Loading discussion guides...</div>;
  if (error) return <div className="p-4 text-red-600">Error: {error}</div>;

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Discussion Guides</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {guides.map((guide) => (
          <DiscussionGuideCard
            key={guide.id}
            guide={guide}
            onViewGuide={handleViewGuide}
            onDelete={handleDeleteGuide}
          />
        ))}
      </div>
    </div>
  );
};

export default DiscussionGuidesList; 