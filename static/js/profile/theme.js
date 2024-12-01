// static/js/profile/theme.js

import { getCsrfToken } from '../utils/csrf.js';

class ThemeManager {
    constructor() {
        this.select = document.getElementById('themeSelect');
        this.select.addEventListener('change', (e) => this.handleThemeChange(e.target.value));
    }

    async handleThemeChange(theme) {
        try {
            const response = await fetch('/api/preferences/theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ theme })
            });

            const data = await response.json();

            if (data.status === 'success') {
                document.documentElement.classList.remove('light', 'dark');
                document.documentElement.classList.add(theme);
                window.notifications.show(data.message, 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Theme update error:', error);
            window.notifications.show(error.message || 'Failed to update theme', 'error');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
});