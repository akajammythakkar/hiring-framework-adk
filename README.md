# Tech Hiring Agentic Framework Powered by Google Gemini and Google ADK

An AI-powered hiring evaluation system built with Google ADK (Agent Development Kit) that automates candidate assessment through resume analysis, GitHub profile evaluation, and comprehensive final verdicts.

## 🌟 Features

- **Multi-Level Evaluation System**
  - **Level 1**: Resume screening against job description
  - **Level 2**: GitHub profile and repository analysis
  - **Level 3**: Coding assessment (optional)
  - **Final Verdict**: Comprehensive hiring recommendation

- **Intelligent Analysis**
  - JD processing and automatic rubric generation
  - Resume parsing with structured information extraction
  - GitHub username validation (prevents hallucination)
  - Markdown-formatted analysis with proper PDF rendering

- **Modern Web Interface**
  - Built with Next.js and React
  - Real-time evaluation progress
  - Dark mode support
  - Interactive results display
  - PDF report generation

- **RESTful API**
  - FastAPI backend
  - Comprehensive endpoints for all evaluation levels
  - Configurable thresholds
  - Export to PDF

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (for webapp)
- Google API Key (for Gemini models)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd tech-hiring-adk
```

### 2. Setup Backend

```bash
# Run the setup script
chmod +x setup.sh
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Setup Frontend (Optional)

```bash
cd webapp
npm install
```

### 4. Start the Application

**Terminal 1 - Backend API:**
```bash
python api_server.py
# Server runs on http://localhost:8000
```

**Terminal 2 - Frontend (Optional):**
```bash
cd webapp
npm run dev
# Web app runs on http://localhost:3000
```

## 🔑 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional - Evaluation Thresholds (out of 10)
LEVEL_1_THRESHOLD=7.0
LEVEL_2_THRESHOLD=6.0
LEVEL_3_THRESHOLD=8.0

# Optional - Model Configuration
MODEL_NAME=gemini-2.0-flash-exp

# Optional - API Server
API_HOST=0.0.0.0
API_PORT=8000
```

### Evaluation Thresholds

You can adjust passing thresholds for each level:
- **Level 1 (Resume)**: Default 7.0/10
- **Level 2 (GitHub)**: Default 6.0/10
- **Level 3 (Coding)**: Default 8.0/10

Update via API:
```bash
curl -X POST "http://localhost:8000/api/v1/config/thresholds?level_1=7.5&level_2=6.5"
```

## 📖 Usage

### Using the Web Interface

1. Navigate to `http://localhost:3000`
2. **Step 1**: Upload or paste Job Description
3. **Step 2**: Upload or paste Resume
4. **Step 3**: Enter GitHub username/URL
5. **Step 4**: View results and generate final verdict
6. Download comprehensive PDF report

### Using the API

#### 1. Upload Job Description

```bash
curl -X POST "http://localhost:8000/api/v1/jd/upload-text" \
  -H "Content-Type: application/json" \
  -d '{"jd_text": "Your job description here..."}'
```

#### 2. Generate Rubric

```bash
curl -X POST "http://localhost:8000/api/v1/rubric/generate"
```

#### 3. Evaluate Resume

```bash
curl -X POST "http://localhost:8000/api/v1/resume/evaluate-text" \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Candidate resume here..."}'
```

#### 4. Analyze GitHub

```bash
curl -X POST "http://localhost:8000/api/v1/github/analyze" \
  -H "Content-Type: application/json" \
  -d '{"github_url": "torvalds"}'
```

#### 5. Generate Final Verdict

```bash
curl -X POST "http://localhost:8000/api/v1/verdict/generate"
```

#### 6. Export PDF Report

```bash
curl -X GET "http://localhost:8000/api/v1/export/pdf" \
  --output report.pdf
```

## 🏗️ Architecture

```
tech-hiring-adk/
├── agents/                    # AI agents for each evaluation level
│   ├── job_description_processor.py       # Job description processing
│   ├── resume_evaluator.py   # Resume analysis
│   ├── github_analyzer.py    # GitHub profile evaluation
│   └── final_verdict.py      # Final decision maker
├── utils/                     # Utility modules
│   ├── text_extractor.py     # PDF/DOCX text extraction
│   └── pdf_generator.py      # Report generation
├── webapp/                    # Next.js frontend
│   └── src/app/page.tsx      # Main UI component
├── api_server.py             # FastAPI backend
├── hiring_framework.py       # Core orchestration
├── config.py                 # Configuration management
└── requirements.txt          # Python dependencies
```

## 🔧 Key Features Explained

### GitHub Username Validation

The system validates GitHub usernames before analysis to prevent LLM hallucination:

```python
# Automatically checks if username exists
# Raises error if invalid: "GitHub username 'xyz' does not exist"
```

### Markdown-Formatted PDFs

Analysis results preserve formatting in PDF:
- ✅ **Bold** and *italic* text
- ✅ Headings (H1-H6)
- ✅ Bullet points with indentation
- ✅ Proper paragraph spacing

### Candidate Name Extraction

Intelligently extracts candidate names from:
- Explicit "Name:" fields
- First lines of resume
- Structured resume information
- ALL CAPS names (converted to title case)

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jd/upload-text` | POST | Upload JD as text |
| `/api/v1/jd/upload-file` | POST | Upload JD as PDF/DOCX |
| `/api/v1/rubric/generate` | POST | Generate evaluation rubric |
| `/api/v1/rubric/refine` | POST | Refine existing rubric |
| `/api/v1/resume/evaluate-text` | POST | Evaluate resume text |
| `/api/v1/resume/evaluate-file` | POST | Evaluate resume file |
| `/api/v1/github/analyze` | POST | Analyze GitHub profile |
| `/api/v1/verdict/generate` | POST | Generate final verdict |
| `/api/v1/verdict/current` | GET | Get current verdict |
| `/api/v1/export/pdf` | GET | Download PDF report |
| `/api/v1/config/thresholds` | GET/POST | Get/update thresholds |
| `/api/v1/reset` | POST | Reset framework state |

## 🧪 Testing

```bash
# Test individual components
python -c "from agents.github_analyzer import GitHubAnalyzerAgent; agent = GitHubAnalyzerAgent(); print(agent._extract_github_username('https://github.com/torvalds'))"

# Test API endpoints
curl http://localhost:8000/docs  # OpenAPI documentation
```

## 🐛 Troubleshooting

### "Event loop is closed" warnings

These are harmless async cleanup warnings that are automatically suppressed. If they persist, restart the server.

### GitHub username not found

Ensure:
- Username exists on GitHub
- No typos in username
- Valid GitHub URL format

### PDF not rendering markdown

Ensure you're using the latest version. The markdown-to-PDF converter properly handles:
- Headers, bold, italic
- Bullet points
- Code blocks

### Candidate name shows as "Candidate"

The system tries multiple extraction methods. Ensure the resume has:
- Name field clearly labeled
- Name in first few lines
- Proper capitalization

## 📝 License

This project is built using Google ADK and follows applicable licensing terms.

## 🤝 Contributing

Contributions welcome! Please ensure:
- Code follows existing patterns
- Tests pass
- Documentation is updated

## 📧 Support

For issues and questions:
- Check the troubleshooting section
- Review API documentation at `http://localhost:8000/docs`
- Ensure all dependencies are installed

## 🎯 Roadmap

- [ ] Level 3 coding assessment implementation
- [ ] Multi-language support
- [ ] Batch candidate processing
- [ ] Interview scheduling integration
- [ ] Analytics dashboard
- [ ] Email notifications

---

**Built with Google ADK** | **Powered by Gemini 2.0**
