import React from 'react';
import { StageItem } from './StageItem';

interface Stage {
  title: string;
  description?: string;
  activities?: string[];
  [key: string]: any;
}

interface StageListProps {
  stages: Stage[];
}

export const StageList: React.FC<StageListProps> = ({ stages }) => {
  if (!stages || stages.length === 0) return null;

  return (
    <div className="bg-indigo-50 p-6 rounded-lg shadow-md border border-indigo-100 mb-8">
      <h2 className="text-xl font-bold text-indigo-800 mb-4">Journey Stages</h2>
      
      <div className="relative">
        {/* Horizontal connecting line */}
        <div className="absolute top-1/2 left-0 w-full h-1 bg-indigo-200 -z-10"></div>
        
        <div className="flex flex-wrap md:flex-nowrap gap-4 justify-around">
          {stages.map((stage, index) => (
            <StageItem 
              key={index} 
              stage={stage} 
              index={index} 
              totalStages={stages.length} 
            />
          ))}
        </div>
      </div>
    </div>
  );
}; 