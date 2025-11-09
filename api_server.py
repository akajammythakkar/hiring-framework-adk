"""
FastAPI Server for Tech Hiring Agentic Framework
Provides REST API endpoints for the hiring evaluation system
"""

import warnings
import asyncio
import sys
import io
import contextlib

# Suppress async cleanup warnings globally
warnings.filterwarnings('ignore', message='Event loop is closed')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*Event loop is closed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited.*')
warnings.filterwarnings('ignore')

# Filter stderr to suppress specific async cleanup errors
class StderrFilter(io.TextIOBase):
    """Filter stderr to suppress specific error messages"""
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.suppress_patterns = [
            'Event loop is closed',
            'Task exception was never retrieved',
            'future:',
            'google.genai._api_client',
            'BaseApiClient.aclose'
        ]
    
    def write(self, text):
        # Check if any suppress pattern is in the text
        if any(pattern in text for pattern in self.suppress_patterns):
            return  # Silently ignore
        return self.original_stderr.write(text)
    
    def flush(self):
        return self.original_stderr.flush()

# Apply stderr filter
sys.stderr = StderrFilter(sys.stderr)

# Suppress asyncio task exception messages
def custom_exception_handler(loop, context):
    """Suppress 'Task exception was never retrieved' messages for event loop closure"""
    exception = context.get('exception')
    if isinstance(exception, RuntimeError) and 'Event loop is closed' in str(exception):
        return  # Silently ignore
    if 'future' in context.get('message', ''):
        return  # Ignore future/task cleanup errors
    # For other exceptions, log them but don't print traceback
    if exception:
        pass  # Silently ignore all async cleanup exceptions

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
from hiring_framework import HiringFramework
from utils import TextExtractor, pdf_generator
from config import config

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Tech Hiring Agentic Framework API",
    description="AI-powered hiring evaluation system using Google ADK",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to configure asyncio exception handler
@app.on_event("startup")
async def startup_event():
    """Configure asyncio exception handler to suppress cleanup warnings"""
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(custom_exception_handler)
    except:
        pass

# Initialize hiring framework
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

framework = HiringFramework(api_key=api_key)
text_extractor = TextExtractor()


# ==================== Request/Response Models ====================

class JDTextRequest(BaseModel):
    jd_text: str


class RubricFeedbackRequest(BaseModel):
    feedback: str


class ResumeTextRequest(BaseModel):
    resume_text: str


class StatusResponse(BaseModel):
    status: str
    message: str


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Tech Hiring Agentic Framework API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ==================== Step 1: JD Processing ====================

@app.post("/api/v1/jd/upload-text")
async def upload_jd_text(request: JDTextRequest):
    """
    Upload Job Description as text
    """
    try:
        result = framework.process_jd(jd_text=request.jd_text)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jd/upload-file")
async def upload_jd_file(file: UploadFile = File(...)):
    """
    Upload Job Description as file (PDF or TXT)
    """
    try:
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        file_extension = file.filename.split('.')[-1].lower()
        jd_text = text_extractor.extract_text(
            file_bytes=content,
            file_extension=file_extension
        )
        
        # Process JD
        result = framework.process_jd(jd_text=jd_text)
        
        return {
            "status": "success",
            "filename": file.filename,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rubric/generate")
async def generate_rubric():
    """
    Generate evaluation rubric based on processed JD
    """
    try:
        if not framework.current_jd:
            raise HTTPException(
                status_code=400,
                detail="Job Description must be uploaded first"
            )
        
        result = framework.generate_rubric()
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/rubric/current")
async def get_current_rubric():
    """
    Get the current rubric
    """
    if not framework.current_rubric:
        raise HTTPException(status_code=404, detail="No rubric generated yet")
    
    return {
        "status": "success",
        "rubric": framework.current_rubric
    }


@app.post("/api/v1/rubric/refine")
async def refine_rubric(request: RubricFeedbackRequest):
    """
    Refine rubric based on user feedback
    """
    try:
        if not framework.current_rubric:
            raise HTTPException(
                status_code=400,
                detail="Rubric must be generated first"
            )
        
        result = framework.refine_rubric_with_feedback(request.feedback)
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Step 2: Resume Evaluation (Level 1) ====================

@app.post("/api/v1/resume/evaluate-text")
async def evaluate_resume_text(request: ResumeTextRequest):
    """
    Evaluate resume provided as text (Level 1)
    """
    try:
        if not framework.current_jd or not framework.current_rubric:
            raise HTTPException(
                status_code=400,
                detail="JD and Rubric must be set up first"
            )
        
        result = framework.evaluate_resume_level_1(resume_text=request.resume_text)
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Level 2: GitHub Analysis ====================

class GitHubRequest(BaseModel):
    github_url: str

@app.post("/api/v1/github/analyze")
async def analyze_github(request: GitHubRequest):
    """
    Analyze GitHub profile for Level 2 evaluation
    
    - **github_url**: GitHub profile URL or username
    """
    try:
        if not framework.current_jd:
            raise HTTPException(
                status_code=400,
                detail="JD must be processed first (Step 1)"
            )
        
        print("🔍 Analyzing GitHub profile...")
        
        result = framework.analyze_github(github_url=request.github_url)
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors (e.g., invalid GitHub username)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/resume/evaluate-file")
async def evaluate_resume_file(file: UploadFile = File(...)):
    """
    Evaluate resume provided as file (Level 1)
    """
    try:
        if not framework.current_jd or not framework.current_rubric:
            raise HTTPException(
                status_code=400,
                detail="JD and Rubric must be set up first"
            )
        
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        file_extension = file.filename.split('.')[-1].lower()
        resume_text = text_extractor.extract_text(
            file_bytes=content,
            file_extension=file_extension
        )
        
        # Evaluate resume
        result = framework.evaluate_resume_level_1(resume_text=resume_text)
        
        return {
            "status": "success",
            "filename": file.filename,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/evaluations/report")
async def get_evaluation_report():
    """
    Get comprehensive evaluation report
    """
    report = framework.get_evaluation_report()
    
    return {
        "status": "success",
        "report": report,
        "total_evaluations": len(framework.evaluation_results),
        "evaluations": framework.evaluation_results
    }


@app.get("/api/v1/config/thresholds")
async def get_thresholds():
    """
    Get current evaluation thresholds
    """
    return {
        "status": "success",
        "data": {
            "level_1": config.LEVEL_1_THRESHOLD,
            "level_2": config.LEVEL_2_THRESHOLD,
            "level_3": config.LEVEL_3_THRESHOLD
        }
    }


@app.post("/api/v1/config/thresholds")
async def update_thresholds(
    level_1: Optional[float] = None,
    level_2: Optional[float] = None,
    level_3: Optional[float] = None
):
    """
    Update evaluation thresholds
    
    - **level_1**: Threshold for Level 1 (0-10)
    - **level_2**: Threshold for Level 2 (0-10)
    - **level_3**: Threshold for Level 3 (0-10)
    """
    if level_1 is not None:
        if not 0 <= level_1 <= 10:
            raise HTTPException(status_code=400, detail="Level 1 threshold must be between 0 and 10")
        config.set_threshold(1, level_1)
    
    if level_2 is not None:
        if not 0 <= level_2 <= 10:
            raise HTTPException(status_code=400, detail="Level 2 threshold must be between 0 and 10")
        config.set_threshold(2, level_2)
    
    if level_3 is not None:
        if not 0 <= level_3 <= 10:
            raise HTTPException(status_code=400, detail="Level 3 threshold must be between 0 and 10")
        config.set_threshold(3, level_3)
    
    return {
        "status": "success",
        "message": "Thresholds updated successfully",
        "data": {
            "level_1": config.LEVEL_1_THRESHOLD,
            "level_2": config.LEVEL_2_THRESHOLD,
            "level_3": config.LEVEL_3_THRESHOLD
        }
    }


@app.post("/api/v1/reset")
async def reset_framework():
    """
    Reset framework state
    """
    framework.reset()
    return {
        "status": "success",
        "message": "Framework state reset successfully"
    }


# ==================== Step 5: Final Verdict ====================

@app.post("/api/v1/verdict/generate")
async def generate_final_verdict():
    """
    Generate final hiring verdict by combining all evaluation levels
    
    Combines Level 1 (Resume), Level 2 (GitHub), and optionally Level 3 (Coding)
    to provide a comprehensive hiring recommendation.
    """
    try:
        if not framework.current_jd:
            raise HTTPException(
                status_code=400,
                detail="JD must be processed first (Step 1)"
            )
        
        if not framework.latest_level_1:
            raise HTTPException(
                status_code=400,
                detail="Level 1 (Resume) evaluation must be completed first"
            )
        
        if not framework.latest_level_2:
            raise HTTPException(
                status_code=400,
                detail="Level 2 (GitHub) evaluation must be completed first"
            )
        
        print("🎯 Generating Final Verdict...")
        
        result = framework.generate_final_verdict()
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/verdict/current")
async def get_current_verdict():
    """
    Get the current final verdict if available
    """
    if not framework.latest_final_verdict:
        raise HTTPException(status_code=404, detail="No final verdict generated yet")
    
    return {
        "status": "success",
        "data": framework.latest_final_verdict
    }


# ==================== PDF Export ====================

@app.get("/api/v1/export/pdf")
async def export_evaluation_pdf():
    """
    Export complete evaluation report as PDF
    
    Includes:
    - Level 1 (Resume) evaluation
    - Level 2 (GitHub) analysis (if available)
    - Final verdict (if available)
    """
    try:
        if not framework.latest_level_1:
            raise HTTPException(
                status_code=400,
                detail="No evaluation data available. Please complete at least Level 1 evaluation."
            )
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_full_report(
            evaluation=framework.latest_level_1,
            github_analysis=framework.latest_level_2,
            final_verdict=framework.latest_final_verdict
        )
        
        # Extract candidate name from evaluation data
        candidate_name = framework.latest_level_1.get('candidate_name', 'Candidate')
        
        # Format name for filename
        import re
        # Remove special chars and extra spaces
        safe_name = re.sub(r'[^\w\s-]', '', candidate_name).strip()
        
        # Split into parts (first name, last name, etc.)
        name_parts = safe_name.split()
        
        # Generate filename based on name parts
        if len(name_parts) >= 2:
            # Has first and last name: candidate_evaluation_FirstName_LastName
            filename = f"candidate_evaluation_{name_parts[0]}_{name_parts[-1]}.pdf"
        elif len(name_parts) == 1:
            # Only first name: candidate_evaluation_FirstName
            filename = f"candidate_evaluation_{name_parts[0]}.pdf"
        else:
            # Fallback: candidate_evaluation_Candidate
            filename = "candidate_evaluation_Candidate.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print(" " * 15 + "TECH HIRING AGENTIC FRAMEWORK API")
    print(" " * 20 + "Powered by Google ADK")
    print("=" * 70)
    print("\nStarting server...")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
