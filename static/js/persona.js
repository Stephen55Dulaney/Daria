class PersonaManager {
    constructor(projectName) {
        this.projectName = projectName;
        this.personas = [];
        this.currentPersona = null;
        this.selectedInterviews = new Set();
        
        // Initialize event listeners
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Add persona tab
        document.getElementById('addPersonaTab').addEventListener('click', () => {
            this.createNewPersona();
        });

        // Chat functionality
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });

        document.getElementById('sendMessage').addEventListener('click', () => {
            this.sendChatMessage();
        });

        // File upload handlers
        document.getElementById('uploadImage').addEventListener('click', () => {
            this.handleImageUpload();
        });

        document.getElementById('uploadFile').addEventListener('click', () => {
            this.handleFileUpload();
        });

        // Make content editable
        this.makeContentEditable();
    }

    async createNewPersona() {
        const name = prompt('Enter persona name (e.g., "Janet - The Family Planner"):');
        if (!name) return;

        // Create new persona object
        const persona = {
            id: Date.now(),
            name: name,
            image: '/static/default-avatar.png',
            quote: '[Click to edit quote]',
            demographicProfile: {
                personal: '',
                professional: '',
                environment: '',
                psychographics: ''
            },
            goalsAndNeeds: ['', '', ''],
            motivations: ['', '', ''],
            frustrations: ['', '', ''],
            everydayActivities: [],
            deviceUsage: {
                desktop: 50,
                mobile: 50,
                socialMedia: 50,
                technicalKnowHow: 50
            },
            notableQuotes: []
        };

        // Add to personas array
        this.personas.push(persona);
        
        // Create and add tab
        this.addPersonaTab(persona);
        
        // Switch to new persona
        this.switchPersona(persona.id);

        // Generate initial content if we have selected interviews
        if (this.selectedInterviews.size > 0) {
            await this.generatePersonaContent();
        }
    }

    addPersonaTab(persona) {
        const tabsContainer = document.getElementById('personaTabs');
        const tab = document.createElement('div');
        tab.className = 'px-4 py-2 cursor-pointer hover:bg-gray-100';
        tab.textContent = persona.name;
        tab.dataset.personaId = persona.id;
        tab.addEventListener('click', () => this.switchPersona(persona.id));
        tabsContainer.appendChild(tab);
    }

    async switchPersona(personaId) {
        this.currentPersona = this.personas.find(p => p.id === personaId);
        if (!this.currentPersona) return;

        // Update UI with persona data
        this.updatePersonaUI();
        
        // Update active tab
        document.querySelectorAll('#personaTabs > div').forEach(tab => {
            tab.classList.toggle('bg-blue-500', tab.dataset.personaId === String(personaId));
            tab.classList.toggle('text-white', tab.dataset.personaId === String(personaId));
        });
    }

    updatePersonaUI() {
        if (!this.currentPersona) return;

        // Update header
        document.getElementById('personaImage').src = this.currentPersona.image;
        document.getElementById('personaName').textContent = this.currentPersona.name;
        document.getElementById('personaQuote').textContent = this.currentPersona.quote;

        // Update demographic profile
        const demographicProfile = document.getElementById('demographicProfile');
        demographicProfile.innerHTML = `
            <p>Personal Background: ${this.currentPersona.demographicProfile.personal}</p>
            <p>Professional Background: ${this.currentPersona.demographicProfile.professional}</p>
            <p>User Environment: ${this.currentPersona.demographicProfile.environment}</p>
            <p>Psychographics: ${this.currentPersona.demographicProfile.psychographics}</p>
        `;

        // Update goals and needs
        document.getElementById('goalsAndNeeds').innerHTML = this.currentPersona.goalsAndNeeds
            .map(goal => `<li>${goal}</li>`).join('');

        // Update motivations
        document.getElementById('motivations').innerHTML = this.currentPersona.motivations
            .map(motivation => `<li>${motivation}</li>`).join('');

        // Update frustrations
        document.getElementById('frustrations').innerHTML = this.currentPersona.frustrations
            .map(frustration => `<li>${frustration}</li>`).join('');

        // Update everyday activities
        document.getElementById('everydayActivities').innerHTML = this.currentPersona.everydayActivities
            .map(activity => `<li>${activity}</li>`).join('');

        // Update device usage sliders
        Object.entries(this.currentPersona.deviceUsage).forEach(([device, value]) => {
            const slider = document.querySelector(`[data-device="${device}"]`);
            if (slider) {
                slider.value = value;
                slider.previousElementSibling.querySelector('.value').textContent = `${value}%`;
            }
        });

        // Update notable quotes
        document.getElementById('notableQuotes').innerHTML = this.currentPersona.notableQuotes
            .map(quote => `<div class="italic">"${quote}"</div>`).join('');

        // Update line numbers
        this.updateLineNumbers();
    }

    async generatePersonaContent() {
        const selectedIds = Array.from(this.selectedInterviews);
        if (selectedIds.length === 0) {
            alert('Please select at least one interview transcript');
            return;
        }

        try {
            const response = await fetch('/generate_persona', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    interview_ids: selectedIds,
                    project_name: this.projectName
                })
            });

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

            this.populateFromAnalysis(data);
        } catch (error) {
            console.error('Error generating persona:', error);
            alert('Error generating persona content. Please try again.');
        }
    }

    populateFromAnalysis(analysis) {
        // Set name and quote
        document.getElementById('personaName').textContent = analysis.name || 'Name: [Click to Edit]';
        document.getElementById('personaQuote').textContent = analysis.keyInsights?.[0] || '[Click to Edit Quote]';

        // Populate demographic profile
        const demographicProfile = document.getElementById('demographicProfile');
        if (analysis.demographics) {
            demographicProfile.innerHTML = `<p class="content-editable">${analysis.demographics}</p>`;
        }

        // Populate goals and needs
        const goalsAndNeeds = document.getElementById('goalsAndNeeds');
        if (analysis.goals) {
            goalsAndNeeds.innerHTML = `<li class="content-editable">${analysis.goals}</li>`;
        }

        // Populate motivations
        const motivations = document.getElementById('motivations');
        if (analysis.behaviors) {
            motivations.innerHTML = `<li class="content-editable">${analysis.behaviors}</li>`;
        }

        // Populate frustrations
        const frustrations = document.getElementById('frustrations');
        if (analysis.challenges) {
            frustrations.innerHTML = `<li class="content-editable">${analysis.challenges}</li>`;
        }

        // Populate everyday activities
        const everydayActivities = document.getElementById('everydayActivities');
        if (analysis.preferences) {
            everydayActivities.innerHTML = `<li class="content-editable">${analysis.preferences}</li>`;
        }

        // Populate notable quotes
        const notableQuotes = document.getElementById('notableQuotes');
        if (analysis.keyInsights) {
            notableQuotes.innerHTML = analysis.keyInsights
                .map(quote => `<p class="content-editable italic">"${quote}"</p>`)
                .join('');
        }

        // Make all content editable
        this.makeContentEditable();
        
        // Update line numbers
        this.updateLineNumbers();
    }

    makeContentEditable() {
        document.querySelectorAll('.content-editable').forEach(element => {
            element.addEventListener('click', () => {
                const newValue = prompt('Edit content:', element.textContent);
                if (newValue !== null) {
                    element.textContent = newValue;
                    this.savePersonaData();
                }
            });
        });
    }

    updateLineNumbers() {
        const content = document.getElementById('personaContent');
        const lineNumbers = document.getElementById('lineNumbers');
        lineNumbers.innerHTML = '';
        
        const elements = content.querySelectorAll('*:not(.slider-container):not(.slider-label):not(input)');
        elements.forEach(() => {
            const span = document.createElement('span');
            span.className = 'line-number';
            lineNumbers.appendChild(span);
        });
    }

    async savePersonaData() {
        const personaData = {
            name: document.getElementById('personaName').textContent,
            quote: document.getElementById('personaQuote').textContent,
            demographics: document.getElementById('demographicProfile').textContent,
            goals: document.getElementById('goalsAndNeeds').textContent,
            behaviors: document.getElementById('motivations').textContent,
            challenges: document.getElementById('frustrations').textContent,
            preferences: document.getElementById('everydayActivities').textContent,
            keyInsights: Array.from(document.getElementById('notableQuotes').children).map(p => p.textContent)
        };

        fetch('/save_persona', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_name: this.projectName,
                persona_data: personaData
            })
        }).catch(error => console.error('Error saving persona:', error));
    }

    async sendChatMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message) return;

        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML += `
            <div class="flex justify-end">
                <div class="bg-blue-100 rounded-lg p-2 max-w-3/4">
                    ${message}
                </div>
            </div>
        `;

        input.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            chatMessages.innerHTML += `
                <div class="flex justify-start">
                    <div class="bg-gray-100 rounded-lg p-2 max-w-3/4">
                        ${data.response}
                    </div>
                </div>
            `;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    handleImageUpload() {
        // Implement image upload functionality
    }

    handleFileUpload() {
        // Implement file upload functionality
    }
}

// Initialize the persona manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const projectName = document.querySelector('h1').textContent.split('Create Personas for ')[1];
    window.personaManager = new PersonaManager(projectName);
}); 