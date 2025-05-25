import React from 'react';
import Badge from './Badge';
import InfoRow from './InfoRow';
import CopyableText from './CopyableText';

interface Session {
  id: string;
  title: string;
  project?: string;
  interview_type?: string;
  character?: string;
  created_at: string;
  status?: string;
  participant_name?: string;
}

interface SessionCardProps {
  session: Session;
  onClick?: (session: SessionCardProps['session']) => void;
  className?: string;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onClick, className = '' }) => {
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
    <div 
      className={`p-4 border rounded-lg shadow-sm bg-white hover:shadow-md transition-shadow hover:border-purple-400 ${className}`}
      onClick={() => onClick?.(session)}
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

      <div className="space-y-2">
        {session.project && (
          <InfoRow label="Project" value={session.project} />
        )}
        {session.interview_type && (
          <InfoRow label="Type" value={session.interview_type} />
        )}
        {session.character && (
          <InfoRow label="Character" value={session.character} />
        )}
        {session.participant_name && (
          <InfoRow label="Participant" value={session.participant_name} />
        )}
        <InfoRow label="Created" value={formatDate(session.created_at)} />
        <InfoRow label="Session ID" value={<CopyableText text={session.id} />} />
      </div>
    </div>
  );
};

export default SessionCard; 