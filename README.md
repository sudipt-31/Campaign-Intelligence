# Campaign Intelligence Agent

An intelligent multi-agent system designed to analyze marketing campaigns, identify trends, and provide strategic recommendations using LangGraph and React.

## Project Structure

- `campaign_intelligence_v2/`: FastAPI Backend powered by LangGraph.
- `frontend/`: React + Vite + Tailwind CSS Frontend.

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd campaign_intelligence_v2
   ```
2. Create and configure your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY and other credentials
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## Features

- **Multi-Agent Orchestration**: Uses LangGraph for complex agent workflows.
- **Data Quality Gate**: Automated checks to ensure data integrity before synthesis.
- **Critic Loop**: Intelligent critique and revision of strategic recommendations.
- **Real-time Updates**: Server-Sent Events (SSE) for streaming agent progress.
- **Modern UI**: Responsive dashboard built with React and Tailwind CSS.

## License

MIT
