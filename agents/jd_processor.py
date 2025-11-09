"""
Job Description Processor Agent
Handles JD extraction and rubric generation using Google ADK
"""

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import os
import asyncio
import warnings
from typing import Dict, Any

# Suppress async cleanup warnings
warnings.filterwarnings('ignore', message='Event loop is closed')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*Event loop is closed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*exception was never retrieved.*')

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


class JDProcessorAgent:
    """Agent for processing Job Descriptions and generating evaluation rubrics using Google ADK"""
    
    def __init__(self, api_key: str = None):
        """Initialize the JD Processor Agent with Google ADK"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Set API key in environment for ADK
        os.environ["GOOGLE_API_KEY"] = self.api_key
        
        # Create session service (shared across all operations)
        self.session_service = InMemorySessionService()
        self.app_name = "jd_processor_app"
        self._session_counter = 0
        
        # Create ADK Agent for JD extraction
        self.extraction_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='jd_extraction_agent',
            description="Extracts key requirements from job descriptions",
            instruction="""You are an expert HR analyst specializing in job description analysis.
            Extract and structure key information from job descriptions including:
            - Job title
            - Required technical skills
            - Years of experience required
            - Education requirements
            - Preferred skills
            - Key responsibilities
            - Domain/Industry
            
            Format your response as clear, structured text that's easy to parse."""
        )
        
        # Create ADK Agent for rubric generation
        self.rubric_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='rubric_generation_agent',
            description="Generates evaluation rubrics from job requirements",
            instruction="""You are an expert in creating hiring evaluation rubrics.
            Create a detailed, weighted evaluation rubric for Level 1 screening with this structure:
            
            LEVEL 1 EVALUATION RUBRIC (Total: 10 points)
            
            1. Technical Skills Match (4 points)
               - 4: All required skills present with strong evidence
               - 3: Most required skills present
               - 2: Some required skills present
               - 1: Few required skills present
               - 0: No technical skills match
            
            2. Experience Level (3 points)
               - 3: Meets or exceeds experience requirements
               - 2: Close to required experience
               - 1: Below required experience
               - 0: Significantly below requirements
            
            3. Education & Qualifications (2 points)
               - 2: Meets education requirements
               - 1: Partial match or equivalent
               - 0: Does not meet requirements
            
            4. Role Relevance (1 point)
               - 1: Previous roles highly relevant
               - 0: Roles not relevant
            
            Customize this rubric based on the specific job requirements provided."""
        )
        
        # Create ADK Agent for rubric refinement
        self.refinement_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='rubric_refinement_agent',
            description="Refines evaluation rubrics based on user feedback",
            instruction="""You are an expert at refining evaluation criteria.
            Take the current rubric and user feedback, then improve the rubric
            while maintaining its structure and practicality for candidate evaluation.
            Ensure the rubric remains objective and measurable."""
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
    
    def extract_jd_requirements(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract key requirements from Job Description using Google ADK
        
        Args:
            jd_text: Raw job description text
            
        Returns:
            Dictionary containing extracted requirements
        """
        
        prompt = f"""
        Analyze the following Job Description and extract key information in a structured format.
        
        Job Description:
        {jd_text}
        
        Extract and return:
        1. Job Title
        2. Required Technical Skills (list)
        3. Required Years of Experience
        4. Education Requirements
        5. Preferred Skills (list)
        6. Key Responsibilities (list)
        7. Domain/Industry
        
        Format your response as a structured JSON-like text.
        """
        
        # Execute ADK agent using async helper
        extracted_info = _run_async_safe(self._run_agent_async(self.extraction_agent, prompt))
        
        return {
            "raw_jd": jd_text,
            "extracted_info": extracted_info,
            "status": "extracted"
        }
    
    def generate_rubric(self, jd_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate evaluation rubric based on JD requirements using Google ADK
        
        Args:
            jd_info: Extracted JD information
            
        Returns:
            Dictionary containing evaluation rubric
        """
        
        prompt = f"""
        Based on the following Job Description information, create a detailed evaluation rubric 
        for Level 1 screening (Resume vs JD comparison).
        
        JD Information:
        {jd_info.get('extracted_info', jd_info.get('raw_jd', ''))}
        
        IMPORTANT INSTRUCTIONS:
        - Output ONLY the rubric itself, no preamble or explanation text
        - Do NOT wrap your response in code blocks or backticks
        - Use markdown formatting (headings, bullet points, bold text)
        - Customize the standard rubric structure based on the specific JD requirements
        - Start directly with the rubric title
        
        Return the rubric in a clear, well-formatted markdown structure.
        """
        
        # Execute ADK agent using async helper
        rubric_text = _run_async_safe(self._run_agent_async(self.rubric_agent, prompt))
        
        # Clean up code block markers if present
        rubric_text = self._clean_code_blocks(rubric_text)
        
        return {
            "rubric": rubric_text,
            "jd_info": jd_info,
            "status": "rubric_generated"
        }
    
    def _clean_code_blocks(self, text: str) -> str:
        """Remove markdown code block wrappers and preamble text"""
        import re
        
        # Remove preamble text before the rubric (like "Okay, I will generate...")
        # Look for the actual rubric start (typically starts with # or LEVEL)
        rubric_patterns = [
            r'(?:^|\n)(#{1,3}\s*LEVEL\s+1.*)',
            r'(?:^|\n)(LEVEL\s+1\s+EVALUATION.*)',
            r'(?:^|\n)(#{1,3}.*RUBRIC.*)',
        ]
        
        for pattern in rubric_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                text = match.group(1)
                break
        
        # Remove code block markers (```...```)
        text = re.sub(r'^```[\w]*\s*\n', '', text.strip(), flags=re.MULTILINE)
        text = re.sub(r'\n\s*```\s*$', '', text.strip(), flags=re.MULTILINE)
        
        # Remove any remaining code blocks in the middle
        text = re.sub(r'```[\w]*\s*\n', '', text)
        text = re.sub(r'\n```', '', text)
        
        return text.strip()
    
    def refine_rubric(self, current_rubric: str, user_feedback: str) -> Dict[str, Any]:
        """
        Refine rubric based on user feedback using Google ADK
        
        Args:
            current_rubric: Current rubric text
            user_feedback: User's feedback for refinement
            
        Returns:
            Dictionary containing refined rubric
        """
        
        prompt = f"""
        Here is the current evaluation rubric:
        
        {current_rubric}
        
        User Feedback:
        {user_feedback}
        
        Please refine the rubric based on the user's feedback while maintaining the structure 
        and ensuring it remains practical for candidate evaluation.
        """
        
        # Execute ADK agent using async helper
        refined_rubric = _run_async_safe(self._run_agent_async(self.refinement_agent, prompt))
        
        return {
            "rubric": refined_rubric,
            "status": "rubric_refined",
            "applied_feedback": user_feedback
        }
