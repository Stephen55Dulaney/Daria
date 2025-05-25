import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

interface Message {
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
}

interface Session {
  id: string;
  title: string;
  project?: string;
  interview_type?: string;
  character?: string;
  created_at: string;
  status: string;
  participant_name?: string;
  messages: Message[];
  transcript?: string;
}

export default function SessionDetail() {
  const router = useRouter();
  const { guideId, sessionId } = router.query;
  
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      if (!sessionId || !guideId) return;
      
      try {
        setLoading(true);
        const response = await axios.get<{ session: Session }>(
          `http://127.0.0.1:5025/api/discussion_guide/${guideId}/sessions/${sessionId}`
        );
        setSession(response.data.session);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch session');
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, [sessionId, guideId]);

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

  if (!session) {
    return (
      <div className="p-4 text-gray-600">
        Session not found
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{session.title}</h1>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            ← Back to Sessions
          </button>
        </div>
        
        <div className="mt-4 space-y-2 text-sm text-gray-600">
          {session.project && <p>Project: {session.project}</p>}
          {session.interview_type && <p>Type: {session.interview_type}</p>}
          {session.character && <p>Character: {session.character}</p>}
          {session.participant_name && <p>Participant: {session.participant_name}</p>}
          <p>Created: {formatDate(session.created_at)}</p>
          <p>Status: <span className={`font-medium ${session.status === 'active' ? 'text-green-600' : 'text-gray-600'}`}>{session.status}</span></p>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Transcript</h2>
        {session.messages.length > 0 ? (
          <div className="space-y-4">
            {session.messages.map((message, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-50 ml-8'
                    : 'bg-gray-50 mr-8'
                }`}
              >
                <div className="flex items-center mb-2">
                  <span className="font-medium text-sm text-gray-600">
                    {message.role === 'user' ? 'Participant' : session.character || 'Assistant'}
                  </span>
                  <span className="ml-2 text-xs text-gray-500">
                    {formatDate(message.timestamp)}
                  </span>
                </div>
                <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
              </div>
            ))}
          </div>
        ) : session.transcript ? (
          <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg text-gray-800">
            {session.transcript}
          </pre>
        ) : (
          <p className="text-gray-600">No transcript available</p>
        )}
      </div>
    </div>
  );
} 