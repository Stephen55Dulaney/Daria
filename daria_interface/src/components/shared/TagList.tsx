import React from 'react';

export interface Tag {
  id: string;
  label: string;
  color?: string;
  user?: { name: string; avatarUrl?: string };
  createdAt?: string;
}

interface TagListProps {
  tags: Tag[];
  onTagClick?: (tag: Tag) => void;
  showAvatars?: boolean;
}

const TagList: React.FC<TagListProps> = ({ tags, onTagClick, showAvatars }) => (
  <div className="flex flex-wrap gap-2 mt-1">
    {tags.map(tag => (
      <span
        key={tag.id}
        className={`px-2 py-1 rounded text-xs cursor-pointer`}
        style={{ background: tag.color || '#e0e7ff', color: '#3730a3' }}
        onClick={() => onTagClick?.(tag)}
        title={tag.user ? `Tagged by ${tag.user.name}` : undefined}
      >
        {showAvatars && tag.user?.avatarUrl && (
          <img src={tag.user.avatarUrl} alt={tag.user.name} className="inline w-4 h-4 rounded-full mr-1" />
        )}
        {tag.label}
      </span>
    ))}
  </div>
);

export default TagList;
