import React, { useState } from 'react';
import { Card, Button, Spinner, Alert } from 'react-bootstrap';

const AnalysisCard = ({ sessionId }) => {
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const analyzeSession = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/research_session/${sessionId}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to analyze session');
            }
            
            setAnalysis(data.analysis);
        } catch (err) {
            setError(err.message);
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
        a.download = `analysis_${sessionId}_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <Card className="mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Research Analysis</h5>
                <div>
                    <Button 
                        variant="primary" 
                        onClick={analyzeSession} 
                        disabled={loading}
                        className="me-2"
                    >
                        {loading ? (
                            <>
                                <Spinner as="span" animation="border" size="sm" className="me-2" />
                                Analyzing...
                            </>
                        ) : 'Analyze Session'}
                    </Button>
                    {analysis && (
                        <Button 
                            variant="success" 
                            onClick={downloadAnalysis}
                        >
                            Download Analysis
                        </Button>
                    )}
                </div>
            </Card.Header>
            <Card.Body>
                {error && (
                    <Alert variant="danger">
                        {error}
                    </Alert>
                )}
                
                {analysis && (
                    <div>
                        <h6>Summary</h6>
                        <p>{analysis.summary}</p>
                        
                        <h6 className="mt-4">Key Findings</h6>
                        {analysis.key_findings.map((finding, index) => (
                            <div key={index} className="mb-3">
                                <strong>{finding.insight}</strong>
                                <p className="mb-1">{finding.importance}</p>
                                {finding.supporting_quotes.map((quote, qIndex) => (
                                    <blockquote key={qIndex} className="text-muted small">
                                        "{quote}"
                                    </blockquote>
                                ))}
                            </div>
                        ))}
                        
                        <h6 className="mt-4">User Needs</h6>
                        {analysis.user_needs.map((need, index) => (
                            <div key={index} className="mb-3">
                                <strong>{need.need}</strong>
                                <p className="mb-1">{need.context}</p>
                                <span className={`badge bg-${need.priority === 'High' ? 'danger' : need.priority === 'Medium' ? 'warning' : 'info'}`}>
                                    {need.priority} Priority
                                </span>
                            </div>
                        ))}
                        
                        <h6 className="mt-4">Pain Points</h6>
                        {analysis.pain_points.map((point, index) => (
                            <div key={index} className="mb-3">
                                <strong>{point.issue}</strong>
                                <p className="mb-1">{point.impact}</p>
                                <span className="badge bg-secondary">
                                    {point.frequency}
                                </span>
                            </div>
                        ))}
                        
                        <h6 className="mt-4">Opportunities</h6>
                        {analysis.opportunities.map((opp, index) => (
                            <div key={index} className="mb-3">
                                <strong>{opp.opportunity}</strong>
                                <p className="mb-1">{opp.rationale}</p>
                                <span className={`badge bg-${opp.feasibility === 'High' ? 'success' : opp.feasibility === 'Medium' ? 'warning' : 'secondary'}`}>
                                    {opp.feasibility} Feasibility
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

export default AnalysisCard; 