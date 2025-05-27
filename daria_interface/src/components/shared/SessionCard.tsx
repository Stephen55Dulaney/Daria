import React from 'react';
import InfoRow from './InfoRow';
import { Link } from 'react-router-dom';

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

interface SessionCardProps {
  session: Session;
  hideDetailsButton?: boolean;
  onViewTranscript?: (session: Session) => void;
  className?: string;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, hideDetailsButton, onViewTranscript, className = '' }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleCopyId = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(session.id);
  };

  return (
    <div 
      className={`p-4 border rounded-lg shadow-sm bg-white hover:shadow-md transition-shadow hover:border-purple-400 ${className}`}
    >
      <div className="flex justify-between items-start mb-3">
        <h2 className="text-xl font-semibold text-gray-900">{session.title || 'Untitled Session'}</h2>
        {session.status && (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            session.status.toLowerCase() === 'active' 
              ? 'bg-purple-100 text-purple-800'
              : 'bg-gray-100 text-gray-800'
          }`}>
            {session.status}
          </span>
        )}
      </div>

      {/* Participant Information */}
      {session.interviewee && (
        <div className="mb-2">
          <div className="font-semibold">Participant Information</div>
          <InfoRow label="Name" value={session.interviewee.name || 'N/A'} />
          <InfoRow label="Email" value={session.interviewee.email || 'N/A'} />
          <InfoRow label="Role" value={session.interviewee.role || 'N/A'} />
          <InfoRow label="Department" value={session.interviewee.department || 'N/A'} />
        </div>
      )}

      {/* Session Stats */}
      <div className="mb-2">
        <div className="font-semibold">Session Stats </div>
        <InfoRow label="Duration" value={session.duration || 'N/A'} />
        <InfoRow label="Messages" value={Array.isArray(session.messages) ? session.messages.length.toString() : '0'} />
        <InfoRow label="Transcript Length" value={
          typeof session.transcript_length === 'number'
            ? `${(session.transcript_length / 1000).toFixed(1)}k characters`
            : '0.0k characters'
        } />
      </div>

      <div className="space-y-2">
        {session.project && (
          <InfoRow label="Project" value={session.project} />
        )}
        {session.interview_type && (
          <InfoRow label="Type" value={session.interview_type} />
        )}
        {session.name && (
          <InfoRow label="Interviewee" value={session.name} />
        )}
        {session.character && (
          <InfoRow label="Character" value={session.character} />
        )}
        {session.participant_name && (
          <InfoRow label="Participant" value={session.participant_name} />
        )}
        <InfoRow label="Created" value={formatDate(session.created_at)} />
        <div className="flex items-center gap-2">
          <InfoRow label="Session ID" value={session.id} />
          <button
            title="Copy ID"
            onClick={handleCopyId}
            className="ml-1 px-2 py-1 text-xs border rounded hover:bg-gray-100"
          >
            📋
          </button>
        </div>
        {Array.isArray(session.messages) && session.messages.length > 0 && (
          <div className="text-xs text-gray-500 italic mt-1">
            “{session.messages[0].content.slice(0, 60)}{session.messages[0].content.length > 60 ? '…' : ''}”
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mt-4">
        {!hideDetailsButton && (
          <Link
            to={`/sessions/${session.id}`}
            className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600 transition-colors flex items-center gap-1"
          >
            <span role="img" aria-label="details">📄</span> Session Details
          </Link>
        )}
        {/* Placeholder buttons for future features */}
        <button
          className="bg-gray-200 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-300 transition-colors flex items-center gap-1"
          disabled
        >
          <span role="img" aria-label="semantic">🔖</span> Semantic Transcript
        </button>
        <button
          className="bg-purple-200 text-purple-700 px-3 py-1 rounded text-sm hover:bg-purple-300 transition-colors flex items-center gap-1"
          disabled
        >
          <span role="img" aria-label="analysis">📊</span> View Analysis
        </button>
        <button
          className="bg-red-200 text-red-700 px-3 py-1 rounded text-sm hover:bg-red-300 transition-colors flex items-center gap-1"
          disabled
        >
          <span role="img" aria-label="delete">🗑️</span> Delete
        </button>
      </div>
    </div>
  );
};

export default SessionCard; 