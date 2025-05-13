import React from 'react';
import './AudioControls.css';

interface AudioControlsProps {
  isRecording: boolean;
  onStartRecording: () => void;
  onStopRecording: () => Promise<void>;
  disabled: boolean;
}

const AudioControls: React.FC<AudioControlsProps> = ({
  isRecording,
  onStartRecording,
  onStopRecording,
  disabled
}) => {
  return (
    <div className="audio-controls">
      {!isRecording ? (
        <button
          className="record-button"
          onClick={onStartRecording}
          disabled={disabled}
          title="Start recording"
        >
          <span className="microphone-icon">🎤</span>
          <span>Record</span>
        </button>
      ) : (
        <button
          className="stop-button"
          onClick={onStopRecording}
          title="Stop recording"
        >
          <span className="stop-icon">⬛</span>
          <span>Stop</span>
        </button>
      )}
      
      {isRecording && (
        <div className="recording-indicator">
          <span className="recording-dot"></span>
          <span className="recording-text">Recording...</span>
        </div>
      )}
    </div>
  );
};

export default AudioControls; 