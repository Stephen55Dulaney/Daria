import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Card, Select, Button, Spin, message } from 'antd';
import PersonaDisplay from './PersonaDisplay';
import InterviewSearchSelect from '../../components/InterviewSearchSelect/index';
import ActionButtons from '../../components/common/ActionButtons';
import { exportToFigma } from '../../utils/export';

const PersonaGenerator: React.FC = () => {
  const [selectedInterviews, setSelectedInterviews] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4');
  const [generatingPersona, setGeneratingPersona] = useState<boolean>(false);
  const [generatedPersona, setGeneratedPersona] = useState<any>(null);
  const [savedPersonaId, setSavedPersonaId] = useState<string | null>(null);

  const handleInterviewSelectionChange = (selectedIds: string[]) => {
    setSelectedInterviews(selectedIds);
  };

  const handleGeneratePersona = async () => {
    if (selectedInterviews.length === 0) {
      message.warning('Please select at least one interview.');
      return;
    }
    setGeneratingPersona(true);
    setGeneratedPersona(null);
    setSavedPersonaId(null);
    try {
      const response = await axios.post('/api/generate_persona', {
        interview_ids: selectedInterviews,
        project_id: 'default',
        model: selectedModel
      });
      console.log('Received data from /api/generate_persona:', response.data);
      setGeneratedPersona(response.data);
    } catch (error: any) {
      console.error('Error generating persona:', error);
      message.error(`Error generating persona: ${error.response?.data?.error || error.message}`);
      setGeneratedPersona(null);
    } finally {
      setGeneratingPersona(false);
    }
  };
  
  const handleSavePersona = async (name: string, description: string) => {
    try {
      const response = await axios.post('/api/save-persona', {
        project_name: name,
        persona_data: {
          ...generatedPersona,
          description
        }
      });
      
      console.log('Save persona response:', response.data);
      
      // The backend may not return an id directly
      if (response.data.id) {
        setSavedPersonaId(response.data.id);
      } else {
        // Check the console for the actual response structure
        message.warning('Persona saved, but sharing might not work. Check console for details.');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error saving persona:', error);
      throw error;
    }
  };
  
  const handleExportToFigma = () => {
    if (generatedPersona) {
      exportToFigma(generatedPersona, 'persona');
    }
  };

  const renderPersonaTemplate = () => {
    if (generatingPersona) {
      return (
        <div className="mt-8 text-center">
          <Spin size="large" tip="Generating Persona..." />
        </div>
      );
    }
    if (!generatedPersona || typeof generatedPersona !== 'object' || !generatedPersona.name) {
      const errorMessage = generatedPersona?.error;
      return (
        <div className="mt-8 text-center text-gray-500">
          {errorMessage 
            ? `Persona Generation Failed: ${errorMessage}` 
            : "Select interviews and click Generate Persona."
          }
        </div>
      );
    }
    
    return (
      <div className="mt-8">
        <div className="flex justify-end mb-4">
          <ActionButtons 
            type="persona"
            data={generatedPersona}
            onSave={handleSavePersona}
            exportToFigma={handleExportToFigma}
            shareUrl={savedPersonaId ? `${window.location.origin}/view-persona/${savedPersonaId}` : undefined}
            disabled={!generatedPersona}
          />
        </div>
        <PersonaDisplay persona={generatedPersona} />
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 relative">
      {generatingPersona && (
        <div className="fixed inset-0 bg-gray-200 bg-opacity-70 z-[9999] flex items-center justify-center">
          <Spin size="large" tip="Generating persona..." />
        </div>
      )}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Persona Generator</h1>
        <Link to="/personas" className="text-blue-500 hover:text-blue-600">
          View All Personas
        </Link>
      </div>

      <div className="mb-8">
        <InterviewSearchSelect 
          onSelectionChange={handleInterviewSelectionChange} 
          selectedInterviewIds={selectedInterviews}
        />

        <Card title="Generate Persona" className="mb-6">
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
              onClick={handleGeneratePersona}
              disabled={selectedInterviews.length === 0 || generatingPersona}
              loading={generatingPersona}
            >
              Generate Persona from {selectedInterviews.length} Selected Interview{selectedInterviews.length !== 1 ? 's' : ''}
            </Button>
          </div>
        </Card>
      </div>

      {renderPersonaTemplate()}
    </div>
  );
};

export default PersonaGenerator; 