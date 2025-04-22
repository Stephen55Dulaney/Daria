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
        // Get participant name from all possible sources
        const participantName = interview.transcript_name || // Try transcript_name first
                               interview.metadata?.participant?.name ||
                               interview.participant_name ||
                               'Anonymous';
                               
        // Calculate interview duration
        const durationMinutes = interview.metadata?.interview_details?.duration || 
                               interview.duration || 
                               calculateDurationFromChunks(interview.chunks);
                               
        const durationText = durationMinutes ? `${durationMinutes} min` : '';
        
        // Format date nicely
        const date = interview.created_at ? 
            new Date(interview.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            }) : 'No date';
            
        const previewText = interview.preview || interview.content_preview || 'No preview available';
        const type = interview.type || 'Interview';
        const status = interview.status || 'Draft';
        
        // Construct title using participant name
        const title = `Interview with ${participantName} - ${date}`;
        
        return `
            <div class="interview-card" data-interview-id="${interview.id}">
                <div class="card-header">
                    <span class="type-badge ${type.toLowerCase()}">${type}</span>
                    <span class="status-badge ${status.toLowerCase()}">${status}</span>
                </div>
                
                <div class="card-body">
                    <h3 class="interview-title">${title}</h3>
                    <div class="interview-meta">
                        <span class="duration">${durationText || 'Duration unknown'}</span>
                    </div>
                    
                    <p class="preview-text">${previewText}</p>
                    
                    <div class="card-actions">
                        <button class="action-btn view-btn" data-id="${interview.id}">
                            <i class="fas fa-eye"></i> View
                        </button>
                        <button class="action-btn copy-btn" data-id="${interview.id}">
                            <i class="fas fa-link"></i> Copy Link
                        </button>
                        <button class="action-btn favorite-btn" data-id="${interview.id}">
                            <i class="far fa-star"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    };

    // Helper function to calculate duration from chunks
    const calculateDurationFromChunks = (chunks) => {
        if (!chunks || !Array.isArray(chunks)) return null;
        
        // Assuming chunks have timestamps or we can calculate from content length
        let totalDuration = 0;
        chunks.forEach(chunk => {
            if (chunk.duration) {
                totalDuration += parseFloat(chunk.duration);
            }
        });
        
        return totalDuration > 0 ? Math.round(totalDuration / 60) : null;
    };

    // Attach event listeners to card buttons
    const attachCardEventListeners = () => {
        // Copy link buttons
        document.querySelectorAll('.copy-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.currentTarget.dataset.id;
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
        document.querySelectorAll('.favorite-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                const id = e.currentTarget.dataset.id;
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