// static/js/profile/auto-sync.js

import { getCsrfToken } from '../utils/csrf.js';

class AutoSyncModal {
    constructor() {
        this.modal = document.getElementById('autoSyncModal');
        this.form = document.getElementById('autoSyncForm');
        this.enabledToggle = document.getElementById('autoSyncEnabled');
        this.intervalSelect = document.getElementById('syncInterval');
        this.configureBtn = document.getElementById('configureAutoSyncBtn');
        this.setupToggle();

        this.initializeEventListeners();
    }

    setupToggle() {
        const checkbox = document.getElementById('autoSyncEnabled');
        const span = checkbox.nextElementSibling;
        const intervalSelect = document.getElementById('syncInterval');
        
        // Set initial state based on checkbox's checked state from template
        span.dataset.checked = checkbox.checked;
        intervalSelect.disabled = !checkbox.checked;
    
        checkbox.addEventListener('change', () => {
            span.dataset.checked = checkbox.checked;
            intervalSelect.disabled = !checkbox.checked;
        });
    }

    initializeEventListeners() {
        // Modal controls
        this.configureBtn.addEventListener('click', () => this.open());
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });

        // Form handling
        this.enabledToggle.addEventListener('change', (e) => {
            this.intervalSelect.disabled = !e.target.checked;
        });

        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    open() {
        this.modal.classList.remove('hidden');
    }

    close() {
        this.modal.classList.add('hidden');
    }

    async handleSubmit(e) {
        e.preventDefault();
        const submitButton = this.form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        try {
            submitButton.disabled = true;
            submitButton.textContent = 'Saving...';
            const formData = {
                auto_sync_enabled: this.enabledToggle.checked,
                sync_interval: this.intervalSelect.value
            };
            const response = await fetch('/api/settings/auto-sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(formData)
            });
            const data = await response.json();
            if (response.ok) {  // Check response.ok instead of data.status
                window.notifications.show(data.message, 'success');
                // Pass the data.data object to updateNextSyncTime
                if (data.data) {
                    this.updateNextSyncTime(data.data);
                }
                this.close();
            } else {
                throw new Error(data.message || 'Failed to update settings');
            }
        } catch (error) {
            console.error('Settings update error:', error);
            window.notifications.show(error.message || 'Failed to update auto-sync settings', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    updateNextSyncTime(data) {
        const nextSyncElement = document.getElementById('nextSyncTime');
        if (!nextSyncElement) return;  // Guard against missing element

        if (data && data.next_sync) {  // Check if data and next_sync exist
            const nextSyncDate = new Date(data.next_sync);
            nextSyncElement.textContent = `Next sync scheduled for ${nextSyncDate.toLocaleString()}`;
            nextSyncElement.classList.remove('hidden');
        } else {
            nextSyncElement.classList.add('hidden');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AutoSyncModal();
});

let autoSyncModal;  // Declare a variable to hold the instance

document.addEventListener('DOMContentLoaded', () => {
    autoSyncModal = new AutoSyncModal();  // Store the instance
    // Expose the close method globally
    window.closeAutoSyncModal = () => autoSyncModal.close();
});