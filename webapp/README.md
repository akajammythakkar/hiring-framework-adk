# Tech Hiring Web App

Beautiful modern web interface for the Tech Hiring Agentic Framework.

## Features

- ✨ Modern, responsive UI with Tailwind CSS
- 🎯 3-step workflow (JD → Rubric → Evaluation)
- 🚀 Real-time evaluation results
- 📱 Mobile-friendly design
- 🎨 Beautiful gradient UI with icons

## Setup

### 1. Install Dependencies

```bash
cd webapp
npm install
```

### 2. Start Backend API

In a separate terminal:

```bash
cd ..  # Back to project root
conda activate adk-hiring
python api_server.py
```

The API will run on `http://localhost:8000`

### 3. Start Frontend

```bash
npm run dev
```

The web app will be available at `http://localhost:3000`

## Usage

1. **Step 1**: Paste your job description
2. **Step 2**: Review generated rubric, then paste candidate resume
3. **Step 3**: View evaluation results with score and detailed reasoning

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Backend**: FastAPI (Python)

## Development

```bash
# Development server
npm run dev

# Build for production
npm build

# Start production server
npm start
```

## Environment

The app connects to the backend at `http://localhost:8000`. If your API runs on a different port, update the `API_URL` in `src/app/page.tsx`.

## Screenshots

The app features:
- Clean, modern interface
- Step-by-step progress indicator
- Textarea inputs for JD and resumes
- Color-coded pass/fail results
- Detailed evaluation display

## Notes

- Ensure the backend API server is running before using the web app
- The app uses Google ADK agents through the FastAPI backend
- All processing happens server-side for security
