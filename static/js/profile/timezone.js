// static/js/profile/timezone.js

import { getCsrfToken } from '../utils/csrf.js';

class TimezoneManager {
    constructor() {
        this.select = document.getElementById('timezoneSelect');
        if (this.select) {
            this.select.addEventListener('change', () => this.handleChange());
        }
    }

    async handleChange() {
        try {
            const response = await fetch('/api/settings/timezone/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    timezone: this.select.value
                })
            });

            const data = await response.json();
            if (response.ok) {
                window.notifications.show('Timezone updated successfully', 'success');
                // Reload to show updated times
                window.location.reload();
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Timezone update error:', error);
            window.notifications.show(error.message || 'Failed to update timezone', 'error');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new TimezoneManager();
});