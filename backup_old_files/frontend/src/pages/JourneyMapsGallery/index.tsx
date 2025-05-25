import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Card, Empty, Spin, message } from 'antd';
import { EditOutlined, DeleteOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';

interface JourneyMap {
  id: string;
  project_name: string;
  created_at: string;
  filename: string;
}

const JourneyMapsGallery: React.FC = () => {
  const [journeyMaps, setJourneyMaps] = useState<JourneyMap[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJourneyMaps();
  }, []);

  const fetchJourneyMaps = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/journey-maps');
      setJourneyMaps(response.data);
    } catch (error) {
      console.error('Error fetching journey maps:', error);
      message.error('Failed to load journey maps');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this journey map?')) {
      return;
    }
    
    try {
      await axios.post(`/delete_journey_map/${id}`);
      message.success('Journey map deleted successfully');
      fetchJourneyMaps();
    } catch (error) {
      console.error('Error deleting journey map:', error);
      message.error('Failed to delete journey map');
    }
  };

  const handleDownload = (id: string) => {
    window.open(`/view-journey-map/${id}?download=true`, '_blank');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Journey Map Gallery</h1>
        <Link 
          to="/journey-map" 
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition-colors"
        >
          Create New Journey Map
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Spin size="large" />
        </div>
      ) : journeyMaps.length === 0 ? (
        <Empty
          description="No journey maps found"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {journeyMaps.map(journeyMap => (
            <Card
              key={journeyMap.id}
              className="h-full shadow-sm hover:shadow-md transition-shadow"
              actions={[
                <Link to={`/view-journey-map/${journeyMap.id}`} key="view">
                  <EyeOutlined /> View
                </Link>,
                <Link to={`/edit-journey-map/${journeyMap.id}`} key="edit">
                  <EditOutlined /> Edit
                </Link>,
                <span onClick={() => handleDownload(journeyMap.id)} key="download" className="cursor-pointer">
                  <DownloadOutlined /> Download
                </span>,
                <span onClick={() => handleDelete(journeyMap.id)} key="delete" className="cursor-pointer text-red-500">
                  <DeleteOutlined /> Delete
                </span>,
              ]}
            >
              <div className="h-full flex flex-col">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-2">{journeyMap.project_name}</h3>
                  <p className="text-gray-500 text-sm">Created: {formatDate(journeyMap.created_at)}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default JourneyMapsGallery; 