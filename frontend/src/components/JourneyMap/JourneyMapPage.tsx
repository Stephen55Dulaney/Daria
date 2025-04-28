import React from 'react';
import { JourneyMapHeader } from './JourneyMapHeader';
import { StageList } from './StageList';
import { TouchpointList } from './TouchpointList';
import { EmotionList } from './EmotionList';
import { PainPointList } from './PainPointList';
import { OpportunityList } from './OpportunityList';

interface JourneyMapPageProps {
  journeyMap: any; // Contains the journey map data
}

export const JourneyMapPage: React.FC<JourneyMapPageProps> = ({ journeyMap }) => {
  if (!journeyMap) return <div className="text-center text-red-500 py-12">No journey map data available</div>;

  // Extract journey map data, handling both legacy HTML format and new structured JSON
  const data = journeyMap.journey_map_data || journeyMap;
  
  // Legacy support for HTML-only journey maps
  if (data.html && !data.stages) {
    return (
      <div className="max-w-6xl mx-auto">
        <JourneyMapHeader 
          title={data.title || 'Journey Map'} 
          description={data.description || ''} 
        />
        <div 
          className="journey-map-legacy bg-white rounded-lg shadow-md p-6 mt-6"
          dangerouslySetInnerHTML={{ __html: data.html }} 
        />
      </div>
    );
  }

  // New structured journey map format
  return (
    <div className="max-w-6xl mx-auto">
      <JourneyMapHeader 
        title={data.title || 'Journey Map'} 
        description={data.description || ''} 
      />

      <StageList stages={data.stages || []} />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
        <TouchpointList touchpoints={data.touchpoints || []} />
        <EmotionList emotions={data.emotions || []} />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
        <PainPointList painPoints={data.pain_points || []} />
        <OpportunityList opportunities={data.opportunities || []} />
      </div>
    </div>
  );
}; 