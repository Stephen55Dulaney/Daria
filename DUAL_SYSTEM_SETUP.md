# Dual System Setup: Daria & Remote Interview System

This document explains how to run both the Daria Interview Tool and the Remote Interview System simultaneously.

## Port Configuration

| Application | Component | Port | Notes |
|-------------|-----------|------|-------|
| Remote Interview System | Flask Backend | 5001 | Used for the remote interview functionality |
| Remote Interview System | React Frontend | 5175 | Auto-selected by Vite after 5174 was busy |
| Daria Interview Tool | Flask Backend | 5003 | Used for the main Daria application |
| Daria Interview Tool | React Frontend | 5174 | Original port configured in Vite |

## Running Both Systems

### 1. Start the Remote Interview System

1. Open a terminal and navigate to the project directory:
   ```bash
   cd /path/to/DariaInterviewTool
   ```

2. Activate your virtual environment (if using one):
   ```bash
   source venv/bin/activate
   ```

3. Run the Remote Interview System backend:
   ```bash
   python run_remote_interview.py
   ```

4. Open another terminal, navigate to the frontend directory, and start the React frontend:
   ```bash
   cd frontend
   npm run dev
   ```

5. The Remote Interview System will be accessible at:
   - Frontend: http://localhost:5175/
   - API: http://localhost:5001/

### 2. Start the Daria Interview Tool

1. Open a new terminal and navigate to the project directory:
   ```bash
   cd /path/to/DariaInterviewTool
   ```

2. Activate your virtual environment (if using one):
   ```bash
   source venv/bin/activate
   ```

3. Run the Daria Interview Tool backend:
   ```bash
   python run_daria.py
   ```

4. The Daria Interview Tool will be accessible at:
   - Backend: http://localhost:5003/
   - React frontend pages will automatically use port 5174 when accessed through the backend

## Feature Distribution

### Remote Interview System (LangChain-Based)
- Remote interviews with shareable links
- Real-time interview monitoring
- Voice interactions using ElevenLabs
- AI-driven interview analysis
- Available at `/langchain/interview/setup`

### Daria Interview Tool (Main System)
- Home page
- Interview archive
- Advanced search
- Upload transcript
- Annotated transcript viewer
- Research planning
- Discovery planning
- Available at the standard routes

## Troubleshooting

### SQLAlchemy Errors
The SQLAlchemy errors you might see are non-fatal - the database tables already exist, so the application tries to create them again but continues running despite these errors.

### Port Conflicts
If you see port conflicts, ensure no other applications are using ports 5001, 5003, 5174, or 5175.

### Frontend Routing Issues
If you encounter issues with the frontend routing:
1. Check that Vite is correctly configured for port 5174
2. Ensure CORS is properly configured in both backend apps
3. Verify that the API URLs in the frontend point to the correct ports 