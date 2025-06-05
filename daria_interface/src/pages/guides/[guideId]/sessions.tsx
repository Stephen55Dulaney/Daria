import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import SessionCard from '../../../components/shared/SessionCard';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

interface Session {
  id: string;
  title: string;
  project?: string;
  name?: string;
  interview_type?: string;
  character?: string;
  created_at: string;
  status?: string;
  participant_name?: string;
  messages?: any[];
  interviewee?: {
    name?: string;
    email?: string;
    role?: string;
    department?: string;
  };
  duration?: string;
  transcript_length?: number;
}

interface GuideDetails {
  id: string;
  title: string;
  project: string;
}

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex justify-between text-sm text-gray-600">
    <span className="font-medium">{label}:</span>
    <span>{value}</span>
  </div>
);

const GuideSessions: React.FC = () => {
  // Get guideId from URL
  const { guideId } = useParams();
  const navigate = useNavigate();
  
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
        const guideResponse = await axios.get<{ guide: GuideDetails }>(
          `${API_BASE_URL}/api/discussion_guide/${guideId}`
        );
        setGuide(guideResponse.data.guide);
        
        // Fetch sessions for this guide
        const sessionsResponse = await axios.get<{ sessions: Session[] }>(
          `${API_BASE_URL}/api/discussion_guide/${guideId}/sessions`
        );
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
    navigate(`/guides/${guideId}/sessions/${session.id}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading data</h3>
            <div className="mt-2 text-sm text-red-700">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Sessions for {guide?.title}
            </h1>
            {guide && (
              <p className="mt-1 text-sm text-gray-500">
                Project: {guide.project}
              </p>
            )}
          </div>
          <button
            onClick={() => navigate('/guides')}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            ← Back to Guide
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.map((session) => (
          <SessionCard
            key={session.id}
            session={session}
            onClick={() => handleSessionClick(session)}
          >
            {session.interviewee && (
              <div className="mb-2">
                <div className="font-semibold">Participant Information</div>
                <InfoRow label="Name" value={session.interviewee.name || 'N/A'} />
                <InfoRow label="Email" value={session.interviewee.email || 'N/A'} />
                <InfoRow label="Role" value={session.interviewee.role || 'N/A'} />
                <InfoRow label="Department" value={session.interviewee.department || 'N/A'} />
              </div>
            )}

            <div className="mb-2">
              <div className="font-semibold">Session Stats</div>
              <InfoRow label="Duration" value={session.duration || 'N/A'} />
              <InfoRow label="Messages" value={Array.isArray(session.messages) ? session.messages.length.toString() : '0'} />
              <InfoRow label="Transcript Length" value={
                typeof session.transcript_length === 'number'
                  ? `${(session.transcript_length / 1000).toFixed(1)}k characters`
                  : '0.0k characters'
              } />
            </div>
            <InfoRow label="Session ID" value={session.id} />
          </SessionCard>
        ))}
      </div>

      {sessions.length === 0 && (
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No sessions</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by creating a new interview session for this guide.
          </p>
          <div className="mt-6">
            <button
              type="button"
              onClick={() => navigate(`/guides/${guideId}/sessions/new`)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <svg
                className="-ml-1 mr-2 h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clipRule="evenodd"
                />
              </svg>
              Create New Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GuideSessions; 