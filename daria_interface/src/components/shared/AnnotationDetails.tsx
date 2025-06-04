import { useState } from 'react';
import Card from './Card';
import { Label } from './Label';
import { Textarea } from './TextArea';
import Button from './Button';
import Badge from './Badge';

interface AnnotationDetailsProps {
  message: {
    content: string;
    semantic?: {
      emotions?: string[];
      intent?: string;
      affinity_hint?: string;
      frustration_markers?: string[];
      pain_points?: Array<{
        quote: string;
        issue: string;
        severity_score: number;
        sentiment: string;
      }>;
      themes?: string[];
      ux_heuristic_violations?: string[];
      follow_up_questions?: string[];
      quotes?: Array<{
        text: string;
        theme?: string;
        emotion?: string;
        persona?: string;
      }>;
      interaction_modality?: string;
      task_success?: string;
      phase?: string;
      persona?: string;
      goal_satisfaction?: string;
    };
  };
  onSaveComment: (comment: string) => void;
}

export default function AnnotationDetails({ message, onSaveComment }: AnnotationDetailsProps) {
  const [comment, setComment] = useState('');
  const s = message?.semantic || {};

  return (
    <Card className="w-full p-4 space-y-4">
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Annotation Workspace</h2>

        {/* Semantic Fields Display */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {s.emotions && s.emotions.length > 0 && (
            <div>
              <Label>Emotions</Label>
              <div className="flex gap-2 flex-wrap">
                {s.emotions.map((e) => (
                  <Badge key={e} label={e} />
                ))}
              </div>
            </div>
          )}

          {s.themes && s.themes.length > 0 && (
            <div>
              <Label>Themes</Label>
              <div className="flex gap-2 flex-wrap">
                {s.themes.map((theme) => (
                  <Badge key={theme} label={theme} />
                ))}
              </div>
            </div>
          )}

          {s.intent && (
            <div>
              <Label>Intent</Label>
              <Badge label={s.intent} />
            </div>
          )}

          {s.affinity_hint && (
            <div>
              <Label>Affinity Hint</Label>
              <Badge label={s.affinity_hint} />
            </div>
          )}

          {s.interaction_modality && (
            <div>
              <Label>Interaction Modality</Label>
              <Badge label={s.interaction_modality} />
            </div>
          )}

          {s.task_success && (
            <div>
              <Label>Task Success</Label>
              <Badge label={s.task_success} />
            </div>
          )}

          {s.phase && (
            <div>
              <Label>Phase</Label>
              <Badge label={s.phase} />
            </div>
          )}

          {s.persona && (
            <div>
              <Label>Persona</Label>
              <Badge label={s.persona} />
            </div>
          )}

          {s.goal_satisfaction && (
            <div>
              <Label>Goal Satisfaction</Label>
              <Badge label={s.goal_satisfaction} />
            </div>
          )}
        </div>

        {s.frustration_markers && s.frustration_markers.length > 0 && (
          <div>
            <Label>Frustration Markers</Label>
            <ul className="list-disc ml-5 text-sm">
              {s.frustration_markers.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        )}

        {s.ux_heuristic_violations && s.ux_heuristic_violations.length > 0 && (
          <div>
            <Label>UX Heuristic Violations</Label>
            <ul className="list-disc ml-5 text-sm">
              {s.ux_heuristic_violations.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          </div>
        )}

        {s.pain_points && s.pain_points.length > 0 && (
          <div>
            <Label>Pain Points</Label>
            {s.pain_points.map((p, i) => (
              <div key={i} className="border p-2 rounded mt-2">
                <p className="text-sm italic">"{p.quote}"</p>
                <p className="text-sm">Issue: {p.issue}</p>
                <p className="text-sm">Severity: {p.severity_score} / Sentiment: {p.sentiment}</p>
              </div>
            ))}
          </div>
        )}

        {s.follow_up_questions && s.follow_up_questions.length > 0 && (
          <div>
            <Label>Follow-Up Questions</Label>
            <ul className="list-disc ml-5 text-sm">
              {s.follow_up_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </div>
        )}

        {s.quotes && s.quotes.length > 0 && (
          <div>
            <Label>Quotes</Label>
            <ul className="list-disc ml-5 text-sm">
              {s.quotes.map((q, i) => (
                <li key={i}>
                  <span className="italic">"{q.text}"</span>
                  {q.theme && <span className="ml-2 text-xs bg-gray-200 rounded px-2">{q.theme}</span>}
                  {q.emotion && <span className="ml-2 text-xs bg-blue-100 rounded px-2">{q.emotion}</span>}
                  {q.persona && <span className="ml-2 text-xs bg-green-100 rounded px-2">{q.persona}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Single Comment/Annotation Input */}
        <div className="space-y-2">
          <Label htmlFor="comment">Add Comment</Label>
          <Textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add your annotation/comment here..."
          />
          <Button
            disabled={!comment.trim()}
            onClick={() => {
              if (onSaveComment) onSaveComment(comment);
              setComment('');
            }}
          >
            Save Annotation
          </Button>
        </div>
      </div>
    </Card>
  );
}
