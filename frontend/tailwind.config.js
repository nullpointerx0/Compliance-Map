/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#090D16',
        darkCard: '#131926',
        darkBorder: '#1E293B',
        brandPrimary: '#10B981', // green for compliant
        brandDanger: '#EF4444',  // red for anomaly
        brandWarning: '#F59E0B', // yellow for expired/warning
        brandAmbiguous: '#8B5CF6', // purple or grey
      },
    },
  },
  plugins: [],
}
