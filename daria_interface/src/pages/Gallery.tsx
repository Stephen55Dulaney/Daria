import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Gallery from '../components/shared/Gallery';
import Select from '../components/shared/Select';
import Card from '../components/shared/Card';
import LoadingSpinner from '../components/shared/LoadingSpinner';
import Button from '../components/shared/Button';
import { analysisService } from '../services/analysisService';
import type { ResearchAssistant, AnalysisResult } from '../services/analysisService';

interface GalleryItem {
  id: string;
  title: string;
  description?: string;
  imageUrl?: string;
  createdAt: string;
  type: 'character' | 'analysis';
}

const GalleryPage: React.FC = () => {
  const { assistantId } = useParams<{ assistantId?: string }>();
  const navigate = useNavigate();
  const [selectedType, setSelectedType] = useState<'all' | 'character' | 'analysis'>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [researchAssistants, setResearchAssistants] = useState<ResearchAssistant[]>([]);
  const [savedAnalyses, setSavedAnalyses] = useState<AnalysisResult[]>([]);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [assistants, analyses] = await Promise.all([
          analysisService.getResearchAssistants(),
          analysisService.getSavedAnalyses(),
        ]);
        setResearchAssistants(assistants);
        setSavedAnalyses(analyses);
      } catch (error) {
        console.error('Failed to load gallery data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  const allItems: GalleryItem[] = [
    ...researchAssistants.map(assistant => ({
      id: assistant.id,
      title: assistant.name,
      description: assistant.description,
      imageUrl: assistant.imageUrl,
      createdAt: new Date().toISOString(),
      type: 'character' as const,
    })),
    ...savedAnalyses.map(analysis => ({
      id: analysis.id,
      title: analysis.title,
      description: analysis.content,
      createdAt: analysis.createdAt,
      type: 'analysis' as const,
    })),
  ];

  const filteredItems = selectedType === 'all'
    ? allItems
    : allItems.filter(item => item.type === selectedType);

  const selectedAssistant = assistantId 
    ? researchAssistants.find(a => a.id === assistantId)
    : null;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (selectedAssistant) {
    return (
      <div className="py-8">
        <div className="flex items-center gap-4 mb-8">
          <Button
            variant="outline"
            onClick={() => navigate('/gallery')}
          >
            ← Back to Gallery
          </Button>
          <h1 className="text-3xl font-bold">{selectedAssistant.name}</h1>
        </div>

        <Card variant="bordered" padding="lg" className="mb-8">
          <div className="flex gap-8">
            {selectedAssistant.imageUrl && (
              <img
                src={selectedAssistant.imageUrl}
                alt={selectedAssistant.name}
                className="w-48 h-48 object-cover rounded-lg"
              />
            )}
            <div>
              <h2 className="text-xl font-semibold mb-4">About {selectedAssistant.name}</h2>
              <p className="text-gray-600">{selectedAssistant.description}</p>
            </div>
          </div>
        </Card>

        <h2 className="text-2xl font-bold mb-6">Analyses by {selectedAssistant.name}</h2>
        <Gallery
          items={savedAnalyses
            .filter(analysis => analysis.assistantId === selectedAssistant.id)
            .map(analysis => ({
              ...analysis,
              type: 'analysis' as const,
            }))}
          onItemClick={(item) => {
            // Handle item click
            console.log('Clicked item:', item);
          }}
        />
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Gallery</h1>
        
        <Select
          options={[
            { value: 'all', label: 'All Items' },
            { value: 'character', label: 'Research Assistants' },
            { value: 'analysis', label: 'Analyses' },
          ]}
          value={selectedType}
          onChange={(value) => setSelectedType(value as 'all' | 'character' | 'analysis')}
          className="w-48"
        />
      </div>

      {filteredItems.length > 0 ? (
        <Gallery
          items={filteredItems}
          onItemClick={(item) => {
            if (item.type === 'character') {
              navigate(`/gallery/${item.id}`);
            } else {
              // Handle analysis item click
              console.log('Clicked analysis:', item);
            }
          }}
        />
      ) : (
        <Card variant="bordered" padding="lg" className="text-center py-12">
          <p className="text-gray-500">No items found in the selected category</p>
        </Card>
      )}
    </div>
  );
};

export default GalleryPage; 