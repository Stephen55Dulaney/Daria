import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Card, Select, Button, Spin, message } from 'antd';
import JourneyMapDisplay from './JourneyMapDisplay';
import InterviewSearchSelect from '../../components/InterviewSearchSelect/index';
import ActionButtons from '../../components/common/ActionButtons';
import { exportToFigma } from '../../utils/export';
import { JourneyMapPage } from '../../components/JourneyMap/JourneyMapPage';

const JourneyMap: React.FC = () => {
  const [selectedInterviews, setSelectedInterviews] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4');
  const [generatingJourneyMap, setGeneratingJourneyMap] = useState<boolean>(false);
  const [generatedJourneyMap, setGeneratedJourneyMap] = useState<any>(null);
  const [savedJourneyMapId, setSavedJourneyMapId] = useState<string | null>(null);

  const handleInterviewSelectionChange = (selectedIds: string[]) => {
    setSelectedInterviews(selectedIds);
  };

  const handleGenerateJourneyMap = async () => {
    if (selectedInterviews.length === 0) {
      message.warning('Please select at least one interview.');
      return;
    }
    setGeneratingJourneyMap(true);
    setGeneratedJourneyMap(null);
    setSavedJourneyMapId(null);
    
    try {
      // Updated API call to specify we want structured JSON data
      const response = await axios.post('/api/journey-map', {
        interview_ids: selectedInterviews,
        model: selectedModel,
        format: 'structured_json'
      });
      console.log('Received data from /api/journey-map:', response.data);
      setGeneratedJourneyMap(response.data);
    } catch (error: any) {
      console.error('Error generating journey map:', error);
      message.error(`Error generating journey map: ${error.response?.data?.error || error.message}`);
      setGeneratedJourneyMap(null);
    } finally {
      setGeneratingJourneyMap(false);
    }
  };
  
  const handleSaveJourneyMap = async (name: string, description: string) => {
    try {
      // Make sure we have a properly structured journey map data
      const journeyMapData = {
        title: name,
        description,
        // Include original HTML for backward compatibility
        html: generatedJourneyMap.html,
        // Include structured data
        stages: generatedJourneyMap.stages || [],
        touchpoints: generatedJourneyMap.touchpoints || [],
        emotions: generatedJourneyMap.emotions || [],
        pain_points: generatedJourneyMap.pain_points || [],
        opportunities: generatedJourneyMap.opportunities || []
      };
      
      const response = await axios.post('/api/save-journey-map', {
        project_name: name,
        journey_map_data: journeyMapData
      });
      
      console.log('Save journey map response:', response.data);
      
      // The backend returns id in the response
      if (response.data.id) {
        setSavedJourneyMapId(response.data.id);
      } else {
        // Check the console for the actual response structure
        message.warning('Journey map saved, but sharing might not work. Check console for details.');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error saving journey map:', error);
      throw error;
    }
  };
  
  const handleExportToFigma = () => {
    if (generatedJourneyMap) {
      // Extract structured data for Figma export
      const journeyMapData = {
        journeyTitle: generatedJourneyMap.title || "User Journey",
        stages: generatedJourneyMap.stages || [],
        // Add other sections as needed for Figma export
      };
      
      exportToFigma(journeyMapData, 'journey-map');
    }
  };

  const renderJourneyMapTemplate = () => {
    if (generatingJourneyMap) {
      return (
        <div className="mt-8 text-center">
          <div className="bg-white p-8 rounded-lg shadow-sm">
            <Spin size="large">
              <div className="h-8" />
              <div className="text-gray-600 mt-3">Generating Journey Map...</div>
            </Spin>
          </div>
        </div>
      );
    }
    
    if (!generatedJourneyMap || typeof generatedJourneyMap !== 'object') {
      const errorMessage = generatedJourneyMap?.error;
      return (
        <div className="mt-8 text-center text-gray-500">
          {errorMessage 
            ? `Journey Map Generation Failed: ${errorMessage}` 
            : "Select interviews and click Generate Journey Map."
          }
        </div>
      );
    }
    
    return (
      <div className="mt-8">
        <div className="flex justify-end mb-4">
          <ActionButtons 
            type="journey-map"
            data={generatedJourneyMap}
            onSave={handleSaveJourneyMap}
            exportToFigma={handleExportToFigma}
            shareUrl={savedJourneyMapId ? `${window.location.origin}/view-journey-map/${savedJourneyMapId}` : undefined}
            disabled={!generatedJourneyMap}
          />
        </div>
        {/* Use the new JourneyMapPage component for better display */}
        <JourneyMapPage journeyMap={generatedJourneyMap} />
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 relative">
      {generatingJourneyMap && (
        <div className="fixed inset-0 bg-gray-200 bg-opacity-70 z-[9999] flex items-center justify-center">
          <div className="bg-white p-8 rounded-lg shadow-lg">
            <Spin size="large">
              <div className="h-8" />
              <div className="text-gray-600 mt-3">Generating journey map...</div>
            </Spin>
          </div>
        </div>
      )}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Journey Map Generator</h1>
        <Link to="/journey-maps" className="text-blue-500 hover:text-blue-600">
          View All Journey Maps
        </Link>
      </div>

      <div className="mb-8">
        <InterviewSearchSelect 
          onSelectionChange={handleInterviewSelectionChange} 
          selectedInterviewIds={selectedInterviews}
        />

        <Card title="Generate Journey Map" className="mb-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Model
              </label>
              <Select
                className="w-full"
                value={selectedModel}
                onChange={value => setSelectedModel(value)}
              >
                <Select.Option value="gpt-4-turbo">GPT-4 Turbo (Recommended)</Select.Option>
                <Select.Option value="gpt-4">GPT-4</Select.Option>
                <Select.Option value="claude-3.7-sonnet">Claude 3.7 Sonnet (Experimental)</Select.Option>
              </Select>
            </div>

            <Button
              type="primary"
              className="w-full"
              onClick={handleGenerateJourneyMap}
              disabled={selectedInterviews.length === 0 || generatingJourneyMap}
              loading={generatingJourneyMap}
            >
              Generate Journey Map from {selectedInterviews.length} Selected Interview{selectedInterviews.length !== 1 ? 's' : ''}
            </Button>
          </div>
        </Card>
      </div>

      {renderJourneyMapTemplate()}
    </div>
  );
};

export default JourneyMap; 