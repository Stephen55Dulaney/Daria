import React, { useState, useEffect } from 'react';
import Select from '../components/shared/Select';
import Button from '../components/shared/Button';
import Card from '../components/shared/Card';
import LoadingSpinner from '../components/shared/LoadingSpinner';
import Gallery from '../components/shared/Gallery';
import { analysisService } from '../services/analysisService';
import type { ResearchAssistant, DiscussionGuide, Session, AnalysisResult } from '../services/analysisService';
import { toast } from 'react-toastify';

const Analysis: React.FC = () => {
  const [selectedGuide, setSelectedGuide] = useState('');
  const [selectedSession, setSelectedSession] = useState('');
  const [selectedAssistant, setSelectedAssistant] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [savedAnalyses, setSavedAnalyses] = useState<AnalysisResult[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // State for options
  const [researchAssistants, setResearchAssistants] = useState<ResearchAssistant[]>([]);
  const [discussionGuides, setDiscussionGuides] = useState<DiscussionGuide[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [assistants, guides] = await Promise.all([
          analysisService.getResearchAssistants(),
          analysisService.getDiscussionGuides(),
        ]);
        setResearchAssistants(assistants);
        setDiscussionGuides(guides);
        toast.info('Analysis page loaded successfully!'); // Test toast
      } catch (error) {
        console.error('Failed to load initial data:', error);
        toast.error('Failed to load initial data. Please try again.');
      }
    };

    loadInitialData();
  }, []);

  // Load sessions when guide is selected
  useEffect(() => {
    const loadSessions = async () => {
      if (selectedGuide) {
        try {
          const guideSessions = await analysisService.getSessionsByGuide(selectedGuide);
          setSessions(guideSessions);
        } catch (error) {
          console.error('Failed to load sessions:', error);
          toast.error('Failed to load sessions. Please try again.');
        }
      } else {
        setSessions([]);
      }
    };

    loadSessions();
  }, [selectedGuide]);

  // Load saved analyses
  useEffect(() => {
    const loadSavedAnalyses = async () => {
      try {
        const saved = await analysisService.getSavedAnalyses();
        setSavedAnalyses(saved);
      } catch (error) {
        console.error('Failed to load saved analyses:', error);
        toast.error('Failed to load saved analyses. Please try again.');
      }
    };

    loadSavedAnalyses();
  }, []);

  const handleAnalyze = async () => {
    setIsLoading(true);
    try {
      const result = await analysisService.runAnalysis(
        selectedGuide,
        selectedSession,
        selectedAssistant
      );
      setAnalysisResult(result);
      toast.success('Analysis completed successfully!');
    } catch (error) {
      console.error('Analysis failed:', error);
      toast.error('Analysis failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveToGallery = async (item: AnalysisResult | null) => {
    if (!item || !selectedAssistant) {
      toast.error('No analysis or assistant selected to save.');
      return;
    }

    setIsSaving(true);
    try {
      // Find the selected assistant's ID
      const assistant = researchAssistants.find(a => a.name === selectedAssistant);
      if (!assistant) {
        throw new Error('Selected assistant not found');
      }

      const analysisToSave = {
        ...item,
        assistantId: assistant.id, // Use the ID instead of name
        createdAt: new Date().toISOString()
      };
      
      const savedItem = await analysisService.saveToGallery(analysisToSave);
      setSavedAnalyses(prev => [...prev, savedItem]);
      toast.success('Analysis saved to gallery successfully!');
    } catch (error) {
      console.error('Failed to save to gallery:', error);
      toast.error('Failed to save to gallery. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadAnalysis = () => {
    if (!analysisResult) return;
    
    const blob = new Blob([JSON.stringify(analysisResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Analysis downloaded successfully!');
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Analysis</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card variant="bordered" padding="lg">
          <h2 className="text-xl font-semibold mb-4">Analysis Configuration</h2>
          
          <div className="space-y-4">
            <Select
              label="Research Assistant"
              options={researchAssistants.map(assistant => ({
                value: assistant.id,
                label: assistant.name,
              }))}
              value={selectedAssistant}
              onChange={setSelectedAssistant}
              placeholder="Select a research assistant"
            />

            <Select
              label="Discussion Guide"
              options={discussionGuides.map(guide => ({
                value: guide.id,
                label: guide.title,
              }))}
              value={selectedGuide}
              onChange={setSelectedGuide}
              placeholder="Select a discussion guide"
            />

            <Select
              label="Session"
              options={sessions.map(session => ({
                value: session.id,
                label: `${session.title} - ${new Date(session.date).toLocaleDateString()}`,
              }))}
              value={selectedSession}
              onChange={setSelectedSession}
              placeholder="Select a session"
              disabled={!selectedGuide}
            />

            <Button
              variant="primary"
              size="lg"
              isLoading={isLoading}
              onClick={handleAnalyze}
              disabled={!selectedAssistant || !selectedGuide || !selectedSession}
              fullWidth
            >
              Analyze
            </Button>
          </div>
        </Card>

        <Card variant="bordered" padding="lg">
          <div className="d-flex justify-content-between align-items-center card-header mb-4">
            <h5 className="mb-0">Analysis Results</h5>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => handleSaveToGallery(analysisResult)}
                disabled={!analysisResult || isSaving}
                isLoading={isSaving}
              >
                Save to Gallery
              </Button>
              <Button
                variant="outline"
                onClick={handleDownloadAnalysis}
                disabled={!analysisResult}
              >
                Download Analysis
              </Button>
            </div>
          </div>
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <LoadingSpinner size="lg" />
            </div>
          ) : analysisResult ? (
            <div>
              <h3 className="text-lg font-medium mb-2">{analysisResult.title}</h3>
              <p className="text-gray-600 mb-4">{analysisResult.content}</p>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              Select options and click Analyze to see results
            </p>
          )}
        </Card>
      </div>

      {savedAnalyses.length > 0 && (
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">Saved Analyses</h2>
          <Gallery
            items={savedAnalyses.map(analysis => ({
              ...analysis,
              type: 'analysis',
            }))}
            onItemClick={(item) => {
              // Handle item click
              console.log('Clicked item:', item);
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Analysis; 