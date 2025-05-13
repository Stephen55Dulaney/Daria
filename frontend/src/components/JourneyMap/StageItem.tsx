import React from 'react';

interface StageItemProps {
  stage: {
    title: string;
    description?: string;
    activities?: string[];
    [key: string]: any;
  };
  index: number;
  totalStages: number;
}

export const StageItem: React.FC<StageItemProps> = ({ stage, index, totalStages }) => {
  return (
    <div className="flex-1 flex flex-col items-center max-w-xs">
      {/* Stage number bubble */}
      <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center text-white font-semibold mb-3 z-10">
        {index + 1}
      </div>
      
      {/* Stage content */}
      <div className="bg-white p-4 rounded-lg shadow-sm w-full">
        <h3 className="font-semibold text-indigo-700 text-center mb-2">{stage.title}</h3>
        
        {stage.description && (
          <p className="text-gray-600 text-sm mb-2">{stage.description}</p>
        )}
        
        {stage.activities && stage.activities.length > 0 && (
          <div className="mt-2">
            <p className="text-sm font-medium text-indigo-600 mb-1">Activities:</p>
            <ul className="list-disc pl-5 text-gray-500 text-xs">
              {stage.activities.map((activity, i) => (
                <li key={i} className="mb-1">{activity}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}; 