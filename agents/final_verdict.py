"""
Final Verdict Agent
Combines Level 1 (Resume) and Level 2 (GitHub) analysis to provide final hiring decision
"""

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import os
import asyncio
import warnings
from typing import Dict, Any, Optional, List
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


class FinalVerdictAgent:
    """Agent for generating final hiring verdict by combining all evaluation levels"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Final Verdict Agent with Google ADK"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Set API key in environment for ADK
        os.environ["GOOGLE_API_KEY"] = self.api_key
        
        # Create session service (shared across all operations)
        self.session_service = InMemorySessionService()
        self.app_name = "final_verdict_app"
        self._session_counter = 0
        
        # Create ADK Agent for final verdict
        self.verdict_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='final_verdict_agent',
            description="Synthesizes all evaluation data to provide final hiring recommendation",
            instruction="""You are a senior technical hiring manager with expertise in comprehensive candidate evaluation.
            
            Your task is to analyze all evaluation data from multiple levels and provide a final, decisive hiring recommendation.
            
            You MUST:
            1. Weigh the importance of each evaluation level (Resume, GitHub, Coding Assessment if available)
            2. Consider overall fit for the role based on all evidence
            3. Identify key decision factors (both positive and negative)
            4. Account for any red flags or exceptional strengths
            5. Provide a clear, justified HIRE or NO HIRE recommendation
            6. Include confidence level in your decision (High/Medium/Low)
            7. Suggest next steps (e.g., interview rounds, additional assessments)
            
            Be objective, thorough, and base your decision on concrete evidence from all evaluations.
            Consider both technical skills and other factors like consistency, documentation, best practices."""
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
    
    def generate_final_verdict(
        self,
        jd_info: Dict[str, Any],
        level_1_result: Dict[str, Any],
        level_2_result: Dict[str, Any],
        level_3_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate final hiring verdict by combining all evaluation levels
        
        Args:
            jd_info: Job description information
            level_1_result: Level 1 (Resume) evaluation results
            level_2_result: Level 2 (GitHub) evaluation results
            level_3_result: Level 3 (Coding) evaluation results (optional)
            
        Returns:
            Dictionary containing final verdict with recommendation and reasoning
        """
        
        # Extract key information
        l1_score = level_1_result.get('score', 0)
        l1_max = level_1_result.get('max_score', 10)
        l1_passed = level_1_result.get('passed', False)
        l1_analysis = level_1_result.get('evaluation', '')
        
        l2_score = level_2_result.get('score', 0)
        l2_max = level_2_result.get('max_score', 10)
        l2_passed = level_2_result.get('passed', False)
        l2_analysis = level_2_result.get('analysis', '')
        
        # Build evaluation summary
        evaluations_summary = f"""
## EVALUATION SUMMARY

### Level 1: Resume Analysis
- Score: {l1_score}/{l1_max}
- Status: {'PASSED' if l1_passed else 'FAILED'}
- Threshold: {level_1_result.get('threshold', 7)}/{l1_max}

**Analysis:**
{l1_analysis[:1000]}...

### Level 2: GitHub Analysis  
- Score: {l2_score}/{l2_max}
- Status: {'PASSED' if l2_passed else 'FAILED'}
- Threshold: {level_2_result.get('threshold', 6)}/{l2_max}

**Analysis:**
{l2_analysis[:1000]}...
"""
        
        # Add Level 3 if available
        if level_3_result:
            l3_score = level_3_result.get('score', 0)
            l3_max = level_3_result.get('max_score', 10)
            l3_passed = level_3_result.get('passed', False)
            l3_analysis = level_3_result.get('analysis', '')
            
            evaluations_summary += f"""
### Level 3: Coding Assessment
- Score: {l3_score}/{l3_max}
- Status: {'PASSED' if l3_passed else 'FAILED'}
- Threshold: {level_3_result.get('threshold', 8)}/{l3_max}

**Analysis:**
{l3_analysis[:1000]}...
"""
        
        # Calculate composite score (weighted average)
        if level_3_result:
            # L1: 30%, L2: 30%, L3: 40%
            composite_score = (l1_score * 0.3) + (l2_score * 0.3) + (level_3_result.get('score', 0) * 0.4)
            total_levels = 3
        else:
            # L1: 50%, L2: 50%
            composite_score = (l1_score * 0.5) + (l2_score * 0.5)
            total_levels = 2
        
        # Build prompt for final verdict
        jd_text = jd_info.get('extracted_info', jd_info.get('raw_jd', ''))[:500]
        
        prompt = f"""
        As a senior hiring manager, review all evaluation data and provide a FINAL HIRING DECISION.
        
        **JOB REQUIREMENTS (Summary):**
        {jd_text}...
        
        {evaluations_summary}
        
        **COMPOSITE SCORE:** {composite_score:.1f}/10 (based on {total_levels} levels)
        
        Provide your final verdict in this format:
        
        ## FINAL VERDICT
        
        **DECISION: HIRE / NO HIRE**
        
        **CONFIDENCE: High / Medium / Low**
        
        **COMPOSITE SCORE: {composite_score:.1f}/10**
        
        ### KEY DECISION FACTORS
        
        **Strengths:**
        - [List top 3-5 strengths across all evaluations]
        
        **Concerns:**
        - [List top 3-5 concerns or gaps]
        
        ### DETAILED REASONING
        
        [Provide comprehensive reasoning that:
        1. Weighs all evaluation levels
        2. Explains how strengths/concerns impact the decision
        3. Considers overall fit for the role
        4. Addresses any critical factors]
        
        ### RECOMMENDATION SUMMARY
        
        [2-3 sentence summary of why you recommend HIRE or NO HIRE]
        
        ### NEXT STEPS
        
        **If HIRE:**
        - [Suggest interview rounds, additional assessments, or direct offer]
        
        **If NO HIRE:**
        - [Provide feedback and suggestions for candidate improvement]
        
        Be decisive, clear, and justify your recommendation with specific evidence from the evaluations.
        """
        
        # Execute ADK agent using async helper
        verdict_text = _run_async_safe(self._run_agent_async(self.verdict_agent, prompt))
        
        # Extract decision
        decision = self._extract_decision(verdict_text)
        confidence = self._extract_confidence(verdict_text)
        
        return {
            "decision": decision,  # "HIRE" or "NO_HIRE"
            "confidence": confidence,  # "High", "Medium", "Low"
            "composite_score": round(composite_score, 1),
            "level_1_score": l1_score,
            "level_2_score": l2_score,
            "level_3_score": level_3_result.get('score') if level_3_result else None,
            "all_levels_passed": l1_passed and l2_passed and (level_3_result.get('passed', True) if level_3_result else True),
            "verdict_text": verdict_text,
            "total_levels_evaluated": total_levels,
            "status": "final_verdict_generated"
        }
    
    def _extract_decision(self, verdict_text: str) -> str:
        """
        Extract HIRE/NO_HIRE decision from verdict text
        
        Args:
            verdict_text: The verdict response text
            
        Returns:
            "HIRE" or "NO_HIRE"
        """
        import re
        
        # Look for patterns like "DECISION: HIRE" or "DECISION: NO HIRE"
        patterns = [
            r'DECISION:\s*(HIRE|NO\s*HIRE|NO_HIRE)',
            r'RECOMMENDATION:\s*(HIRE|NO\s*HIRE|NO_HIRE)',
            r'FINAL\s+DECISION:\s*(HIRE|NO\s*HIRE|NO_HIRE)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, verdict_text, re.IGNORECASE)
            if match:
                decision = match.group(1).upper().replace(' ', '_')
                return "HIRE" if decision == "HIRE" else "NO_HIRE"
        
        # Default based on context
        if 'recommend hiring' in verdict_text.lower() or 'should be hired' in verdict_text.lower():
            return "HIRE"
        elif 'not recommend' in verdict_text.lower() or 'should not be hired' in verdict_text.lower():
            return "NO_HIRE"
        
        return "NO_HIRE"  # Conservative default
    
    def _extract_confidence(self, verdict_text: str) -> str:
        """
        Extract confidence level from verdict text
        
        Args:
            verdict_text: The verdict response text
            
        Returns:
            "High", "Medium", or "Low"
        """
        import re
        
        # Look for patterns like "CONFIDENCE: High"
        pattern = r'CONFIDENCE:\s*(High|Medium|Low)'
        match = re.search(pattern, verdict_text, re.IGNORECASE)
        
        if match:
            return match.group(1).capitalize()
        
        return "Medium"  # Default
