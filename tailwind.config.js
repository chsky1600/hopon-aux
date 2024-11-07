/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/src/js/**/*.js',
    './static/src/css/**/*.css', 
  ],
  theme: {
    extend: {
      colors: {
        darkBlue: '#070F2B',
        purple: '#1B1A55',
        lightPurple: '#535C91',
        softPurple: '#9290C3',
      },
    },
  },
  plugins: [],
}
