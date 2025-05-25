import React, { useState } from 'react';
import { Button, Tooltip, message } from 'antd';
import { SaveOutlined, DownloadOutlined, ShareAltOutlined } from '@ant-design/icons';
import SaveModal from './SaveModal';
import { downloadJson, shareContent } from '../../utils/export';

interface ActionButtonsProps {
  type: 'persona' | 'journey-map';
  data: any;
  onSave: (name: string, description: string) => Promise<void>;
  exportToFigma: () => void;
  shareUrl?: string;
  disabled?: boolean;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({
  type,
  data,
  onSave,
  exportToFigma,
  shareUrl,
  disabled = false
}) => {
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const handleSave = async (name: string, description: string) => {
    setSaving(true);
    try {
      await onSave(name, description);
      message.success(`${type === 'persona' ? 'Persona' : 'Journey map'} saved successfully!`);
      setSaveModalOpen(false);
    } catch (error) {
      console.error('Error saving:', error);
      message.error(`Failed to save ${type}. Please try again.`);
    } finally {
      setSaving(false);
    }
  };
  
  const handleDownload = () => {
    const filename = type === 'persona'
      ? `${data.name?.replace(/\s+/g, '_') || 'persona'}.json`
      : `${data.journeyTitle?.replace(/\s+/g, '_') || 'journey_map'}.json`;
      
    downloadJson(data, filename);
    message.success(`${type === 'persona' ? 'Persona' : 'Journey map'} downloaded successfully!`);
  };
  
  const handleShare = async () => {
    if (!shareUrl) {
      message.warning('Save the item first to get a shareable link.');
      return;
    }
    
    const title = type === 'persona' 
      ? `${data.name || 'Persona'}`
      : `${data.journeyTitle || 'Journey Map'}`;
      
    const text = type === 'persona'
      ? `Check out this persona: ${data.name}`
      : `Check out this journey map: ${data.journeyTitle || 'Journey Map'}`;
    
    const success = await shareContent(title, text, shareUrl);
    
    if (success) {
      message.success(typeof navigator.share === 'function'
        ? 'Shared successfully!' 
        : 'Link copied to clipboard!');
    } else {
      message.error('Failed to share. Please try again.');
    }
  };
  
  return (
    <>
      <div className="flex gap-2">
        <Tooltip title="Save">
          <Button 
            icon={<SaveOutlined />} 
            onClick={() => setSaveModalOpen(true)}
            disabled={disabled}
          />
        </Tooltip>
        
        <Tooltip title="Download JSON">
          <Button 
            icon={<DownloadOutlined />} 
            onClick={handleDownload}
            disabled={disabled}
          />
        </Tooltip>
        
        <Tooltip title={shareUrl ? "Share" : "Save first to share"}>
          <Button 
            icon={<ShareAltOutlined />} 
            onClick={handleShare}
            disabled={disabled || !shareUrl}
          />
        </Tooltip>
        
        <Tooltip title="Export to Figma">
          <Button 
            onClick={exportToFigma}
            disabled={disabled}
          >
            Figma
          </Button>
        </Tooltip>
      </div>
      
      <SaveModal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSave={handleSave}
        title={`Save ${type === 'persona' ? 'Persona' : 'Journey Map'}`}
        type={type}
        loading={saving}
      />
    </>
  );
};

export default ActionButtons; 