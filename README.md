# Oasis Part 2 - Oracle Agent Hub

A full-stack web application that provides a chat interface to interact with Oracle Fusion Cloud AI Agent Studio agents. The application features user authentication, multi-agent routing based on intent classification, and real-time polling for asynchronous agent responses.

## Features

- **User Authentication**: JWT-based authentication with registration, login, and secure token management
- **Intent Classification**: Automatic classification of user queries using Google Gemini AI or regex fallbacks
- **Multi-Agent Routing**: Dynamic routing to appropriate Oracle Fusion agents based on query intent
- **Asynchronous Processing**: Background job processing with real-time status polling
- **Rich UI**: React-based frontend with chat interface, agent badges, and follow-up suggestions
- **Database Integration**: SQLAlchemy ORM with user management, roles, permissions, and audit logging
- **Health Monitoring**: Built-in health check endpoints for backend and frontend status

## Architecture

### Backend (FastAPI)
- RESTful API with async job processing
- Oracle Fusion Cloud integration
- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- SQLAlchemy database models
- Intent classification service

### Frontend (React + Vite)
- Modern React application with TypeScript
- Authentication context and protected routes
- Real-time chat interface with polling
- Responsive design with Tailwind CSS

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Oracle Fusion Cloud account (for agent integration)
- Google Gemini API key (optional, for intent classification)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd oasis-part2
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac

   # Install dependencies
   pip install -r requirements.txt

   # Configure environment variables
   cp Backend/.env.example Backend/.env
   # Edit Backend/.env with your Oracle Fusion and API keys
   ```

3. **Frontend Setup**
   ```bash
   cd Frontend
   npm install
   ```

### Running the Application

1. **Start Backend**
   ```bash
   cd Backend
   uvicorn main:app --reload
   ```
   Backend will be available at `http://127.0.0.1:8000`

2. **Start Frontend**
   ```bash
   cd Frontend
   npm run dev
   ```
   Frontend will be available at `http://127.0.0.1:5173`

### Health Checks

- Backend health: `http://127.0.0.1:8000/api/health`
- Frontend status check: Run `python temp_frontend_check.py`
- Backend status check: Run `python temp_health_check.py`

## API Documentation

Once the backend is running, visit `http://127.0.0.1:8000/docs` for interactive API documentation.

### Key Endpoints

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/chat` - Submit chat query (async)
- `GET /api/chat/{job_id}` - Poll job status

## Testing

Run the provided test scripts to validate functionality:

```bash
# Test basic chat functionality
python Backend/test_chat.py

# Test multiple queries
python Backend/test_queries.py
```

## Configuration

### Environment Variables (Backend/.env)

```env
# Database
DATABASE_URL=sqlite:///./app.db

# Oracle Fusion
FUSION_USER=your_fusion_username
FUSION_PASSWORD=your_fusion_password
FUSION_BASE_URL=https://your-fusion-instance.oraclecloud.com

# AI Services
GEMINI_API_KEY=your_gemini_api_key

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key

# CORS
FRONTEND_URL=http://127.0.0.1:5173
```

## Project Structure

See [README_STRUCTURE.md](README_STRUCTURE.md) for detailed file hierarchy and component descriptions.

## Development

- Backend uses FastAPI with SQLAlchemy
- Frontend uses React 19 with Vite
- Authentication uses JWT tokens with refresh mechanism
- Database migrations are handled automatically on startup
- Debug JSON files contain sample Oracle API responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and health checks
5. Submit a pull request

## License

[Add license information here]
