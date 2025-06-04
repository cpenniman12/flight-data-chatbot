// API configuration based on environment
const config = {
  // For production (GitHub Pages), we'll use a deployed backend
  // For development, use localhost
  API_BASE_URL: import.meta.env.PROD 
    ? 'https://your-backend-url.herokuapp.com' // You'll need to replace this with actual backend URL
    : 'http://localhost:5001'
}

export default config
