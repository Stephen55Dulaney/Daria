import React, { useEffect, useState } from 'react';
import axios from 'axios';
import SessionCard from '../../components/shared/SessionCard';

// Types
interface Guide {
  id: string;
  title: string;
  sessions: string[];
  analysis_prompt?: string;
}

interface Session {
  id: string;
  title: string;
  project: string;
  created_at: string;
  status: string;
  [key: string]: any;
}

interface Character {
  name: string;
  description?: string;
  analysis_prompt?: string;
}

// GuideSelector
const GuideSelector: React.FC<{
  guides: Guide[];
  selectedGuideId: string | null;
  onSelect: (id: string) => void;
}> = ({ guides, selectedGuideId, onSelect }) => (
  <div className="mb-4">
    <label className="block mb-1 font-semibold">Select Discussion Guide</label>
    <select
      className="border rounded px-3 py-2 w-full max-w-md"
      value={selectedGuideId || ''}
      onChange={e => onSelect(e.target.value)}
    >
      <option value="">-- Select a Guide --</option>
      {guides.map(guide => (
        <option key={guide.id} value={guide.id}>{guide.title}</option>
      ))}
    </select>
  </div>
);

// SessionCardList
const SessionCardList: React.FC<{
  sessions: Session[];
  selectedSessionIds: string[];
  onSelect: (id: string) => void;
}> = ({ sessions, selectedSessionIds, onSelect }) => (
  <div>
    <h2 className="text-xl font-semibold mb-2">Select Research Sessions</h2>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sessions.map(session => (
        <div key={session.id} className="relative">
          <SessionCard
            session={session}
            className={selectedSessionIds.includes(session.id) ? 'ring-2 ring-violet-500 bg-violet-50' : ''}
          />
          <input
            type="checkbox"
            checked={selectedSessionIds.includes(session.id)}
            onChange={() => onSelect(session.id)}
            className="absolute top-4 right-4 w-5 h-5 z-10"
            onClick={e => e.stopPropagation()}
          />
        </div>
      ))}
      {sessions.length === 0 && <div className="text-gray-500">No sessions found for this guide.</div>}
    </div>
  </div>
);

// CharacterSelector
const CharacterSelector: React.FC<{
  characters: Character[];
  selectedCharacter: string | null;
  onSelect: (name: string) => void;
}> = ({ characters, selectedCharacter, onSelect }) => (
  <div className="mb-4">
    <label className="block mb-1 font-semibold">Select Research Assistant</label>
    <select
      className="border rounded px-3 py-2 w-full max-w-md"
      value={selectedCharacter || ''}
      onChange={e => onSelect(e.target.value)}
    >
      <option value="">-- Select a Character --</option>
      {characters.map(char => (
        <option key={char.name} value={char.name}>{char.name.charAt(0).toUpperCase() + char.name.slice(1)}</option>
      ))}
    </select>
  </div>
);

// AnalysisPromptDisplay
const AnalysisPromptDisplay: React.FC<{
  prompt: string | undefined;
}> = ({ prompt }) => (
  <div className="mb-4">
    <label className="block mb-1 font-semibold">Analysis Prompt</label>
    <textarea
      className="border rounded px-3 py-2 w-full max-w-xl bg-gray-100 text-gray-700"
      value={prompt || 'No analysis prompt available.'}
      readOnly
      rows={8}
    />
  </div>
);

// GenerateReportButton
const GenerateReportButton: React.FC<{
  disabled: boolean;
  onClick: () => void;
}> = ({ disabled, onClick }) => (
  <button
    className="bg-violet-600 text-white px-6 py-2 rounded text-lg font-semibold disabled:opacity-50"
    disabled={disabled}
    onClick={onClick}
  >
    Generate Report
  </button>
);

// GeneratedReportDisplay
const GeneratedReportDisplay: React.FC<{
  report: string | null;
}> = ({ report }) => (
  report ? (
    <div className="mt-8 p-6 bg-gray-50 border rounded">
      <h2 className="text-xl font-bold mb-2">Generated Report</h2>
      <pre className="whitespace-pre-wrap text-gray-800">{report}</pre>
    </div>
  ) : null
);

// Main Page
const GenerateAnalysisPage: React.FC = () => {
  const [guides, setGuides] = useState<Guide[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedGuideId, setSelectedGuideId] = useState<string | null>(null);
  const [selectedSessionIds, setSelectedSessionIds] = useState<string[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [characterPrompt, setCharacterPrompt] = useState<string>('');
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch guides, characters on mount
  useEffect(() => {
    const fetchGuides = async () => {
      try {
        const res = await axios.get('/api/discussion_guides');
        const guides = res.data.guides || [];
        const updatedGuides = guides.map((guide: Guide) => ({
          ...guide,
          title: guide.title || 'Untitled Guide'
        }));
        setGuides(updatedGuides);
      } catch {
        setGuides([]);
      }
    };
    const fetchCharacters = async () => {
      try {
        const res = await axios.get('/api/health');
        setCharacters((res.data.available_prompts || []).map((name: string) => ({ name })));
      } catch {
        setCharacters([]);
      }
    };
    fetchGuides();
    fetchCharacters();
    setLoading(false);
  }, []);

  // Fetch sessions for selected guide
  useEffect(() => {
    if (!selectedGuideId) {
      setSessions([]);
      setSelectedSessionIds([]);
      return;
    }
    const guide = guides.find(g => g.id === selectedGuideId);
    if (!guide) return;
    // Fetch session details for each session ID
    Promise.all(
      (guide.sessions || []).map(async (sessionId: string) => {
        try {
          const res = await axios.get(`/api/research_session/${sessionId}`);
          return res.data.session;
        } catch {
          return null;
        }
      })
    ).then(results => {
      setSessions(results.filter(Boolean));
      setSelectedSessionIds([]);
    });
  }, [selectedGuideId, guides]);

  // Fetch character analysis prompt when character changes
  useEffect(() => {
    if (!selectedCharacter) {
      setCharacterPrompt('');
      return;
    }
    axios.get(`/api/character/${selectedCharacter}`)
      .then(res => setCharacterPrompt(res.data.analysis_prompt || 'No analysis prompt available.'))
      .catch(() => setCharacterPrompt('No analysis prompt available.'));
  }, [selectedCharacter]);

  const handleSelectSession = (id: string) => {
    setSelectedSessionIds(prev => prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]);
  };

  const handleGenerateReport = async () => {
    // Stub: Replace with actual API call
    setReport(`Report for sessions: ${selectedSessionIds.join(', ')} with character: ${selectedCharacter}\nPrompt: ${characterPrompt}`);
  };

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Generate Research Analysis</h1>
      <GuideSelector guides={guides} selectedGuideId={selectedGuideId} onSelect={setSelectedGuideId} />
      {selectedGuideId && (
        <SessionCardList sessions={sessions} selectedSessionIds={selectedSessionIds} onSelect={handleSelectSession} />
      )}
      <CharacterSelector characters={characters} selectedCharacter={selectedCharacter} onSelect={setSelectedCharacter} />
      <AnalysisPromptDisplay prompt={characterPrompt} />
      <div className="mt-8">
        <GenerateReportButton
          disabled={selectedSessionIds.length === 0 || !selectedCharacter}
          onClick={handleGenerateReport}
        />
      </div>
      <GeneratedReportDisplay report={report} />
    </div>
  );
};

export default GenerateAnalysisPage; 