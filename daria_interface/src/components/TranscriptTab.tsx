// TranscriptTab.tsx
import React from 'react';

interface Message {
  content: string;
  role: string;
  timestamp: string;
}

interface TranscriptTabProps {
  messages: Message[];
}

const TranscriptTab: React.FC<TranscriptTabProps> = ({ messages }) => {
  // Helper to format the timestamp
  const formatTime = (ts: string) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <div>
      {messages.length === 0 ? (
        <div className="text-gray-500">No transcript available.</div>
      ) : (
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg ${msg.role === 'user' || msg.role === 'participant' ? 'bg-blue-50' : 'bg-gray-50'}`}
              style={{ maxWidth: 600, marginLeft: msg.role === 'user' || msg.role === 'participant' ? 'auto' : 0 }}
            >
              <div className="flex items-center mb-1">
                <span className="font-semibold">
                  {msg.role === 'user' || msg.role === 'participant' ? 'Participant' : 'Moderator'}
                </span>
                <span className="ml-2 text-xs text-gray-500">{formatTime(msg.timestamp)}</span>
              </div>
              <div className="text-gray-900">{msg.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TranscriptTab;