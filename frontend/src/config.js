// API configuration based on environment
const config = {
  // For production (GitHub Pages), we'll use demo mode initially
  // You can later replace this with your deployed backend URL
  API_BASE_URL: import.meta.env.PROD 
    ? null // Demo mode - no backend needed for initial deployment
    : 'http://localhost:5001',
    
  // Demo mode flag
  DEMO_MODE: import.meta.env.PROD
}

export default config
