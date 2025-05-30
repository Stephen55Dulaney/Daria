// AnnotationsTab.tsx
import React from 'react';
import type { Tag } from './shared/TagList';
import TagEditor from './shared/TagEditor';
import InsightAnnotation from './shared/InsightAnnotation';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
  tags?: string[]; // AI-assigned tags
}

interface AnnotationsTabProps {
  messages: Message[];
  sessionId: string;
}

interface Annotation {
  id: string;
  messageId: string;
  content: string;
  user: {
    name: string;
  };
  timestamp: string;
}

const AnnotationsTab: React.FC<AnnotationsTabProps> = ({ messages, sessionId }) => {
  const [activeMsgId, setActiveMsgId] = React.useState<string | null>(null);
  const [annotations, setAnnotations] = React.useState<{ [msgId: string]: Annotation[] }>({});
  const [newComment, setNewComment] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Load all annotations for this session
  React.useEffect(() => {
    const loadAnnotations = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/session/${sessionId}/annotations/`, {
          method: 'GET',
        });
        const data = await response.json();
        if (data.annotations) {
          // Group by messageId
          const grouped: { [msgId: string]: Annotation[] } = {};
          for (const ann of data.annotations) {
            if (!grouped[ann.messageId]) grouped[ann.messageId] = [];
            grouped[ann.messageId].push(ann);
          }
          setAnnotations(grouped);
        } else {
          setAnnotations({});
        }
      } catch (e: any) {
        setError('Failed to load annotations');
      } finally {
        setIsLoading(false);
      }
    };
    loadAnnotations();
  }, [sessionId]);

  // Only participant messages are annotatable
  const isParticipant = (msg: Message) => msg.role === 'participant' || msg.role === 'user';

  const handleAddAnnotation = async () => {
    if (!activeMsgId || !newComment.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/session/${sessionId}/annotations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId: activeMsgId, content: newComment })
      });
      const data = await response.json();
      if (data.success && data.annotation) {
        setAnnotations(prev => ({
          ...prev,
          [activeMsgId]: [...(prev[activeMsgId] || []), data.annotation]
        }));
        setNewComment('');
      } else {
        setError(data.error || 'Failed to add annotation');
      }
    } catch (e: any) {
      setError('Failed to add annotation');
    } finally {
      setIsLoading(false);
    }
  };

  // Find the currently active participant message
  const activeMsg = messages.find(m => m.id === activeMsgId && isParticipant(m));

  return (
    <div className="flex gap-6 h-[80vh]">
      {/* Left column: Transcript */}
      <div className="w-3/4 overflow-y-auto pr-4 border-r">
        <h2 className="text-xl font-semibold mb-4">Transcript</h2>
        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`p-4 rounded-lg transition-colors group ${
                isParticipant(msg)
                  ? activeMsgId === msg.id
                    ? 'border-2 border-purple-500 bg-purple-50 cursor-pointer'
                    : 'hover:border-gray-300 border cursor-pointer'
                  : 'bg-gray-50 border cursor-default'
              }`}
              onClick={() => isParticipant(msg) && setActiveMsgId(msg.id)}
              style={{ opacity: isParticipant(msg) ? 1 : 0.7 }}
            >
              <div className="flex items-center mb-1">
                <span className={`font-semibold ${msg.role === 'assistant' || msg.role === 'moderator' ? 'text-gray-500 text-sm' : ''}`}>
                  {msg.role === 'assistant' || msg.role === 'moderator' ? 'Moderator' : 'Participant'}
                </span>
                <span className="ml-2 text-xs text-gray-400">
                  {new Date(msg.timestamp).toLocaleString()}
                </span>
              </div>
              <div className={`text-gray-900 ${msg.role === 'assistant' || msg.role === 'moderator' ? 'text-sm' : ''}`}>{msg.content}</div>
              {/* Show tags for participant messages */}
              {isParticipant(msg) && msg.tags && msg.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {msg.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right column: Annotation workspace */}
      <div className="w-1/4 pl-4 flex flex-col">
        <h2 className="text-lg font-semibold mb-4">Annotation Workspace</h2>
        {activeMsg ? (
          <>
            <div className="mb-4">
              <div className="text-sm text-gray-500 mb-1">Participant Message:</div>
              <div className="p-2 bg-gray-50 rounded border mb-2 text-gray-900">{activeMsg.content}</div>
              {/* Show tags here as well for quick reference */}
              {activeMsg.tags && activeMsg.tags.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {activeMsg.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="mb-6">
              <h3 className="font-medium mb-2">Add Comment</h3>
              <textarea
                className="w-full border rounded p-2 mb-2"
                rows={3}
                value={newComment}
                onChange={e => setNewComment(e.target.value)}
                placeholder="Add your annotation/comment here..."
                disabled={isLoading}
              />
              <button
                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                onClick={handleAddAnnotation}
                disabled={isLoading || !newComment.trim()}
              >
                Save Annotation
              </button>
              {error && <div className="text-red-600 mt-2">{error}</div>}
            </div>
            <div>
              <h3 className="font-medium mb-2">Comments</h3>
              {activeMsgId && annotations[activeMsgId]?.length > 0 ? (
                <div className="space-y-4">
                  {annotations[activeMsgId].map((annotation: Annotation) => (
                    <div key={annotation.id} className="p-3 border rounded-lg bg-white">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium">{annotation.user.name}</span>
                        <span className="text-sm text-gray-500">
                          {new Date(annotation.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-gray-700">{annotation.content}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500">No annotations for this message yet.</div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center text-gray-500 py-8">
            Select a participant response to view/add tags and annotations
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnotationsTab;