import React from 'react';
import Badge from './Badge';
import InfoRow from './InfoRow';
import CopyableText from './CopyableText';

interface SessionCardProps {
  session: {
    id: string;
    title: string;
    project?: string;
    interview_type?: string;
    character?: string;
    created_at: string;
    status: string;
    participant_name?: string;
  };
  onClick?: (session: SessionCardProps['session']) => void;
  className?: string;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onClick, className = '' }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div 
      className={`p-4 border rounded-lg shadow-sm bg-white hover:shadow-md transition-shadow ${className}`}
      onClick={() => onClick?.(session)}
    >
      <div className="flex justify-between items-start mb-3">
        <h2 className="text-xl font-semibold text-gray-900">{session.title}</h2>
        <Badge 
          label={session.status} 
          color={session.status.toLowerCase() === 'active' ? 'green' : 'gray'} 
        />
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