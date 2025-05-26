import React from 'react';
import Card from './Card';
import Button from './Button';

interface GalleryItem {
  id: string;
  title: string;
  description?: string;
  imageUrl?: string;
  createdAt: string;
  type: 'character' | 'analysis';
}

interface GalleryProps {
  items: GalleryItem[];
  onItemClick?: (item: GalleryItem) => void;
  onSaveToGallery?: (item: GalleryItem) => void;
  className?: string;
}

const Gallery: React.FC<GalleryProps> = ({
  items,
  onItemClick,
  onSaveToGallery,
  className = '',
}) => {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}>
      {items.map((item) => (
        <Card
          key={item.id}
          variant="elevated"
          padding="md"
          onClick={() => onItemClick?.(item)}
          className="flex flex-col"
        >
          {item.imageUrl && (
            <div className="w-full h-48 mb-4 rounded-md overflow-hidden">
              <img
                src={item.imageUrl}
                alt={item.title}
                className="w-full h-full object-cover"
              />
            </div>
          )}
          
          <div className="flex-grow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{item.title}</h3>
            {item.description && (
              <p className="text-sm text-gray-600 mb-4">{item.description}</p>
            )}
            <p className="text-xs text-gray-500">
              {new Date(item.createdAt).toLocaleDateString()}
            </p>
          </div>

          {onSaveToGallery && (
            <div className="mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onSaveToGallery(item);
                }}
              >
                Save to Gallery
              </Button>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
};

export default Gallery; 