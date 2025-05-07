# Bible App Backend

This is the backend for the Bible App, providing API services for Bible verses, user notes, and AI-powered insights.

## Setup

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```
JWT_SECRET=your-jwt-secret
ANTHROPIC_API_KEY=your-anthropic-api-key
PORT=5001
```

### Anthropic API Key for AI Insights

To use the AI Insights feature:

1. Create an account at [Anthropic](https://www.anthropic.com/)
2. Generate an API key from your dashboard
3. Add the API key to your `.env` file as `ANTHROPIC_API_KEY`

The application uses Claude 3.7 Sonnet to generate insights about Bible passages based on user preferences and notes.

### Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Start the server:
   ```
   python app.py
   ```

## API Routes

- `/api/bible/*` - Bible-related endpoints
- `/api/auth/*` - Authentication endpoints
- `/api/notes/*` - User notes endpoints
- `/api/friends/*` - Friend-related endpoints

## Features

- Bible verse access
- User authentication and authorization
- Note-taking capabilities
- AI-powered insights using Claude 3.7 Sonnet
- Friend connections and note sharing 