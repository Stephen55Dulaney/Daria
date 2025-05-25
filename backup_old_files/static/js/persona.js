document.addEventListener('DOMContentLoaded', function() {
    const projectSelect = document.getElementById('projectSelect');
    const interviewSelect = document.getElementById('interviewSelect');
    const generateBtn = document.getElementById('generateBtn');
    const loadingSection = document.getElementById('loadingSection');
    const generatedPersona = document.getElementById('generatedPersona');
    const personaContent = document.getElementById('personaContent');

    // Update interviews when project changes
    projectSelect.addEventListener('change', async function() {
        const projectId = this.value;
        if (!projectId) {
            interviewSelect.innerHTML = '<option value="">No interviews available</option>';
            return;
        }

        try {
            const response = await fetch(`/api/projects/${projectId}/interviews`);
            if (!response.ok) {
                throw new Error('Failed to fetch interviews');
            }
            
            const interviews = await response.json();
            
            if (Array.isArray(interviews) && interviews.length > 0) {
                interviewSelect.innerHTML = interviews
                    .map(i => `<option value="${i.id}">${i.title} - ${i.interview_type} (${i.date})</option>`)
                    .join('');
            } else {
                interviewSelect.innerHTML = '<option value="">No interviews available</option>';
            }
        } catch (error) {
            console.error('Error fetching interviews:', error);
            interviewSelect.innerHTML = '<option value="">Error loading interviews</option>';
        }
    });

    // Handle generate button click
    generateBtn.addEventListener('click', async function() {
        const projectId = projectSelect.value;
        const selectedInterviews = Array.from(interviewSelect.selectedOptions).map(opt => opt.value);
        const model = document.getElementById('modelSelect').value;

        if (!projectId || selectedInterviews.length === 0) {
            alert('Please select a project and at least one interview');
            return;
        }

        // Show loading state
        loadingSection.classList.remove('d-none');
        generatedPersona.classList.add('d-none');
        generateBtn.disabled = true;

        try {
            const response = await fetch('/generate_persona', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    interviews: selectedInterviews,
                    project_name: projectId,
                    model: model,
                    selected_elements: []
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate persona');
            }

            const result = await response.json();
            
            if (result.persona) {
                personaContent.innerHTML = result.persona;
                generatedPersona.classList.remove('d-none');
            } else {
                throw new Error(result.error || 'Failed to generate persona');
            }
        } catch (error) {
            console.error('Error:', error);
            alert(error.message || 'An error occurred while generating the persona');
        } finally {
            loadingSection.classList.add('d-none');
            generateBtn.disabled = false;
        }
    });
}); 