// AnnotationsTab.tsx
import React from 'react';
import type { Tag } from './shared/TagList';
import TagEditor from './shared/TagEditor';
import InsightAnnotation from './shared/InsightAnnotation';
import AnnotationDetails from './shared/AnnotationDetails';

interface Message {
  id: string;
  content: string;
  role: string;
  timestamp: string;
  tags?: string[]; // AI-assigned tags
  semantic?: {
    themes?: string[];
    emotions?: string[];
    intent?: string;
    task_success?: string;
    goal_satisfaction?: string;
    persona?: string;
    frustration_markers?: string[];
    ux_heuristic_violations?: string[];
    pain_points?: { issue: string; severity_score: number }[];
    quotes?: { text: string }[];
  };
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

// Tag component for colored badges
const Tag = ({ label, color }: { label: string, color: string }) => (
  <span style={{
    background: color,
    color: '#fff',
    borderRadius: '8px',
    padding: '2px 8px',
    marginRight: '4px',
    fontSize: '0.85em'
  }}>{label}</span>
);

const colorMap = {
  theme: '#a78bfa', // purple
  emotion: '#60a5fa', // blue
  intent: '#34d399', // green
  task_success: '#fbbf24', // yellow
  goal_satisfaction: '#f472b6', // pink
  persona: '#f87171', // red
  heuristic: '#f59e42', // orange
  pain: '#ef4444', // red
};

const Message = ({ msg }: { msg: any }) => {
  const s = msg.semantic || {};
  return (
    <div className="mb-4 p-3 bg-white rounded shadow">
      <div className="font-semibold">{msg.role}</div>
      <div>{msg.content}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {s.themes && s.themes.map((t: string) => <Tag key={t} label={t} color={colorMap.theme} />)}
        {s.emotions && s.emotions.map((e: string) => <Tag key={e} label={e} color={colorMap.emotion} />)}
        {s.intent && <Tag label={s.intent} color={colorMap.intent} />}
        {s.task_success && <Tag label={s.task_success} color={colorMap.task_success} />}
        {s.goal_satisfaction && <Tag label={s.goal_satisfaction} color={colorMap.goal_satisfaction} />}
        {s.persona && <Tag label={s.persona} color={colorMap.persona} />}
        {s.ux_heuristic_violations && s.ux_heuristic_violations.map((h: string) => <Tag key={h} label={h} color={colorMap.heuristic} />)}
        {s.frustration_markers && s.frustration_markers.map((f: string) => <Tag key={f} label={f} color={colorMap.pain} />)}
        {s.pain_points && s.pain_points.map((p: any, i: number) =>
          <Tag key={i} label={`${p.issue} (sev: ${p.severity_score})`} color={colorMap.pain} />
        )}
      </div>
      {/* Optionally, show quotes */}
      {s.quotes && s.quotes.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Quotes: {s.quotes.map((q: any, i: number) => <span key={i} style={{ background: '#e0e7ff', borderRadius: 4, padding: '2px 4px', marginRight: 4 }}>{q.text}</span>)}
        </div>
      )}
    </div>
  );
};

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
        const response = await fetch(`/api/analysis/session/${sessionId}/annotations/`, {
          method: 'GET',
          credentials: 'include',
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
      const response = await fetch(`/api/analysis/session/${sessionId}/annotations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId: activeMsgId, content: newComment }),
        credentials: 'include',
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

  // Patch activeMsg to ensure pain_points have all required fields and only pass if activeMsg is defined
  const patchedActiveMsg = activeMsg
    ? {
        content: activeMsg.content,
        semantic: {
          ...activeMsg.semantic,
          pain_points: activeMsg.semantic?.pain_points?.map((p: any) => ({
            quote: p.quote ?? activeMsg.content ?? '',
            issue: p.issue,
            severity_score: p.severity_score,
            sentiment: p.sentiment ?? '',
          })),
        },
      }
    : undefined;

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
        {patchedActiveMsg ? (
          <>
            <AnnotationDetails
              message={patchedActiveMsg}
              onSaveComment={handleAddAnnotation}
            />
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
