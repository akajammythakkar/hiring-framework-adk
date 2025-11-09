"""
Resume Evaluator Agent
Handles resume evaluation against JD using Google ADK
"""

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import os
import asyncio
import warnings
from typing import Dict, Any, Optional
from config import config

# Suppress async cleanup warnings
warnings.filterwarnings('ignore', message='Event loop is closed')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*Event loop is closed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*exception was never retrieved.*')
warnings.filterwarnings("ignore")

# Suppress warnings about tasks with exceptions
import sys
if sys.version_info >= (3, 8):
    import asyncio
    # Suppress task exception warnings
    def custom_exception_handler(loop, context):
        # Ignore "Event loop is closed" and "Task exception was never retrieved" during cleanup
        if 'exception' in context:
            exception = context['exception']
            if isinstance(exception, RuntimeError) and 'Event loop is closed' in str(exception):
                return
        # For other exceptions, use default handling (but silently)
        pass

def _run_async_safe(coro):
    """Run async coroutine safely, handling existing event loops and cleanup"""
    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
        
        # We're in an existing event loop (e.g., FastAPI/uvicorn)
        # Run in a thread pool to avoid blocking
        import concurrent.futures
        import threading
        
        result_holder = {}
        exception_holder = {}
        
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            # Set custom exception handler to suppress cleanup warnings
            new_loop.set_exception_handler(custom_exception_handler)
            try:
                result = new_loop.run_until_complete(coro)
                result_holder['result'] = result
            except Exception as e:
                exception_holder['exception'] = e
            finally:
                try:
                    # Allow a brief moment for any cleanup tasks
                    import time
                    time.sleep(0.1)
                    
                    # Cancel pending tasks
                    pending = asyncio.all_tasks(new_loop)
                    for task in pending:
                        task.cancel()
                    new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    
                    # Shutdown async generators
                    new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                    
                    # Allow cleanup tasks to complete
                    time.sleep(0.05)
                    
                    # Don't close the loop explicitly - let it be garbage collected
                    # This prevents "Event loop is closed" errors during async cleanup
                except:
                    pass
        
        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()
        
        if 'exception' in exception_holder:
            raise exception_holder['exception']
        return result_holder.get('result')
        
    except RuntimeError:
        # No running loop, create new one with proper cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            # Give pending tasks a chance to complete
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            return result
        finally:
            try:
                import time
                time.sleep(0.1)
                loop.run_until_complete(loop.shutdown_asyncgens())
                time.sleep(0.05)
                # Don't close loop - let garbage collection handle it
            except:
                pass


class ResumeEvaluatorAgent:
    """Agent for evaluating resumes against job descriptions using Google ADK"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Resume Evaluator Agent with Google ADK"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Set API key in environment for ADK
        os.environ["GOOGLE_API_KEY"] = self.api_key
        
        # Create session service (shared across all operations)
        self.session_service = InMemorySessionService()
        self.app_name = "resume_evaluator_app"
        self._session_counter = 0
        
        # Create ADK Agent for resume extraction
        self.extraction_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='resume_extraction_agent',
            description="Extracts and structures information from resumes",
            instruction="""You are an expert resume parser and analyzer.
            Extract and structure all relevant information from resumes including:
            - Candidate name and contact information
            - Technical skills (comprehensive list)
            - Work experience (companies, roles, years, responsibilities)
            - Total years of experience
            - Education (degrees, institutions, years)
            - Projects and achievements
            - GitHub username or profile links
            - Certifications
            - Other relevant information
            
            Format your response as clear, structured text for easy parsing."""
        )
        
        # Create ADK Agent for Level 1 evaluation
        self.evaluation_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='level_1_evaluation_agent',
            description="Evaluates resumes against job descriptions using rubrics",
            instruction="""You are an expert technical recruiter with deep experience in candidate evaluation.
            
            Your task is to perform thorough Level 1 evaluation by comparing a candidate's resume 
            against job requirements using the provided rubric.
            
            You MUST:
            1. Carefully analyze the resume against each rubric criterion
            2. Assign points based strictly on the rubric scoring guide
            3. Provide detailed reasoning for each score
            4. Cite specific examples from the resume
            5. Identify key strengths and gaps
            6. Make a clear recommendation (Yes/No for proceeding to Level 2)
            
            Format your response EXACTLY as:
            SCORE: X/10
            
            REASONING:
            [Break down by each rubric category with assigned points and justification]
            
            STRENGTHS:
            [List key matching points with specific examples]
            
            GAPS:
            [List missing or weak areas]
            
            RECOMMENDATION: Yes/No - [Brief explanation]
            
            Be objective, thorough, and cite specific evidence from the resume."""
        )
    
    async def _run_agent_async(self, agent: Agent, query: str) -> str:
        """Helper method to run an agent asynchronously"""
        # Create unique session for this operation
        self._session_counter += 1
        user_id = f"user_{self._session_counter}"
        session_id = f"session_{self._session_counter}"
        
        # Create session
        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Create runner
        runner = Runner(
            agent=agent,
            app_name=self.app_name,
            session_service=self.session_service
        )
        
        # Create message
        content = types.Content(
            role='user',
            parts=[types.Part(text=query)]
        )
        
        # Run agent and get response
        events = runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        )
        
        response_text = ""
        async for event in events:
            if event.is_final_response():
                response_text = event.content.parts[0].text
                break
        
        return response_text
    
    def extract_resume_text(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract and structure information from resume using Google ADK
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            Dictionary containing structured resume information
        """
        
        prompt = f"""
        Analyze the following resume and extract key information:
        
        Resume:
        {resume_text}
        
        Extract and structure all relevant information in a clear, organized format.
        """
        
        # Execute ADK agent using async helper
        structured_info = _run_async_safe(self._run_agent_async(self.extraction_agent, prompt))
        
        # Extract GitHub URL if present
        github_url = self._extract_github_url(resume_text)
        
        # Extract candidate name using LLM
        candidate_name = self._extract_candidate_name_llm(resume_text)
        
        return {
            "raw_resume": resume_text,
            "structured_info": structured_info,
            "github_url": github_url,
            "candidate_name": candidate_name,
            "status": "extracted"
        }
    
    def _extract_github_url(self, text: str) -> str:
        """
        Extract GitHub URL or username from text
        
        Args:
            text: Text to search for GitHub URL
            
        Returns:
            GitHub URL or username, or empty string if not found
        """
        import re
        
        # Patterns to match GitHub URLs and usernames
        patterns = [
            r'github\.com/([a-zA-Z0-9-]+)',  # github.com/username
            r'@([a-zA-Z0-9-]+)\s*\(github\)',  # @username (github)
            r'github:\s*([a-zA-Z0-9-]+)',  # github: username
            r'github\s+username:\s*([a-zA-Z0-9-]+)',  # github username: username
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Return just the username, not full URL
                return username
        
        return ""
    
    def _extract_candidate_name_llm(self, resume_text: str) -> str:
        """
        Extract candidate's full name from resume using LLM
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            Candidate's full name or "Candidate" if not found
        """
        prompt = f"""
        Extract ONLY the candidate's full name from this resume. 
        
        Resume:
        {resume_text[:1500]}
        
        IMPORTANT INSTRUCTIONS:
        - Return ONLY the person's full name (First Name + Last Name)
        - Do NOT return addresses, locations, cities, or companies
        - Do NOT return any explanation or additional text
        - If the name is in ALL CAPS, convert it to Title Case (e.g., "JOHN DOE" → "John Doe")
        - If you cannot find a clear candidate name, return exactly: "Candidate"
        
        Examples of CORRECT responses:
        - "John Smith"
        - "Sarah Johnson"
        - "Rajesh Kumar"
        
        Examples of WRONG responses (do not return these):
        - "Surat, Gujarat, India" (this is a location, not a name)
        - "Google Inc." (this is a company)
        - "Software Engineer" (this is a job title)
        
        Return only the name, nothing else:
        """
        
        try:
            # Use a simple extraction agent call
            name = _run_async_safe(self._run_agent_async(self.extraction_agent, prompt))
            name = name.strip()
            
            # Clean up common issues
            # Remove quotes if present
            name = name.strip('"\'')
            
            # Check if it looks like a location (has comma, state, country keywords)
            location_indicators = ['india', 'usa', 'uk', 'state', 'city', 'street', 'avenue', 'road']
            if any(indicator in name.lower() for indicator in location_indicators) or ',' in name:
                return "Candidate"
            
            # Check if it's too short or too long
            if len(name) < 3 or len(name) > 50:
                return "Candidate"
            
            # Title case if all caps
            if name.isupper():
                name = name.title()
            
            return name if name and name.lower() != "candidate" else "Candidate"
        except:
            return "Candidate"
    
    def evaluate_level_1(
        self, 
        resume_info: Dict[str, Any], 
        jd_info: Dict[str, Any], 
        rubric: str
    ) -> Dict[str, Any]:
        """
        Level 1 Evaluation: Compare resume against JD using rubric with Google ADK
        
        Args:
            resume_info: Structured resume information
            jd_info: Job description information
            rubric: Evaluation rubric
            
        Returns:
            Dictionary containing evaluation results with score and reasoning
        """
        
        resume_text = resume_info.get('structured_info', resume_info.get('raw_resume', ''))
        jd_text = jd_info.get('extracted_info', jd_info.get('raw_jd', ''))
        
        prompt = f"""
        Evaluate the candidate's resume against the job description using the provided rubric.
        
        JOB DESCRIPTION:
        {jd_text}
        
        RESUME:
        {resume_text}
        
        EVALUATION RUBRIC:
        {rubric}
        
        Perform a thorough Level 1 evaluation following the rubric strictly.
        """
        
        # Execute ADK agent using async helper
        response_text = _run_async_safe(self._run_agent_async(self.evaluation_agent, prompt))
        
        # Parse the response to extract score
        score = self._extract_score(response_text)
        
        # Get threshold from config
        threshold = config.get_threshold(1)
        
        # Extract GitHub URL from resume info if available
        github_url = resume_info.get('github_url', '')
        
        # Get candidate name from resume info
        candidate_name = resume_info.get('candidate_name', 'Candidate')
        
        return {
            "level": "L1",
            "score": score,
            "max_score": config.LEVEL_1_MAX_SCORE,
            "evaluation": response_text,
            "threshold": threshold,
            "passed": score >= threshold if score is not None else False,
            "github_url": github_url,
            "candidate_name": candidate_name,
            "raw_resume": resume_info.get('raw_resume', ''),
            "structured_info": resume_info.get('structured_info', ''),
            "status": "evaluated"
        }
    
    def _extract_score(self, evaluation_text: str) -> Optional[int]:
        """
        Extract numerical score from evaluation text
        
        Args:
            evaluation_text: The evaluation response text
            
        Returns:
            Extracted score or None
        """
        import re
        
        # Look for "SCORE: X/10" pattern
        score_pattern = r'SCORE:\s*(\d+)\s*/\s*10'
        match = re.search(score_pattern, evaluation_text, re.IGNORECASE)
        
        if match:
            return int(match.group(1))
        
        # Alternative patterns
        alt_pattern = r'(\d+)\s*/\s*10'
        match = re.search(alt_pattern, evaluation_text)
        
        if match:
            return int(match.group(1))
        
        return None
    
    def get_evaluation_summary(self, evaluation_result: Dict[str, Any]) -> str:
        """
        Generate a concise summary of the evaluation
        
        Args:
            evaluation_result: The evaluation result dictionary
            
        Returns:
            Formatted summary string
        """
        
        score = evaluation_result.get('score', 'N/A')
        max_score = evaluation_result.get('max_score', 10)
        passed = evaluation_result.get('passed', False)
        
        summary = f"""
╔════════════════════════════════════════════════════════════╗
║              LEVEL 1 EVALUATION SUMMARY                    ║
╠════════════════════════════════════════════════════════════╣
║  Score: {score}/{max_score}                                         
║  Status: {'✓ PASSED' if passed else '✗ FAILED'}                                    
║  Threshold: {evaluation_result.get('threshold', 7)}/10                              
╚════════════════════════════════════════════════════════════╝

{evaluation_result.get('evaluation', '')}
"""
        return summary
