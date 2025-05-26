import React from 'react';
import Badge from './shared/Badge';
import InfoRow from './shared/InfoRow';
import CopyableText from './shared/CopyableText';

interface DiscussionGuideCardProps {
  guide: {
    id: string;
    title: string;
    project: string;
    interview_type: string;
    sessions: string[];
    created_at: string;
    updated_at: string;
    status: string;
    character_select?: string;
    interviewee?: {
      name: string;
      role: string;
      email: string;
    };
    options?: {
      record_transcript: boolean;
      analysis: boolean;
      use_tts: boolean;
    };
    expiration_date?: string;
  };
  onViewGuide?: (id: string) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

const DiscussionGuideCard: React.FC<DiscussionGuideCardProps> = ({
  guide,
  onViewGuide,
  onDelete,
  className = ''
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className={`p-4 border rounded-lg shadow-sm bg-white ${className}`}>
      <div className="flex justify-between items-start mb-3">
        <h2 className="text-xl font-semibold text-gray-900">{guide.title}</h2>
        <div className="flex gap-2">
          <Badge 
            label={guide.status} 
            color={guide.status.toLowerCase() === 'active' ? 'green' : 'gray'} 
          />
          <Badge 
            label={`${guide.sessions.length} Sessions`} 
            color="purple" 
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-6 mb-4">
        <div>
          <InfoRow label="Project" value={guide.project} />
          <InfoRow label="Created" value={formatDate(guide.created_at)} />
          <InfoRow label="Guide ID" value={<CopyableText text={guide.id} />} />
          {guide.interviewee && (
            <InfoRow 
              label="Interviewee" 
              value={`${guide.interviewee.name} (${guide.interviewee.role})`} 
            />
          )}
        </div>
        <div>
          <InfoRow label="Type" value={guide.interview_type} />
          <InfoRow label="Last Updated" value={formatDate(guide.updated_at)} />
          {guide.expiration_date && (
            <InfoRow 
              label="Expires" 
              value={formatDate(guide.expiration_date)} 
            />
          )}
        </div>
      </div>

      {guide.options && (
        <div className="mb-4 flex gap-2">
          {guide.options.record_transcript && (
            <Badge label="Record" color="blue" />
          )}
          {guide.options.analysis && (
            <Badge label="Analysis" color="purple" />
          )}
          {guide.options.use_tts && (
            <Badge label="TTS" color="green" />
          )}
        </div>
      )}

      <div className="mt-4 flex justify-between items-center">
        {guide.character_select && (
          <button className="bg-cyan-400 text-white rounded px-3 py-1 flex items-center gap-2 text-sm hover:bg-cyan-500 transition-colors">
            <span role="img" aria-label="character">👤</span>
            {guide.character_select}
          </button>
        )}
        <div className="flex gap-2 ml-auto">
          <button
            onClick={() => onViewGuide?.(guide.id)}
            className="bg-violet-600 text-white px-3 py-1 rounded text-sm hover:bg-violet-700 transition-colors"
          >
            View Guide
          </button>
          <button
            onClick={() => onDelete?.(guide.id)}
            className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600 transition-colors flex items-center gap-1"
          >
            <span role="img" aria-label="delete">🗑</span>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiscussionGuideCard; 