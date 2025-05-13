import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Spin, message } from 'antd';
import { JourneyMapPage } from '../../components/JourneyMap/JourneyMapPage';

const ViewJourneyMap: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [journeyMap, setJourneyMap] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`/api/journey-maps/${id}`)
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          message.error(data.error);
          setJourneyMap(null);
        } else {
          setJourneyMap(data);
        }
      })
      .catch(() => {
        message.error('Failed to load journey map');
        setJourneyMap(null);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex justify-center py-12"><Spin size="large" /></div>;
  if (!journeyMap) return <div className="text-center text-red-500 py-12">Journey map not found.</div>;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <Link to="/journey-maps" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">&larr; Back to Journey Map Gallery</Link>
      <JourneyMapPage journeyMap={journeyMap} />
    </div>
  );
};

export default ViewJourneyMap; 