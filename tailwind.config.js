/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      './templates/**/*.html',
      './core/templates/**/*.html',
      './plex_auth/templates/**/*.html',
      './media_manager/templates/**/*.html',
      './static/js/**/*.js',
    ],
    theme: {
      extend: {
        colors: {
          'plex-yellow': '#e5a00d',
          'plex-dark': '#1f1f1f',
        },
      },
    },
    plugins: [
      require('@tailwindcss/forms'),
      require('@tailwindcss/typography'),
      require('@tailwindcss/aspect-ratio'),
    ],
  }