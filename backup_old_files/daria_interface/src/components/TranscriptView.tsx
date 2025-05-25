import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface Transcript {
  id: string;
  title: string;
  project: string;
  topic: string;
  context: string;
  goals: string;
  messages: Message[];
  analysis: any;
  created_at: string;
  updated_at: string;
}

const TranscriptView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTranscript = async () => {
      try {
        const response = await axios.get(`http://127.0.0.1:5025/api/transcript/${id}`);
        setTranscript(response.data);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch transcript');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchTranscript();
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !transcript) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-md">
        {error || 'Failed to load transcript'}
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">{transcript.title}</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <p>Project: {transcript.project}</p>
            <p>Topic: {transcript.topic}</p>
            <p>Created: {new Date(transcript.created_at).toLocaleString()}</p>
          </div>
          <div>
            <p>Goals: {transcript.goals}</p>
            <p>Context: {transcript.context}</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {transcript.messages.map((message) => (
          <div
            key={message.id}
            className={`p-4 rounded-lg ${
              message.role === 'assistant'
                ? 'bg-blue-50 ml-4'
                : message.role === 'user'
                ? 'bg-gray-50 mr-4'
                : 'bg-yellow-50'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="font-medium">
                {message.role === 'assistant' ? 'Moderator' : 
                 message.role === 'user' ? 'Participant' : 'System'}
              </span>
              <span className="text-sm text-gray-500">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        ))}
      </div>

      {transcript.analysis && (
        <div className="mt-8 p-6 bg-gray-50 rounded-lg">
          <h2 className="text-2xl font-bold mb-4">Analysis</h2>
          <div className="whitespace-pre-wrap">
            {typeof transcript.analysis === 'string' 
              ? transcript.analysis 
              : JSON.stringify(transcript.analysis, null, 2)}
          </div>
        </div>
      )}
    </div>
  );
};

export default TranscriptView; 