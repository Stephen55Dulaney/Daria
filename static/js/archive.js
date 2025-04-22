document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('#searchInput');
    const searchButton = document.querySelector('#searchButton');
    const interviewGrid = document.querySelector('.interview-grid');
    let searchTimeout;

    // Debounced search function
    const performSearch = (query) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            try {
                // Show loading state
                interviewGrid.innerHTML = `
                    <div class="loading">
                        <p>Searching interviews...</p>
                    </div>
                `;

                // Make the search request
                const response = await fetch(`/search_interviews?q=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error('Search failed');
                
                const data = await response.json();
                if (!data.success) throw new Error(data.error || 'Search failed');
                
                updateInterviewGrid(data.interviews || []);
            } catch (error) {
                console.error('Search error:', error);
                showNotification('Search failed. Please try again.', 'error');
                
                // Show error state in grid
                interviewGrid.innerHTML = `
                    <div class="no-results">
                        <p>An error occurred while searching. Please try again.</p>
                    </div>
                `;
            }
        }, 300);
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
        const date = interview.created_at ? new Date(interview.created_at).toLocaleDateString() : 'No date';
        const previewText = interview.preview || interview.content_preview || 'No preview available';
        const tags = interview.tags || [];
        const status = interview.status || 'Draft';
        const type = interview.type || 'Interview';

        return `
            <div class="interview-card" data-interview-id="${interview.id}">
                <div class="card-header">
                    <span class="type-badge ${type.toLowerCase()}">${type}</span>
                    <span class="status-badge ${status.toLowerCase()}">${status}</span>
                </div>
                <div class="card-body">
                    <h3 class="interview-title">${interview.title || 'Untitled Interview'}</h3>
                    <div class="interview-meta">
                        <span class="participant">${interview.participant_name || 'Anonymous'}</span>
                        <span class="date">${date}</span>
                    </div>
                    <p class="preview-text">${previewText}</p>
                    <div class="project-info">
                        <span class="project-name">${interview.project_name || 'Unassigned'}</span>
                        ${interview.created_by ? `<span class="author">by ${interview.created_by}</span>` : ''}
                    </div>
                    ${tags.length ? `
                        <div class="tags-container">
                            ${tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
                <div class="card-footer">
                    <a href="/transcript/${interview.id}" class="btn-icon" title="View Transcript">
                        <i class="fas fa-file-alt"></i>
                    </a>
                    <a href="/analysis/${interview.id}" class="btn-icon" title="View Analysis">
                        <i class="fas fa-chart-bar"></i>
                    </a>
                    <a href="/metadata/${interview.id}" class="btn-icon" title="View Metadata">
                        <i class="fas fa-info-circle"></i>
                    </a>
                    <button class="btn-icon copy-link" data-interview-id="${interview.id}" title="Copy Link">
                        <i class="fas fa-link"></i>
                    </button>
                    <button class="btn-icon favorite" data-interview-id="${interview.id}" title="Favorite">
                        <i class="fas fa-star"></i>
                    </button>
                </div>
            </div>
        `;
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

        // Favorite buttons
        document.querySelectorAll('.favorite').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.currentTarget.dataset.interviewId;
                const icon = e.currentTarget.querySelector('i');
                
                try {
                    const response = await fetch(`/api/interviews/${id}/favorite`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (!response.ok) throw new Error('Failed to toggle favorite');
                    
                    const { isFavorite } = await response.json();
                    icon.className = isFavorite ? 'fas fa-star' : 'far fa-star';
                    showNotification(
                        isFavorite ? 'Added to favorites' : 'Removed from favorites',
                        'success'
                    );
                } catch (error) {
                    console.error('Favorite toggle error:', error);
                    showNotification('Failed to update favorite status', 'error');
                }
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
    searchInput?.addEventListener('input', (e) => performSearch(e.target.value));
    searchButton?.addEventListener('click', () => performSearch(searchInput.value));

    // Initial setup
    attachCardEventListeners();
}); 