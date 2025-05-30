import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import SessionCard from '../../../components/shared/SessionCard';

interface Session {
  id: string;
  title: string;
  project?: string;
  interview_type?: string;
  character?: string;
  created_at: string;
  status: string;
  participant_name?: string;
}

interface GuideDetails {
  id: string;
  title: string;
  project: string;
}

interface GuideResponse {
  guide: GuideDetails;
}

interface SessionsResponse {
  sessions: Session[];
}

export default function GuideSessions() {
  const router = useRouter();
  const { guideId } = router.query;
  
  const [sessions, setSessions] = useState<Session[]>([]);
  const [guide, setGuide] = useState<GuideDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!guideId) return;
      
      try {
        setLoading(true);
        
        // Fetch guide details
        const guideResponse = await axios.get<GuideResponse>(`http://127.0.0.1:5025/api/discussion_guide/${guideId}`);
        setGuide(guideResponse.data.guide);
        
        // Fetch sessions for this guide
        const sessionsResponse = await axios.get<SessionsResponse>(`http://127.0.0.1:5025/api/discussion_guide/${guideId}/sessions`);
        setSessions(sessionsResponse.data.sessions);
        
      } catch (err: any) {
        setError(err.message || 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guideId]);

  const handleSessionClick = (session: Session) => {
    router.push(`/guides/${guideId}/sessions/${session.id}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded-md">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            Sessions for {guide?.title}
          </h1>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            ← Back to Guide
          </button>
        </div>
        {guide && (
          <p className="text-gray-600 mt-2">
            Project: {guide.project}
          </p>
        )}
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-600">No sessions found for this guide.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onClick={() => handleSessionClick(session)}
            />
          ))}
        </div>
      )}
    </div>
  );
} 