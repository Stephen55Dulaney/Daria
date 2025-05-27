import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import SessionCard from '../components/shared/SessionCard';
import MessageList from '../components/shared/MessageList';
import axios from 'axios';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface Session {
  session: Session;
  id: string;
  title: string;
  project?: string;
  interview_type?: string;
  character?: string;
  created_at: string;
  status?: string;
  participant_name?: string;
  messages?: Message[];
}

const SessionDetailPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'analysis'>('transcript');

  useEffect(() => {
    const fetchSession = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`http://127.0.0.1:5025/api/research_session/${sessionId}`);
        console.log('API Response:', response.data); // Debug log
        setSession(response.data);
      } catch (err: any) {
        console.error('Error fetching session:', err); // Debug log
        setError(err.message || 'Failed to fetch session');
      } finally {
        setLoading(false);
      }
    };
    if (sessionId) fetchSession();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-md">
        {error || 'Failed to load session'}
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row gap-8 container mx-auto px-4 py-8">
      <div className="md:w-1/3 w-full mb-8 md:mb-0">
        
        <SessionCard session={session.session} hideDetailsButton />
      </div>
      <div className="md:w-2/3 w-full">
        <div className="flex gap-4 border-b mb-4">
          <button
            className={`pb-2 px-4 font-semibold ${activeTab === 'transcript' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
            onClick={() => setActiveTab('transcript')}
          >
            Transcript
          </button>
          <button
            className={`pb-2 px-4 font-semibold ${activeTab === 'analysis' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
            onClick={() => setActiveTab('analysis')}
          >
            Analysis
          </button>
        </div>
        {activeTab === 'transcript' ? (
          <MessageList messages={session.session.messages || []} />
        ) : (
          <div className="prose max-w-none">
            {session.session.analysis?.content
              ? <pre className="whitespace-pre-wrap">{session.session.analysis.content}</pre>
              : <div className="text-gray-500 italic">No analysis available</div>
            }
          </div>
        )}
      </div>
    </div>
    
  );
};

export default SessionDetailPage; 