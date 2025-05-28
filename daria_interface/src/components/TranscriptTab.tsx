// TranscriptTab.tsx
import React from 'react';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
}

interface TranscriptTabProps {
  messages: Message[];
}

const TranscriptTab: React.FC<TranscriptTabProps> = ({ messages }) => {
  return (
    <div>
      {messages.length === 0 ? (
        <div className="text-gray-500 italic">No messages available.</div>
      ) : (
        <ul>
          {messages.map((msg) => (
            <li key={msg.id} className="mb-2">
              <strong>{msg.role}:</strong> {msg.content}
              <span className="text-xs text-gray-400 ml-2">{msg.timestamp}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TranscriptTab;