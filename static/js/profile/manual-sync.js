// static/js/profile/manual-sync.js

import { getCsrfToken } from '../utils/csrf.js';

class ManualSync {
    constructor() {
        this.button = document.getElementById('syncNowBtn');
        this.quickSyncButton = document.getElementById('quickSyncButton');
        this.buttonText = this.button.querySelector('.sync-button-text');
        this.spinner = this.button.querySelector('.sync-spinner');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.button.addEventListener('click', () => this.handleSync());
        if (this.quickSyncButton) {
            this.quickSyncButton.addEventListener('click', () => this.handleSync());
        }
    }

    async handleSync() {
        this.setLoading(true);

        try {
            const response = await fetch('/api/sync/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                }
            });

            const data = await response.json();

            if (data.status === 'success') {
                window.notifications.show(data.message, 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Sync error:', error);
            window.notifications.show(error.message || 'Failed to start sync', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    setLoading(isLoading) {
        this.button.disabled = isLoading;
        this.buttonText.classList.toggle('hidden', isLoading);
        this.spinner.classList.toggle('hidden', !isLoading);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ManualSync();
});