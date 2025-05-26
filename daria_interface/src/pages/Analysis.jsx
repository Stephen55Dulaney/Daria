import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Card, Button, Spinner, Alert } from 'react-bootstrap';

const Analysis = () => {
    const [discussionGuides, setDiscussionGuides] = useState([]);
    const [selectedGuide, setSelectedGuide] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [selectedSessions, setSelectedSessions] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [selectedCharacter, setSelectedCharacter] = useState(null);
    const [analysisPrompt, setAnalysisPrompt] = useState('');
    const [selectedModel, setSelectedModel] = useState('gpt-4');
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [status, setStatus] = useState('');

    // Fetch discussion guides
    useEffect(() => {
        const fetchGuides = async () => {
            try {
                setStatus('Loading discussion guides...');
                const response = await fetch('/api/discussion_guides');
                const data = await response.json();
                if (data.success) {
                    setDiscussionGuides(data.guides);
                    setStatus('');
                } else {
                    setError('Failed to fetch discussion guides: ' + data.error);
                }
            } catch (err) {
                setError('Failed to fetch discussion guides: ' + err.message);
            }
        };
        fetchGuides();
    }, []);

    // Fetch characters
    useEffect(() => {
        const fetchCharacters = async () => {
            try {
                setStatus('Loading characters...');
                const response = await fetch('/api/characters');
                const data = await response.json();
                if (data.success) {
                    setCharacters(data.characters);
                    setStatus('');
                } else {
                    setError('Failed to fetch characters: ' + data.error);
                }
            } catch (err) {
                setError('Failed to fetch characters: ' + err.message);
            }
        };
        fetchCharacters();
    }, []);

    // Fetch sessions when guide is selected
    useEffect(() => {
        if (selectedGuide) {
            const fetchSessions = async () => {
                try {
                    setStatus('Loading sessions...');
                    const response = await fetch(`/api/discussion_guide/${selectedGuide}/sessions`);
                    const data = await response.json();
                    if (data.success) {
                        setSessions(data.sessions);
                        setStatus('');
                    } else {
                        setError('Failed to fetch sessions: ' + data.error);
                    }
                } catch (err) {
                    setError('Failed to fetch sessions: ' + err.message);
                }
            };
            fetchSessions();
        }
    }, [selectedGuide]);

    // Update analysis prompt when character is selected
    useEffect(() => {
        if (selectedCharacter) {
            const fetchCharacterPrompt = async () => {
                try {
                    setStatus('Loading character prompt...');
                    const response = await fetch(`/api/character/${selectedCharacter}`);
                    const data = await response.json();
                    const prompt = data.analysis_prompt || (data.character && data.character.analysis_prompt);
                    if (data.success && prompt) {
                        setAnalysisPrompt(prompt);
                        setStatus('');
                    } else {
                        setError('Failed to fetch character prompt: ' + (data.error || 'No prompt found'));
                    }
                } catch (err) {
                    setError('Failed to fetch character prompt: ' + err.message);
                }
            };
            fetchCharacterPrompt();
        }
    }, [selectedCharacter]);

    const handleSessionSelection = (sessionId) => {
        setSelectedSessions(prev => {
            if (prev.includes(sessionId)) {
                return prev.filter(id => id !== sessionId);
            }
            return [...prev, sessionId];
        });
    };

    const analyzeSessions = async () => {
        if (!selectedSessions.length || !selectedCharacter || !analysisPrompt) {
            setError('Please select sessions, a character, and ensure the analysis prompt is set');
            return;
        }

        setLoading(true);
        setError(null);
        setStatus('Starting analysis...');
        setAnalysis(null);

        try {
            setStatus('Sending request to analyze sessions...');
            const response = await fetch('/api/research_session/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_ids: selectedSessions,
                    character: selectedCharacter,
                    prompt: analysisPrompt,
                    model: selectedModel
                })
            });

            setStatus('Processing analysis results...');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to analyze sessions');
            }

            setAnalysis(data.analysis);
            setStatus('Analysis complete!');
        } catch (err) {
            setError('Analysis failed: ' + err.message);
            setStatus('Analysis failed. Please check the error message above.');
        } finally {
            setLoading(false);
        }
    };

    const downloadAnalysis = () => {
        if (!analysis) return;
        
        const blob = new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleSaveToGallery = async (analysis) => {
        if (!analysis || !selectedCharacter) {
            setError('No analysis or character selected to save.');
            return;
        }
        try {
            setStatus('Saving analysis to gallery...');
            const response = await fetch('/api/gallery/analysis', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...analysis,
                    assistantId: selectedCharacter // or use the correct property for your character ID
                }),
            });
            const data = await response.json();
            if (response.ok) {
                setStatus('Analysis saved to gallery!');
            } else {
                setError('Failed to save analysis: ' + (data.error || 'Unknown error'));
            }
        } catch (err) {
            setError('Failed to save analysis: ' + err.message);
        }
    };

    return (
        <Container className="py-4">
            <h2 className="mb-4">Research Analysis</h2>
            
            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}

            {status && (
                <Alert variant="info" className="mb-4">
                    {status}
                </Alert>
            )}

            {/* Discussion Guide Dropdown */}
            <Row className="mb-4">
                <Col md={6}>
                    <Form.Group className="mb-3">
                        <Form.Label>Discussion Guide</Form.Label>
                        <Form.Select
                            value={selectedGuide || ''}
                            onChange={(e) => setSelectedGuide(e.target.value)}
                        >
                            <option value="">Select a discussion guide...</option>
                            {discussionGuides.map((guide) => (
                                <option key={guide.id} value={guide.id}>
                                    {guide.title}
                                </option>
                            ))}
                        </Form.Select>
                    </Form.Group>
                </Col>
            </Row>

            {/* Session Cards - now directly below guide dropdown */}
            {selectedGuide && (
                <Card className="mb-4">
                    <Card.Header>Research Sessions</Card.Header>
                    <Card.Body>
                        <Row>
                            {sessions.map((session, idx) => (
                                <Col md={6} lg={4} key={session.id + '-' + idx} className="mb-3">
                                    <Card className={`h-100 position-relative shadow-sm ${selectedSessions.includes(session.id) ? 'border-primary' : ''}`}
                                        style={{ minHeight: 160 }}>
                                        <Form.Check
                                            type="checkbox"
                                            id={`session-${session.id}`}
                                            checked={selectedSessions.includes(session.id)}
                                            onChange={() => handleSessionSelection(session.id)}
                                            className="position-absolute" 
                                            style={{ top: 12, right: 12, zIndex: 2 }}
                                            title="Select session for analysis"
                                        />
                                        <Card.Body style={{ paddingTop: 24 }}>
                                            <h6 className="mb-1">{session.title || session.id}</h6>
                                            <div className="text-muted small mb-1">
                                                {session.project && <span>{session.project} <br /></span>}
                                                {session.interview_type && <span>{session.interview_type.replace(/_/g, ' ')} <br /></span>}
                                                {session.character && <span>Character: {session.character} <br /></span>}
                                            </div>
                                            <div className="text-muted small">
                                                {new Date(session.created_at).toLocaleString()}
                                            </div>
                                        </Card.Body>
                                    </Card>
                                </Col>
                            ))}
                        </Row>
                    </Card.Body>
                </Card>
            )}

            {/* Character Dropdown and Analysis Config */}
            <Row className="mb-4">
                <Col md={6}>
                    <Form.Group className="mb-3">
                        <Form.Label>Research Assistant Character</Form.Label>
                        <Form.Select
                            value={selectedCharacter || ''}
                            onChange={(e) => setSelectedCharacter(e.target.value)}
                        >
                            <option value="">Select a character...</option>
                            {characters.map((char) => (
                                <option key={char.name} value={char.name}>
                                    {char.name}
                                </option>
                            ))}
                        </Form.Select>
                    </Form.Group>
                </Col>
            </Row>

            {selectedCharacter && (
                <Card className="mb-4">
                    <Card.Header>Analysis Configuration</Card.Header>
                    <Card.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Analysis Prompt</Form.Label>
                            <Form.Control
                                as="textarea"
                                rows={10}
                                style={{ minHeight: 180 }}
                                value={analysisPrompt}
                                onChange={(e) => setAnalysisPrompt(e.target.value)}
                                placeholder="Enter or edit the analysis prompt..."
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Model Selection</Form.Label>
                            <Form.Select
                                value={selectedModel}
                                onChange={(e) => setSelectedModel(e.target.value)}
                            >
                                <option value="gpt-4">GPT-4</option>
                                <option value="gpt-4-1106-preview">GPT-4 1106 Preview</option>
                                <option value="gpt-4-mini">GPT-4 Mini</option>
                                <option value="claude-3-haiku">Claude 3 Haiku</option>
                                <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                            </Form.Select>
                        </Form.Group>
                        <Button
                            variant="primary"
                            size="lg"
                            className="w-100"
                            onClick={analyzeSessions}
                            disabled={loading || !selectedSessions.length}
                        >
                            {loading ? (
                                <>
                                    <Spinner as="span" animation="border" size="sm" className="me-2" />
                                    Analyzing...
                                </>
                            ) : `Analyze Selected Sessions with ${selectedCharacter}`}
                        </Button>
                    </Card.Body>
                </Card>
            )}

            {analysis && (
                <Card className="mb-4">
                    <Card.Header className="d-flex justify-content-between align-items-center">
                        <h5 className="mb-0">Analysis Results</h5>
                        <Button variant="success" onClick={downloadAnalysis}>
                            Download Analysis
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => handleSaveToGallery(analysis)}
                        >
                            Save to Gallery test
                        </Button>
                    </Card.Header>
                    <Card.Body>
                        <div>
                            <h6>Summary</h6>
                            <p style={{ fontWeight: 500 }}>{analysis.summary}</p>
                            <hr />
                            <h6 className="mt-4">Key Findings</h6>
                            {analysis.key_findings.map((finding, index) => (
                                <div key={index} className="mb-3 p-2" style={{ background: '#f8f9fa', borderRadius: 6 }}>
                                    <strong>{finding.insight}</strong>
                                    <p className="mb-1">{finding.importance}</p>
                                    {finding.supporting_quotes.map((quote, qIndex) => (
                                        <blockquote key={qIndex} className="text-muted small" style={{ marginLeft: 12 }}>
                                            "{quote}"
                                        </blockquote>
                                    ))}
                                </div>
                            ))}
                            <h6 className="mt-4">User Needs</h6>
                            {analysis.user_needs.map((need, index) => (
                                <div key={index} className="mb-3 p-2" style={{ background: '#f8f9fa', borderRadius: 6 }}>
                                    <strong>{need.need}</strong>
                                    <p className="mb-1">{need.context}</p>
                                    <span className={`badge bg-${need.priority === 'High' ? 'danger' : need.priority === 'Medium' ? 'warning' : 'info'}`}>{need.priority} Priority</span>
                                </div>
                            ))}
                            <h6 className="mt-4">Pain Points</h6>
                            {analysis.pain_points.map((point, index) => (
                                <div key={index} className="mb-3 p-2" style={{ background: '#f8f9fa', borderRadius: 6 }}>
                                    <strong>{point.issue}</strong>
                                    <p className="mb-1">{point.impact}</p>
                                    <span className="badge bg-secondary">{point.frequency}</span>
                                </div>
                            ))}
                            <h6 className="mt-4">Opportunities</h6>
                            {analysis.opportunities.map((opp, index) => (
                                <div key={index} className="mb-3 p-2" style={{ background: '#f8f9fa', borderRadius: 6 }}>
                                    <strong>{opp.opportunity}</strong>
                                    <p className="mb-1">{opp.rationale}</p>
                                    <span className={`badge bg-${opp.feasibility === 'High' ? 'success' : opp.feasibility === 'Medium' ? 'warning' : 'secondary'}`}>{opp.feasibility} Feasibility</span>
                                </div>
                            ))}
                        </div>
                    </Card.Body>
                </Card>
            )}

            
        </Container>
    );
};

export default Analysis; 