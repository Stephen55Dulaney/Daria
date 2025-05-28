import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import SessionCard from '../components/shared/SessionCard';
import TranscriptTab from '../components/TranscriptTab';
import AnalysisTab from '../components/AnalysisTab';
import SemanticSearchTab from '../components/shared/SemanticSearchTab';
import AnnotationsTab from '../components/AnnotationsTab'; // To be created
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
  analysis?: { content: string };
}

const SessionDetailPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'analysis' | 'annotations' | 'semantic'>('transcript');

  useEffect(() => {
    const fetchSession = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`http://127.0.0.1:5025/api/research_session/${sessionId}`);
        setSession(response.data);
      } catch (err: any) {
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
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row gap-8">
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
            <button
              className={`pb-2 px-4 font-semibold ${activeTab === 'annotations' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
              onClick={() => setActiveTab('annotations')}
            >
              Annotations
            </button>
            <button
              className={`pb-2 px-4 font-semibold ${activeTab === 'semantic' ? 'border-b-2 border-purple-600 text-purple-700' : 'text-gray-500'}`}
              onClick={() => setActiveTab('semantic')}
            >
              Semantic Search
            </button>
          </div>
          {activeTab === 'transcript' && (
            <TranscriptTab messages={session.session.messages || []} />
          )}
          {activeTab === 'analysis' && (
            <AnalysisTab analysis={session.session.analysis} />
          )}
          {activeTab === 'annotations' && (
            <AnnotationsTab messages={session.session.messages || []} sessionId={session.session.id} />
          )}
          {activeTab === 'semantic' && (
            <SemanticSearchTab />
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionDetailPage; 