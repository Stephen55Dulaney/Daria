// Audio recording configuration
const SAMPLE_RATE = 16000;  // Match server's expected sample rate
const SILENCE_THRESHOLD = 0.01;
const NOISE_THRESHOLD = 0.02;
const SPEECH_THRESHOLD = 0.1;
const SILENCE_DURATION = 2.0;
const MIN_RECORDING_TIME = 2;
const MAX_RECORDING_TIME = 60;
const MIN_SPEECH_DURATION = 0.1;
const MAX_SILENCE_DURATION = 1.3;  // Changed from 3.0 to 1.3 seconds for faster, more natural interview pace
const MIN_RECORDING_DURATION = 1.0;

let mediaRecorder = null;
let audioContext = null;
let currentStream = null;
let isRecording = false;
let silenceStart = null;
let debugLoggingInterval = null;
let recordingStartTime = null;
let currentAudioLevel = 0;
let isSpeechDetected = false;
let silenceDuration = 0;

async function cleanup() {
    console.log('Cleaning up audio resources');
    isRecording = false;
    stopDebugLogging();
    updateRecordingStatus(false);

    // Stop media recorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        console.log('Stopping MediaRecorder...');
        try {
            mediaRecorder.stop();
        } catch (error) {
            console.error('Error stopping MediaRecorder:', error);
        }
        mediaRecorder = null;
    }

    // Close audio context
    if (audioContext) {
        try {
            await audioContext.close();
        } catch (error) {
            console.error('Error closing AudioContext:', error);
        }
        audioContext = null;
    }

    // Stop all tracks in the stream
    if (currentStream) {
        currentStream.getTracks().forEach(track => {
            try {
                track.stop();
            } catch (error) {
                console.error('Error stopping track:', error);
            }
        });
        currentStream = null;
    }

    // Reset all state variables
    silenceStart = null;
    recordingStartTime = null;
    currentAudioLevel = 0;
    isSpeechDetected = false;
    silenceDuration = 0;
}

function startDebugLogging() {
    if (debugLoggingInterval) {
        clearInterval(debugLoggingInterval);
    }
    debugLoggingInterval = setInterval(() => {
        if (audioContext && isRecording) {
            console.log(`[${(Date.now() - recordingStartTime) / 1000}s] Audio Level: ${currentAudioLevel.toFixed(3)} | Speech Detected: ${isSpeechDetected} | Silence Duration: ${silenceDuration.toFixed(1)}s`);
        }
    }, 500);
}

function stopDebugLogging() {
    if (debugLoggingInterval) {
        clearInterval(debugLoggingInterval);
        debugLoggingInterval = null;
    }
}

async function setupAudioContext(stream) {
    if (audioContext) {
        await cleanup();
    }

    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);

    function checkAudioLevel() {
        if (!isRecording || !audioContext) return;

        analyser.getFloatTimeDomainData(dataArray);
        const rms = Math.sqrt(dataArray.reduce((sum, val) => sum + val * val, 0) / bufferLength);
        currentAudioLevel = rms;

        // Speech detection logic
        if (rms > SPEECH_THRESHOLD) {
            if (!isSpeechDetected) {
                console.log(`[${(Date.now() - recordingStartTime) / 1000}s] Speech detected (${rms.toFixed(3)})`);
            }
            isSpeechDetected = true;
            silenceStart = null;
            silenceDuration = 0;
        } else if (rms < SILENCE_THRESHOLD) {
            if (!silenceStart) {
                silenceStart = Date.now();
                console.log(`[${(Date.now() - recordingStartTime) / 1000}s] Silence started`);
            }
            silenceDuration = (Date.now() - silenceStart) / 1000;

            if (silenceDuration >= SILENCE_DURATION && Date.now() - recordingStartTime > MIN_RECORDING_TIME * 1000) {
                console.log(`[${(Date.now() - recordingStartTime) / 1000}s] Stopping due to silence`);
                stopRecording();
                return;
            }
        }

        // Check for maximum recording time
        if (Date.now() - recordingStartTime > MAX_RECORDING_TIME * 1000) {
            console.log(`[${MAX_RECORDING_TIME}s] Stopping due to maximum duration`);
            stopRecording();
            return;
        }

        if (isRecording) {
            requestAnimationFrame(checkAudioLevel);
        }
    }

    requestAnimationFrame(checkAudioLevel);
}

async function startRecording() {
    try {
        await cleanup();
        
        currentStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                channelCount: 1,
                sampleRate: SAMPLE_RATE
            } 
        });
        
        await setupAudioContext(currentStream);
        
        // Create a MediaRecorder with specific options
        const options = {
            mimeType: 'audio/webm',
            audioBitsPerSecond: 128000,
            sampleRate: SAMPLE_RATE,
            channelCount: 1
        };
        
        mediaRecorder = new MediaRecorder(currentStream, options);
        
        isRecording = true;
        recordingStartTime = Date.now();
        isSpeechDetected = false;
        silenceStart = null;
        silenceDuration = 0;
        currentAudioLevel = 0;
        
        startDebugLogging();
        updateRecordingStatus(true);
        console.log('Recording ready');
        
        return mediaRecorder;
        
    } catch (error) {
        console.error('Error starting recording:', error);
        updateRecordingStatus(false);
        throw error;
    }
}

async function stopRecording() {
    if (!isRecording) return;
    
    try {
        console.log('Stopping recording...');
        console.log('MediaRecorder state before stop:', mediaRecorder?.state);
        updateRecordingStatus(false);
        await cleanup();
        return true;
    } catch (error) {
        console.error('Error stopping recording:', error);
        updateRecordingStatus(false);
        return false;
    }
}

// Text-to-speech function
async function speak(text) {
    try {
        const response = await fetch('/text_to_speech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text })
        });
        
        if (!response.ok) {
            throw new Error('Text-to-speech request failed');
        }
        
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        return new Promise((resolve, reject) => {
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                resolve();
            };
            audio.onerror = reject;
            audio.play();
        });
    } catch (error) {
        console.error('Error in speak function:', error);
        throw error;
    }
}

// Make functions available globally
window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.cleanup = cleanup;
window.listen = listen;
window.speak = speak;

// Add the listen function
async function listen() {
    try {
        // Initialize recording
        const chunks = [];
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyzer = audioContext.createAnalyser();
        analyzer.fftSize = 2048;
        source.connect(analyzer);

        const recorder = new MediaRecorder(stream);
        let silenceStartTime = null;
        let speechDetected = false;
        let recordingStartTime = Date.now();
        
        // Create buffer for analyzing audio levels
        const dataArray = new Float32Array(analyzer.frequencyBinCount);
        
        // Monitor audio levels
        const audioLevelInterval = setInterval(() => {
            analyzer.getFloatTimeDomainData(dataArray);
            const audioLevel = Math.max(...dataArray.map(Math.abs));
            const currentTime = (Date.now() - recordingStartTime) / 1000;
            
            console.log(`[${currentTime.toFixed(3)}s] Audio Level: ${audioLevel.toFixed(3)} | Speech Detected: ${speechDetected} | Silence Duration: ${silenceStartTime ? ((Date.now() - silenceStartTime) / 1000).toFixed(1) : '0.0'}s`);
            
            if (audioLevel > SILENCE_THRESHOLD) {
                speechDetected = true;
                silenceStartTime = null;
            } else if (!silenceStartTime) {
                silenceStartTime = Date.now();
                console.log(`[${currentTime.toFixed(3)}s] Silence started`);
            }
            
            // Only stop if we've detected speech and then silence
            if (speechDetected && silenceStartTime) {
                const silenceDuration = (Date.now() - silenceStartTime) / 1000;
                const totalDuration = (Date.now() - recordingStartTime) / 1000;
                
                if (silenceDuration >= MAX_SILENCE_DURATION && totalDuration >= MIN_RECORDING_DURATION) {
                    console.log(`[${currentTime.toFixed(3)}s] Stopping due to silence`);
                    clearInterval(audioLevelInterval);
                    stopRecording();
                }
            }
        }, 500);

        function stopRecording() {
            console.log('Stopping recording...');
            console.log('MediaRecorder state before stop:', recorder.state);
            if (recorder.state === 'recording') {
                recorder.stop();
                stream.getTracks().forEach(track => track.stop());
                clearInterval(audioLevelInterval);
            }
        }

        return new Promise((resolve) => {
            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunks.push(e.data);
                }
            };
            
            recorder.onstop = async () => {
                try {
                    // Create blob with specific type
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    console.log('Audio blob created:', blob.size, 'bytes');
                    
                    const formData = new FormData();
                    formData.append('audio', blob, 'recording.webm');
                    
                    console.log('Sending audio to server...', {
                        project: window.PROJECT_NAME,
                        blobSize: blob.size
                    });
                    
                    const response = await fetch(`/process_audio?project_name=${encodeURIComponent(window.PROJECT_NAME)}`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        console.error('Server error:', response.status);
                        const errorText = await response.text();
                        console.error('Server error details:', errorText);
                        resolve('No speech detected');
                        return;
                    }
                    
                    const result = await response.json();
                    console.log('Transcription result:', result);
                    
                    // Handle should_stop_interview flag
                    if (result.should_stop_interview) {
                        console.log('Interview should stop');
                        // Reset the interview state (don't use await here)
                        resetInterviewState(true).catch(err => console.error('Error resetting interview state:', err));
                        // Make sure to resolve the promise with the transcription
                        resolve(result.transcription || 'No speech detected');
                        return;
                    }
                    
                    resolve(result.transcription || 'No speech detected');
                    
                } catch (error) {
                    console.error('Error processing audio:', error);
                    resolve('Error recording audio');
                }
            };
            
            // Start recording with 100ms chunks
            console.log('Starting MediaRecorder...');
            recorder.start(100);
            console.log('MediaRecorder state:', recorder.state);
        });
    } catch (error) {
        console.error('Error in listen function:', error);
        return 'Error recording audio';
    }
}

// Add visual feedback for recording state
function updateRecordingStatus(isRecording) {
    const status = document.getElementById('recordingStatus');
    if (status) {
        if (isRecording) {
            status.textContent = '🎤 Recording...';
            status.classList.add('recording');
        } else {
            status.textContent = 'Click "Start Interview" to begin';
            status.classList.remove('recording');
        }
    }
} 