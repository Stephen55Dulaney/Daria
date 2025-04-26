import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

interface Interview {
  id: string;
  title: string;
  project_name: string;
  interview_type: string;
  date: string;
  transcript: string;
  interviewee?: string;
  metadata: any;
  preview: string;
}

const parseTranscript = (transcript: string) => {
  // Split transcript into blocks by double newlines
  const blocks = transcript.split(/\n\n+/);
  return blocks.map((block, idx) => {
    // Try to extract [Speaker] timestamp\nText
    const match = block.match(/^\[(.*?)\] (\d{2}:\d{2}:\d{2})\n([\s\S]*)$/);
    if (match) {
      return {
        speaker: match[1],
        timestamp: match[2],
        text: match[3],
        key: idx,
      };
    } else {
      // Fallback: just text
      return {
        speaker: null,
        timestamp: null,
        text: block,
        key: idx,
      };
    }
  });
};

const InterviewCard = ({ interview }: { interview: Interview }) => (
  <div className="bg-white rounded-lg shadow p-6 mb-6">
    <div className="flex justify-between items-start mb-4">
      <div>
        <h3 className="text-xl font-semibold">{interview.title}</h3>
        <p className="text-gray-600">{interview.project_name}</p>
      </div>
      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
        {interview.interview_type}
      </span>
    </div>
    <div className="mb-4">
      <p className="text-gray-500 text-sm mb-2">{interview.date}</p>
      {interview.interviewee && (
        <p className="text-gray-700">Interviewee: {interview.interviewee}</p>
      )}
    </div>
    <div className="mb-4">
      <p className="text-gray-700 line-clamp-3">{interview.preview}</p>
    </div>
    <div className="flex justify-end">
      <Link
        to={`/transcript/${interview.id}`}
        className="text-blue-600 hover:text-blue-800"
      >
        View Full Transcript →
      </Link>
    </div>
  </div>
);

const FullTranscript = () => {
  const { id } = useParams();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    if (id) {
      // If we have an ID, fetch a single interview
      fetch(`/interviews/raw/${id}.json`)
        .then((res) => {
          if (!res.ok) throw new Error("Interview not found");
          return res.json();
        })
        .then((json) => {
          setInterviews([json]);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    } else {
      // Otherwise, fetch all interviews
      fetch('/api/interviews/raw')
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load interviews");
          return res.json();
        })
        .then((json) => {
          setInterviews(json);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [id]);

  if (loading) return <div className="p-8 text-center">Loading...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!interviews.length) return <div className="p-8 text-center">No interviews found.</div>;

  // If we're viewing a single interview, show the full transcript view
  if (id) {
    const interview = interviews[0];
    const transcriptBlocks = parseTranscript(interview.transcript);

    return (
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8 mt-8">
        <Link to="/" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Archive</Link>
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-2">Project Information</h2>
          <div className="mb-1"><span className="font-bold">Project Name:</span> {interview.project_name}</div>
          <div className="mb-1"><span className="font-bold">Interview Type:</span> {interview.interview_type}</div>
          <div className="mb-1"><span className="font-bold">Date:</span> {interview.date}</div>
          {interview.interviewee && (
            <div className="mb-1"><span className="font-bold">Interviewee:</span> {interview.interviewee}</div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Interview Transcript</h2>
          <div className="space-y-4">
            {transcriptBlocks.map((block) => (
              <div key={block.key} className="bg-gray-50 rounded p-3">
                {block.speaker && (
                  <div className="text-gray-600 text-sm mb-1">
                    <span className="font-mono">[{block.speaker}]</span>
                    {block.timestamp && <span className="ml-2 font-mono">{block.timestamp}</span>}
                  </div>
                )}
                <div className="whitespace-pre-line text-gray-900">{block.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Otherwise, show the interview cards
  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Interview Archive</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {interviews.map((interview) => (
          <InterviewCard key={interview.id} interview={interview} />
        ))}
      </div>
    </div>
  );
};

export default FullTranscript; 