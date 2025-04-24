document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('#searchInput');
    const searchButton = document.querySelector('#searchButton');
    const searchTypeSelect = document.querySelector('#searchType');
    const interviewGrid = document.querySelector('.interview-grid');
    let searchTimeout;

    // Initialize Bootstrap modal
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    let interviewToDelete = null;

    // Handle delete button clicks
    document.querySelectorAll('.delete-interview').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            interviewToDelete = this.dataset.interviewId;
            deleteModal.show();
        });
    });

    // Handle confirm delete
    document.getElementById('confirmDelete').addEventListener('click', function() {
        if (!interviewToDelete) return;

        fetch(`/delete_interview/${interviewToDelete}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Remove the interview card from the UI
                const card = document.querySelector(`.interview-card[data-interview-id="${interviewToDelete}"]`);
                if (card) {
                    card.remove();
                }
                // Show success message
                showNotification('Interview deleted successfully', 'success');
            } else {
                throw new Error(data.message || 'Failed to delete interview');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to delete interview: ' + error.message, 'error');
        })
        .finally(() => {
            deleteModal.hide();
            interviewToDelete = null;
        });
    });

    // Debounced search function
    const performSearch = async (query, searchType = 'exact') => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            try {
                // Show loading state
                interviewGrid.innerHTML = `
                    <div class="loading">
                        <p>Searching interviews...</p>
                    </div>
                `;

                // Make the search request to the appropriate endpoint
                const endpoint = searchType === 'exact' ? '/api/search/exact' : '/api/search/fuzzy';
                const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
                
                if (!response.ok) throw new Error('Search failed');
                
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error(data.error || 'Search failed');
                }
                
                updateInterviewGrid(data.interviews);
                
            } catch (error) {
                console.error('Search error:', error);
                interviewGrid.innerHTML = `
                    <div class="alert alert-danger">
                        Error performing search: ${error.message}
                    </div>
                `;
            }
        }, 300); // 300ms debounce delay
    };

    // Update interview grid with search results
    const updateInterviewGrid = (interviews) => {
        if (!interviews.length) {
            interviewGrid.innerHTML = `
                <div class="no-results">
                    <p>No interviews found matching your search.</p>
                </div>
            `;
            return;
        }

        interviewGrid.innerHTML = interviews.map(interview => createInterviewCard(interview)).join('');
        attachCardEventListeners();
    };

    // Create HTML for a single interview card
    const createInterviewCard = (interview) => {
        // Add null checks and default values
        const type = (interview.type || 'Interview').toLowerCase();
        const status = (interview.status || 'Draft').toLowerCase();
        const displayName = interview.transcript_name || 'Untitled Interview';
        const projectName = interview.project_name || 'Unassigned';
        const date = interview.created_at ? 
            new Date(interview.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            }) : 'No date';
            
        // Create badges for emotions with null check
        const emotionBadges = (interview.emotions || []).map(emotion => `
            <span class="emotion-badge" title="${emotion.count || 0} occurrences, avg intensity: ${emotion.avg_intensity || 0}">
                ${getEmotionIcon(emotion.name || '')} ${emotion.name || ''}
            </span>
        `).join('');

        // Create badges for themes with null check
        const themeBadges = (interview.themes || []).map(theme => `
            <span class="theme-badge">${theme || ''}</span>
        `).join('');

        // Create badges for insights with null check
        const insightBadges = (interview.insights || []).map(insight => `
            <span class="insight-badge">${insight || ''}</span>
        `).join('');

        return `
            <div class="interview-card" data-interview-id="${interview.id || ''}">
                <div class="card-header">
                    <span class="type-badge ${type}">${interview.type || 'Interview'}</span>
                    <span class="status-badge ${status}">${interview.status || 'Draft'}</span>
                </div>
                
                <div class="card-body">
                    <div class="participant-info">
                        <h3 class="participant-name">${displayName}</h3>
                        <span class="project-name">${projectName}</span>
                    </div>
                    
                    <div class="interview-meta">
                        <span class="date">${date}</span>
                    </div>
                    
                    ${emotionBadges ? `
                        <div class="emotion-badges">
                            ${emotionBadges}
                        </div>
                    ` : ''}
                    
                    <p class="preview-text">${interview.preview || 'No preview available'}</p>
                    
                    ${themeBadges ? `
                        <div class="theme-badges">
                            ${themeBadges}
                        </div>
                    ` : ''}
                    
                    ${insightBadges ? `
                        <div class="insight-badges">
                            ${insightBadges}
                        </div>
                    ` : ''}
                </div>
                
                <div class="card-footer">
                    <a href="/transcript/${interview.id || ''}" class="btn btn-icon" title="View Transcript">
                        <i class="fas fa-file-alt"></i>
                    </a>
                    <a href="/analysis/${interview.id || ''}" class="btn btn-icon" title="View Analysis">
                        <i class="fas fa-chart-bar"></i>
                    </a>
                    <a href="/demographics/${interview.id || ''}" class="btn btn-icon" title="View Demographics">
                        <i class="fas fa-user-circle"></i>
                    </a>
                    <button class="btn btn-icon copy-link" data-interview-id="${interview.id || ''}" title="Copy Link">
                        <i class="fas fa-link"></i>
                    </button>
                    <button class="btn btn-icon delete-interview" data-interview-id="${interview.id || ''}" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    };

    // Helper function to get emotion icon
    const getEmotionIcon = (emotion) => {
        const emotionIcons = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'neutral': '😐',
            'excited': '🤩',
            'frustrated': '😤',
            'confused': '😕',
            'anxious': '😰',
            'satisfied': '😌',
            'disappointed': '😞'
        };
        return emotionIcons[emotion.toLowerCase()] || '😐';
    };

    // Attach event listeners to card buttons
    const attachCardEventListeners = () => {
        // Copy link buttons
        document.querySelectorAll('.copy-link').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.currentTarget.dataset.interviewId;
                const url = `${window.location.origin}/transcript/${id}`;
                
                try {
                    await navigator.clipboard.writeText(url);
                    showNotification('Link copied to clipboard!', 'success');
                } catch (err) {
                    console.error('Failed to copy:', err);
                    showNotification('Failed to copy link', 'error');
                }
            });
        });

        // Delete buttons
        document.querySelectorAll('.delete-interview').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.currentTarget.dataset.interviewId;
                interviewToDelete = id;
                deleteModal.show();
            });
        });
    };

    // Show notification
    const showNotification = (message, type = 'info') => {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    };

    // Event listeners
    searchInput?.addEventListener('input', (e) => {
        const searchType = searchTypeSelect?.value || 'exact';
        performSearch(e.target.value, searchType);
    });

    searchTypeSelect?.addEventListener('change', () => {
        if (searchInput?.value) {
            performSearch(searchInput.value, searchTypeSelect.value);
        }
    });

    // Initial setup
    attachCardEventListeners();
}); 