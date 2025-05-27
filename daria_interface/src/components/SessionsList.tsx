import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Session {
  id: string;
  title: string;
  project: string;
  topic: string;
  context: string;
  goals: string;
  created_at: string;
  updated_at: string;
  interview_type: string;
  name?: string;
}

const SessionsList: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:5025/api/sessions');
        const sessionsWithName = response.data.map((session: any) => ({
          ...session,
          name: session.interviewee?.name || '',
        }));
        setSessions(sessionsWithName);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch sessions');
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-md">
        {error}
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Interview Sessions</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200"
          >
            <div className="p-6">
              <h2 className="text-xl font-semibold mb-2">{session.title}</h2>
              <div className="text-sm text-gray-600 mb-4">
                <p>Project: {session.project}</p>
                <p>Topic: {session.topic}</p>
                <p>Type: {session.interview_type}</p>
                <p>Name: {session.name}</p>
                <p>Created: {new Date(session.created_at).toLocaleDateString()}</p>
              </div>
              <div className="mb-4">
                <h3 className="font-medium mb-1">Goals</h3>
                <p className="text-gray-700 text-sm">{session.goals}</p>
              </div>
              <div className="mb-4">
                <h3 className="font-medium mb-1">Context</h3>
                <p className="text-gray-700 text-sm">{session.context}</p>
              </div>
              <div className="mt-4">
                <button 
                  onClick={() => window.location.href = `/sessions/${session.id}`}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors duration-200"
                >
                  Session Details
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SessionsList; 