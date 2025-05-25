import React from 'react';

interface BadgeProps {
  label: string;
  color?: 'green' | 'purple' | 'blue' | 'red' | 'gray';
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({ label, color = 'gray', className = '' }) => {
  const colorMap = {
    green: 'bg-green-500 text-white',
    purple: 'bg-violet-600 text-white',
    blue: 'bg-blue-500 text-white',
    red: 'bg-red-500 text-white',
    gray: 'bg-gray-300 text-black',
  };

  return (
    <span 
      className={`text-sm px-2 py-1 rounded-full inline-flex items-center ${colorMap[color]} ${className}`}
    >
      {label}
    </span>
  );
};

export default Badge; 