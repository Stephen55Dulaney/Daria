import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const CharacterDetail: React.FC = () => {
  const { characterName } = useParams();
  const [character, setCharacter] = useState<any>(null);

  useEffect(() => {
    axios.get('/api/characters').then(res => {
      const found = res.data.characters.find((c: any) => c.name === characterName);
      setCharacter(found);
    });
  }, [characterName]);

  if (!character) return <div>Loading...</div>;

  return (
    <div>
      <h1>{character.display_name || character.name}</h1>
      <h2>{character.role}</h2>
      <p>{character.description}</p>
      <h3>Interview Prompt</h3>
      <pre>{character.interview_prompt}</pre>
      <h3>Analysis Prompt</h3>
      <pre>{character.analysis_prompt}</pre>
    </div>
  );
};

export default CharacterDetail;
