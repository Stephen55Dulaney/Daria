import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Card, Select, Button, Spin, Tooltip, Popover, Checkbox } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import PersonaDisplay from './PersonaDisplay';

interface Interview {
  id: string;
  title: string;
  date: string;
  type: string;
  preview?: string;
  transcript?: string;
}

interface Project {
  id: string;
  name: string;
}

const PersonaGenerator: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [selectedInterviews, setSelectedInterviews] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4');
  const [loading, setLoading] = useState<boolean>(false);
  const [generatedPersona, setGeneratedPersona] = useState<any>(null);

  useEffect(() => {
    // Fetch projects on component mount
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await axios.get('/api/projects');
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  };

  const fetchInterviews = async (projectId: string) => {
    try {
      const response = await axios.get(`/api/projects/${projectId}/interviews`);
      setInterviews(response.data);
      // Debug: log interviews to console
      console.log('Loaded interviews:', response.data);
    } catch (error) {
      console.error('Error fetching interviews:', error);
    }
  };

  const handleProjectChange = (value: string) => {
    setSelectedProject(value);
    setSelectedInterviews([]);
    if (value) {
      fetchInterviews(value);
    } else {
      setInterviews([]);
    }
  };

  const handleGeneratePersona = async () => {
    if (!selectedProject || selectedInterviews.length === 0) {
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post('/api/generate_persona', {
        project_id: selectedProject,
        interview_ids: selectedInterviews,
        model: selectedModel
      });
      setGeneratedPersona(response.data);
      // Debug: log persona JSON to console
      console.log('Generated persona JSON:', response.data);
    } catch (error) {
      console.error('Error generating persona:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderInterviewCard = (interview: Interview) => {
    const isSelected = selectedInterviews.includes(interview.id);
    // Add a preview of the transcript or summary if available
    const preview = interview.preview || interview.transcript?.slice(0, 120) || 'No preview available';
    const previewContent = (
      <div className="space-y-2">
        <div className="font-semibold text-base">{interview.title}</div>
        <div className="text-xs text-gray-500">{interview.type}</div>
        <div className="text-xs text-gray-400">{interview.date}</div>
        <div className="text-xs text-gray-700 mt-2 line-clamp-3">{preview}</div>
      </div>
    );
    return (
      <Popover content={previewContent} title="Metadata Preview" placement="bottom" key={interview.id}>
        <Card
          key={interview.id}
          className={`transition-all flex flex-col justify-between items-start ${isSelected ? 'border-blue-500 shadow-md' : ''}`}
          style={{ cursor: 'pointer', width: 220, height: 220, minWidth: 220, minHeight: 220, maxWidth: 220, maxHeight: 220, margin: '0 auto' }}
          onClick={() => {
            if (isSelected) {
              setSelectedInterviews(selectedInterviews.filter(id => id !== interview.id));
            } else {
              setSelectedInterviews([...selectedInterviews, interview.id]);
            }
          }}
        >
          <div className="flex items-center justify-between w-full mb-2">
            <Checkbox checked={isSelected} onChange={e => {
              e.stopPropagation();
              if (isSelected) {
                setSelectedInterviews(selectedInterviews.filter(id => id !== interview.id));
              } else {
                setSelectedInterviews([...selectedInterviews, interview.id]);
              }
            }} />
            <div className="flex-1 ml-2">
              <div className="font-semibold text-base truncate w-36">{interview.title}</div>
              <div className="text-xs text-gray-500 truncate">{interview.type}</div>
              <div className="text-xs text-gray-400">{interview.date}</div>
            </div>
          </div>
          <div className="flex gap-2 mt-2 text-xs text-blue-600">
            <Link to={`/transcript/${interview.id}`}>Transcript</Link>
            <Link to={`/analysis/${interview.id}`}>Analysis</Link>
            <Link to={`/metadata/${interview.id}`}>Metadata</Link>
          </div>
          {/* Add preview at the bottom of the card */}
          <div className="mt-4 text-xs text-gray-700 line-clamp-3">{preview}</div>
        </Card>
      </Popover>
    );
  };

  const renderPersonaTemplate = () => {
    if (loading) return null;
    if (!generatedPersona) return <div className="mt-8 text-center text-gray-500">No persona generated yet or LLM did not return a persona.</div>;

    // Handle array of personas
    if (Array.isArray(generatedPersona)) {
      return (
        <div className="mt-8 space-y-8">
          {generatedPersona.map((persona: any, idx: number) => (
            <PersonaDisplay key={persona.name || idx} persona={persona} />
          ))}
        </div>
      );
    }
    // Handle { personas: [...] }
    if (generatedPersona.personas && Array.isArray(generatedPersona.personas)) {
      return (
        <div className="mt-8 space-y-8">
          {generatedPersona.personas.map((persona: any, idx: number) => (
            <PersonaDisplay key={persona.name || idx} persona={persona} />
          ))}
        </div>
      );
    }
    // Handle { persona: {...} }
    if (generatedPersona.persona && typeof generatedPersona.persona === 'object') {
      return <div className="mt-8"><PersonaDisplay persona={generatedPersona.persona} /></div>;
    }
    // Single persona object
    return <div className="mt-8"><PersonaDisplay persona={generatedPersona} /></div>;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 relative">
      {/* Busy overlay */}
      {loading && (
        <div className="fixed inset-0 bg-gray-200 bg-opacity-80 z-[9999] flex items-center justify-center">
          <Spin size="large" tip="Generating persona..." />
        </div>
      )}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Persona Generator</h1>
        <Link to="/personas" className="text-blue-500 hover:text-blue-600">
          View All Personas
        </Link>
      </div>

      {/* Configuration/Form Area - full width */}
      <div className="mb-8">
        <Card title="Configuration" className="mb-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Project
              </label>
              <Select
                className="w-full"
                placeholder="Choose a project"
                value={selectedProject}
                onChange={handleProjectChange}
              >
                {projects.map(project => (
                  <Select.Option key={project.id} value={project.id}>
                    {project.name}
                  </Select.Option>
                ))}
              </Select>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <h2 className="text-base font-semibold mb-2">Transcript Preview</h2>
              <div className="grid grid-cols-3 gap-4">
                {interviews.slice(0, 9).map(interview => renderInterviewCard(interview))}
                {interviews.length === 0 && (
                  <p className="text-gray-500 text-center py-4 col-span-3">
                    {selectedProject ? 'No interviews available for this project' : 'Select a project to view interviews'}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Model
              </label>
              <Select
                className="w-full"
                value={selectedModel}
                onChange={value => setSelectedModel(value)}
              >
                <Select.Option value="gpt-4">GPT-4</Select.Option>
                <Select.Option value="claude-3.7-sonnet">Claude 3.7 Sonnet</Select.Option>
                <Select.Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Select.Option>
              </Select>
            </div>

            <Button
              type="primary"
              className="w-full"
              onClick={handleGeneratePersona}
              disabled={!selectedProject || selectedInterviews.length === 0 || loading}
            >
              {loading ? <Spin size="small" /> : 'Generate Persona'}
            </Button>
          </div>
        </Card>

        <Card title="Selected Interviews" extra={<InfoCircleOutlined />}>
          <p className="text-sm text-gray-500 mb-2">
            {selectedInterviews.length} interview(s) selected
          </p>
          {selectedInterviews.length > 0 ? (
            <ul className="list-disc list-inside">
              {selectedInterviews.map(id => {
                const interview = interviews.find(i => i.id === id);
                return interview ? (
                  <li key={id} className="text-sm text-gray-600">
                    {interview.title}
                  </li>
                ) : null;
              })}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No interviews selected</p>
          )}
        </Card>
      </div>

      {/* Persona display area: full width, stacked below all form elements */}
      {renderPersonaTemplate()}
      {/* Raw persona JSON dump for debugging */}
      {generatedPersona && (
        <div className="mt-8 p-4 bg-gray-100 rounded-lg">
          <h2 className="text-xl font-bold mb-2">Raw Persona Object</h2>
          <pre className="whitespace-pre-wrap text-xs bg-white p-2 rounded border overflow-x-auto">
            {JSON.stringify(generatedPersona, null, 2)}
          </pre>
          {/* Also show key-value pairs for top-level keys */}
          <div className="mt-4 space-y-4">
            {Object.entries(generatedPersona).map(([key, value]) => (
              <div key={key} className="bg-white p-2 rounded border">
                <div className="font-semibold text-indigo-700 mb-1">{key}</div>
                <div className="text-xs text-gray-800">
                  {typeof value === 'object' ? (
                    <pre className="whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                  ) : (
                    String(value)
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PersonaGenerator; 