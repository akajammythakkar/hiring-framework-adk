"""
GitHub Analyzer Agent
Analyzes candidate's GitHub profile and repositories using Google ADK
"""

from google.adk.agents import Agent
from google.adk.runners import Runner   
from google.adk.sessions import InMemorySessionService
from google.genai import types
import os
import asyncio
import warnings
import requests
import re
from typing import Dict, Any, Optional
from config import config

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


class GitHubAnalyzerAgent:
    """Agent for analyzing GitHub profiles and repositories using Google ADK"""
    
    def __init__(self, api_key: str = None):
        """Initialize the GitHub Analyzer Agent with Google ADK"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Set API key in environment for ADK
        os.environ["GOOGLE_API_KEY"] = self.api_key
        
        # Create session service (shared across all operations)
        self.session_service = InMemorySessionService()
        self.app_name = "github_analyzer_app"
        self._session_counter = 0
        
        # Create ADK Agent for GitHub analysis
        self.analysis_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='github_analysis_agent',
            description="Analyzes GitHub profiles and repositories for technical assessment",
            instruction="""You are an expert at evaluating software engineering skills through GitHub profiles.
            Analyze repositories for:
            - Code quality and best practices
            - Project complexity and technical depth
            - Consistency of contributions
            - Technology stack alignment with job requirements
            - Documentation quality
            - Testing practices
            - Active maintenance and recent activity
            
            Provide objective, evidence-based assessments with specific examples."""
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
    
    def _extract_github_username(self, github_url: str) -> str:
        """
        Extract GitHub username from URL or return the username directly
        
        Args:
            github_url: GitHub profile URL or username
            
        Returns:
            GitHub username
        """
        # Remove trailing slashes
        github_url = github_url.strip().rstrip('/')
        
        # If it's a URL, extract username
        if 'github.com' in github_url.lower():
            # Match patterns like github.com/username
            match = re.search(r'github\.com/([a-zA-Z0-9-]+)', github_url, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Otherwise, assume it's a username (remove @ if present)
        return github_url.replace('@', '').strip()
    
    def _validate_github_username(self, username: str) -> bool:
        """
        Validate if GitHub username exists by checking GitHub API
        
        Args:
            username: GitHub username
            
        Returns:
            True if username exists, False otherwise
            
        Raises:
            ValueError: If username doesn't exist
        """
        try:
            # Use GitHub API to check if user exists
            response = requests.get(
                f"https://api.github.com/users/{username}",
                timeout=10,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            
            if response.status_code == 404:
                raise ValueError(f"GitHub username '{username}' does not exist. Please verify the username and try again.")
            elif response.status_code == 403:
                # Rate limit exceeded - allow analysis to continue but warn
                print(f"⚠️ Warning: GitHub API rate limit exceeded. Unable to verify username '{username}'")
                return True
            elif response.status_code != 200:
                # Other errors - allow analysis to continue but warn
                print(f"⚠️ Warning: Could not verify GitHub username '{username}' (HTTP {response.status_code})")
                return True
            
            # Username exists
            return True
            
        except requests.exceptions.RequestException as e:
            # Network error - allow analysis to continue but warn
            print(f"⚠️ Warning: Network error while validating username '{username}': {str(e)}")
            return True
    
    def analyze_github_profile(self, github_url: str, jd_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze GitHub profile based on job requirements using Google ADK
        
        Args:
            github_url: GitHub profile URL or username
            jd_info: Job description information for context
            
        Returns:
            Dictionary containing analysis and score
            
        Raises:
            ValueError: If GitHub username doesn't exist
        """
        
        # Extract and validate GitHub username
        username = self._extract_github_username(github_url)
        print(f"🔍 Validating GitHub username: {username}")
        self._validate_github_username(username)
        print(f"✓ GitHub username '{username}' verified")
        
        jd_text = jd_info.get('extracted_info', jd_info.get('raw_jd', ''))
        
        prompt = f"""
        Analyze the following GitHub profile/username for a technical position.
        
        GitHub Profile/URL: {github_url}
        
        Job Requirements:
        {jd_text}
        
        Based on typical GitHub profile analysis, provide an evaluation covering:
        
        1. **Repository Quality** (0-3 points)
           - Code organization and structure
           - Adherence to best practices
           - Project complexity
        
        2. **Technology Stack Alignment** (0-3 points)
           - Relevance to job requirements
           - Depth of experience in required technologies
           - Breadth of technical skills
        
        3. **Activity & Consistency** (0-2 points)
           - Recent contributions
           - Consistency of commits
           - Active maintenance
        
        4. **Documentation & Testing** (0-2 points)
           - README quality
           - Code documentation
           - Test coverage
        
        Provide your evaluation in this format:
        
        ## GITHUB ANALYSIS
        
        **SCORE: X/10**
        
        ### Repository Quality (X/3)
        [Detailed analysis with examples]
        
        ### Technology Stack Alignment (X/3)
        [Detailed analysis with examples]
        
        ### Activity & Consistency (X/2)
        [Detailed analysis]
        
        ### Documentation & Testing (X/2)
        [Detailed analysis]
        
        ### STRENGTHS:
        - [List key strengths]
        
        ### AREAS FOR IMPROVEMENT:
        - [List areas to improve]
        
        ### RECOMMENDATION:
        [Pass/Fail with reasoning]
        
        Note: If you cannot access the actual GitHub profile, provide a template evaluation 
        based on typical expectations for the role and mention that actual profile verification is needed.
        """
        
        # Execute ADK agent using async helper
        analysis_text = _run_async_safe(self._run_agent_async(self.analysis_agent, prompt))
        
        # Parse score
        score = self._extract_score(analysis_text)
        
        # Get threshold from config
        threshold = config.get_threshold(2)
        
        return {
            "level": "L2",
            "score": score,
            "max_score": config.LEVEL_2_MAX_SCORE,
            "analysis": analysis_text,
            "github_url": github_url,
            "threshold": threshold,
            "passed": score >= threshold if score is not None else False,
            "status": "analyzed"
        }
    
    def _extract_score(self, analysis_text: str) -> Optional[int]:
        """
        Extract numerical score from analysis text
        
        Args:
            analysis_text: The analysis response text
            
        Returns:
            Score as integer or None if not found
        """
        import re
        
        # Try to find patterns like "SCORE: 8/10" or "Score: 8/10"
        patterns = [
            r'SCORE:\s*(\d+)/10',
            r'Score:\s*(\d+)/10',
            r'score:\s*(\d+)/10',
            r'Total:\s*(\d+)/10',
            r'(\d+)/10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        
        return None
