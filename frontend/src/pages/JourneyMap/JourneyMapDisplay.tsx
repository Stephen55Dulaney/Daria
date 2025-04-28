import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

interface JourneyMapData {
  html: string;
}

interface JourneyMapDisplayProps {
  journeyMap: JourneyMapData;
}

const JourneyMapDisplay: React.FC<JourneyMapDisplayProps> = ({ journeyMap }) => {
  if (!journeyMap || !journeyMap.html) {
    return <div className="text-center text-red-500">Invalid journey map data</div>;
  }

  return (
    <div className="journey-map-display">
      <Card className="mb-8">
        <div dangerouslySetInnerHTML={{ __html: journeyMap.html }} />
      </Card>
    </div>
  );
};

export default JourneyMapDisplay; 