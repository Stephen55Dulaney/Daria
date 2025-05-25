// Analysis module for handling UX insights and visualization
class AnalysisManager {
    constructor() {
        this.currentAnalysis = null;
        this.currentProjectName = null;
    }

    async analyzeInterview(interviewData) {
        try {
            const response = await fetch('/api/analysis/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(interviewData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to analyze interview');
            }

            this.currentAnalysis = await response.json();
            this.currentProjectName = interviewData.project_name;
            
            // Update UI with analysis results
            this.displayInsights();
            this.displayAffinityDiagram();
            
            return this.currentAnalysis;

        } catch (error) {
            console.error('Analysis error:', error);
            throw error;
        }
    }

    async getInsights(interviewId) {
        try {
            const response = await fetch(`/api/analysis/insights/${interviewId}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch insights');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching insights:', error);
            throw error;
        }
    }

    async getAffinityDiagram(projectName) {
        try {
            const response = await fetch(`/api/analysis/affinity-diagram/${projectName}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch affinity diagram');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching affinity diagram:', error);
            throw error;
        }
    }

    displayInsights() {
        if (!this.currentAnalysis || !this.currentAnalysis.insights) {
            console.warn('No insights available to display');
            return;
        }

        const insightsContainer = document.getElementById('insights-container');
        if (!insightsContainer) {
            console.error('Insights container not found');
            return;
        }

        insightsContainer.innerHTML = '';
        
        // Group insights by type
        const groupedInsights = {};
        this.currentAnalysis.insights.forEach(insight => {
            if (!groupedInsights[insight.type]) {
                groupedInsights[insight.type] = [];
            }
            groupedInsights[insight.type].push(insight);
        });

        // Create sections for each insight type
        Object.entries(groupedInsights).forEach(([type, insights]) => {
            const section = document.createElement('div');
            section.className = 'insight-section';
            
            const header = document.createElement('h3');
            header.textContent = type.charAt(0).toUpperCase() + type.slice(1);
            section.appendChild(header);

            insights.forEach(insight => {
                const card = document.createElement('div');
                card.className = 'insight-card';
                card.innerHTML = `
                    <h4>${insight.content}</h4>
                    <div class="confidence-meter">
                        Confidence: ${Math.round(insight.confidence * 100)}%
                    </div>
                    <div class="supporting-quotes">
                        <h5>Supporting Quotes:</h5>
                        <ul>
                            ${insight.supporting_quotes.map(quote => `<li>${quote}</li>`).join('')}
                        </ul>
                    </div>
                `;
                section.appendChild(card);
            });

            insightsContainer.appendChild(section);
        });
    }

    displayAffinityDiagram() {
        if (!this.currentAnalysis || !this.currentAnalysis.affinity_diagram) {
            console.warn('No affinity diagram available to display');
            return;
        }

        const container = document.getElementById('affinity-diagram-container');
        if (!container) {
            console.error('Affinity diagram container not found');
            return;
        }

        // Clear existing content
        container.innerHTML = '';

        // Create tree layout
        const diagram = document.createElement('div');
        diagram.className = 'affinity-diagram';
        
        const createNode = (node) => {
            const nodeElement = document.createElement('div');
            nodeElement.className = 'affinity-node';
            
            const header = document.createElement('div');
            header.className = 'node-header';
            header.textContent = node.name;
            nodeElement.appendChild(header);

            if (node.children) {
                const childrenContainer = document.createElement('div');
                childrenContainer.className = 'node-children';
                node.children.forEach(child => {
                    childrenContainer.appendChild(createNode(child));
                });
                nodeElement.appendChild(childrenContainer);
            }

            if (node.quotes) {
                const quotesContainer = document.createElement('div');
                quotesContainer.className = 'node-quotes';
                node.quotes.forEach(quote => {
                    const quoteElement = document.createElement('div');
                    quoteElement.className = 'quote';
                    quoteElement.textContent = quote;
                    quotesContainer.appendChild(quoteElement);
                });
                nodeElement.appendChild(quotesContainer);
            }

            return nodeElement;
        };

        diagram.appendChild(createNode(this.currentAnalysis.affinity_diagram));
        container.appendChild(diagram);
    }
}

// Export for use in other modules
export const analysisManager = new AnalysisManager(); 