import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Card, Checkbox, Spin, Tag, Tooltip } from 'antd'; // Import necessary Ant Design components

// Define the interface for the data expected by the card
interface InterviewMetadata {
    participant?: { name?: string };
    interviewee?: { name?: string };
    [key: string]: any; // Allow other metadata fields
}

interface ChunkMetadata {
    themes?: string[];
    theme?: string[]; // Handle singular key
    insights?: string[];
    insightTag?: string[];
    insight_tags?: string[]; // Handle plural key
    emotion?: any; // Can be string or object
}

interface Chunk {
    metadata?: ChunkMetadata;
    [key: string]: any; // Allow other chunk fields
}

interface Interview {
  id: string;
  title?: string;
  date?: string; // Keep date handling flexible
  created_at?: string; // Add created_at as potential date source
  type?: string;
  preview?: string;
  transcript?: string;
  participant_name?: string;
  project_name?: string;
  status?: string;
  themes?: string[];
  insights?: string[];
  emotions?: { name: string; count: number; avg_intensity: number }[];
  metadata?: InterviewMetadata;
  chunks?: Chunk[];
  tags?: string[]; // Allow top-level tags too
}

interface InterviewCardProps {
  interviewSummary: Interview; // Expect summary data initially
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  // Add any other props needed, e.g., specific action handlers
}

// Reusable Interview Card Component
const InterviewCard: React.FC<InterviewCardProps> = ({ interviewSummary, isSelected, onToggleSelect }) => {
  const [fullInterview, setFullInterview] = useState<Interview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch full details when component mounts using the summary ID
  useEffect(() => {
    const fetchFullDetails = async () => {
      if (!interviewSummary.id) {
         // ... (error handling for missing ID)
         setError("Missing Interview ID");
         setLoading(false);
         setFullInterview(interviewSummary); 
         return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(`/interviews/raw/${interviewSummary.id}.json`);
        // <<< Log raw response >>>
        console.log(`[InterviewCard ID: ${interviewSummary.id}] Raw data fetched:`, response.data); 
        setFullInterview(response.data);
      } catch (err) {
        // ... (error handling) ...
        console.error(`[InterviewCard ID: ${interviewSummary.id}] Failed to fetch details:`, err);
        setError('Could not load details');
        setFullInterview(interviewSummary); 
      } finally {
        setLoading(false);
      }
    };
    fetchFullDetails();
  }, [interviewSummary.id]); 

  const displayData = fullInterview || interviewSummary;
  // <<< Log display data >>>
  console.log(`[InterviewCard ID: ${interviewSummary.id}] Data used for rendering:`, displayData);

  // --- Tag Calculation ---
  let allTags: string[] = [];
  if (fullInterview && !error) { // Calculate only if full data loaded successfully
      const themes = Array.isArray(fullInterview.themes) ? fullInterview.themes : [];
      const insights = Array.isArray(fullInterview.insights) ? fullInterview.insights : [];
      const topLevelTags = Array.isArray(fullInterview.tags) ? fullInterview.tags : []; // Check top-level tags
      // Extract themes/insights from chunks if they exist
      let chunkThemes = new Set<string>();
      let chunkInsights = new Set<string>();
      let chunkEmotions = new Set<string>();
      if (Array.isArray(fullInterview.chunks)) {
           for (const chunk of fullInterview.chunks) {
               const meta = chunk.metadata || {};
               if (Array.isArray(meta.themes)) meta.themes.forEach((theme: string) => chunkThemes.add(theme));
               if (Array.isArray(meta.theme)) meta.theme.forEach((theme: string) => chunkThemes.add(theme)); 
               if (Array.isArray(meta.insightTag)) meta.insightTag.forEach((insight: string) => chunkInsights.add(insight));
               if (Array.isArray(meta.insight_tags)) meta.insight_tags.forEach((insight: string) => chunkInsights.add(insight));
               // Extract primary emotion label if available
               if (typeof meta.emotion === 'object' && meta.emotion?.primary?.label) {
                   chunkEmotions.add(meta.emotion.primary.label);
               } else if (typeof meta.emotion === 'string') {
                   chunkEmotions.add(meta.emotion);
               }
           }
      }
      // Combine all sources, ensuring uniqueness
      allTags = Array.from(new Set([
        ...themes, 
        ...insights, 
        ...topLevelTags, // Add top-level tags
        ...Array.from(chunkThemes), 
        ...Array.from(chunkInsights),
        ...Array.from(chunkEmotions)
        ]));
  }

  // --- Date Formatting ---
  const formatDate = (dateStr: string | undefined) => {
     if (!dateStr) return 'No Date';
     try {
        return new Date(dateStr).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
     } catch (e) {
        return dateStr; 
     }
  };

  // --- Event Handlers ---
   const handleCardClick = () => {
     // Navigate to transcript view, or maybe just toggle selection?
     // For now, let's keep the toggle logic from PersonaGenerator
     onToggleSelect(displayData.id);
   };

   const handleCheckboxToggle = (e: React.MouseEvent) => {
     e.stopPropagation(); // Prevent card click when clicking checkbox
     onToggleSelect(displayData.id);
   };

   const handleCopyLink = (e: React.MouseEvent) => {
    e.stopPropagation(); 
    const url = `${window.location.origin}/transcript/${displayData.id}`;
    navigator.clipboard.writeText(url).then(() => alert('Link copied!')).catch(() => alert('Failed to copy link.'));
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    alert('Delete action triggered (implementation needed)'); 
    // Add actual delete logic here or pass handler via props
  };

  // --- Card Rendering ---
  return (
    <Card
      key={displayData.id}
      className={`transition-all flex flex-col justify-between items-start ${isSelected ? 'border-blue-500 shadow-md' : 'border-transparent'}`}
      style={{ cursor: 'pointer', width: '100%', minHeight: 260, margin: '0 auto' }} // Adjusted style
      onClick={handleCardClick}
      bodyStyle={{ padding: '16px', flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }} // Ensure body fills card
    >
      {loading ? (
        <div className="flex justify-center items-center h-full w-full">
          <Spin tip="Loading..."/>
        </div>
      ) : (
        <>
          {/* Top section with checkbox, title, date, participant */}
          <div>
            <div className="flex items-start justify-between w-full mb-2">
              <Checkbox 
                checked={isSelected} 
                onChange={() => {}} // Let card click handle toggle
                onClick={handleCheckboxToggle}
                className="pt-1" // Align checkbox slightly lower
              />
              <div className="flex-1 ml-2 overflow-hidden">
                <div 
                    className="font-semibold text-sm sm:text-base truncate" 
                    title={displayData.title || 'Untitled Interview'}
                >
                    {displayData.title || 'Untitled Interview'}
                </div>
                 <div 
                    className="text-xs text-gray-700 font-medium truncate" 
                    title={displayData.participant_name || 'Anonymous'}
                 >
                    {displayData.participant_name || 'Anonymous'}
                 </div>
                <div className="text-xs text-gray-400 truncate">{formatDate(displayData.created_at || displayData.date)}</div>
              </div>
            </div>
            
            {/* Transcript Preview */}
             <div 
                className="text-xs text-gray-600 italic line-clamp-3 my-2" 
                title={displayData.transcript || displayData.preview || 'No transcript available'}
             >
               {displayData.transcript ? 
                 (displayData.transcript.length > 120 ? displayData.transcript.slice(0, 120) + '...' : displayData.transcript) :
                 (displayData.preview || 'No transcript available')
               }
            </div>
            
            {/* Tags */}
            {!error && allTags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                {allTags.slice(0, 4).map((tag, index) => ( // Show fewer tags to save space
                    <Tag key={`${tag}-${index}`} color="blue" style={{fontSize: '10px', padding: '1px 4px', margin: '1px'}}>{tag}</Tag>
                ))}
                {allTags.length > 4 && <Tag style={{fontSize: '10px', padding: '1px 4px', margin: '1px'}}>...</Tag>}
                </div>
            )}
             {error && <div className="text-xs text-red-500 mb-2">{error}</div>}
          </div>
          
          {/* Bottom Actions */}
           <div className="flex items-center gap-x-3 mt-auto border-t pt-2 text-gray-400 text-base justify-end w-full">
               <Tooltip title="View Transcript">
                   <Link to={`/transcript/${displayData.id}`} className="hover:text-indigo-600" onClick={handleCopyLink}>T</Link>
               </Tooltip>
               <Tooltip title="View Analysis">
                   <Link to={`/analysis/${displayData.id}`} className="hover:text-indigo-600" onClick={handleDelete}>A</Link>
               </Tooltip>
               <Tooltip title="View Metadata">
                   <Link to={`/metadata/${displayData.id}`} className="hover:text-indigo-600">M</Link>
               </Tooltip>
           </div>
        </>
      )}
    </Card>
  );
};

export default InterviewCard; 