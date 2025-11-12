"""
Main Hiring Framework Orchestrator
Coordinates the multi-level evaluation process using Google ADK agents
"""

from typing import Dict, Any, Optional
from agents import JobDescriptionProcessorAgent, ResumeEvaluatorAgent, GitHubAnalyzerAgent, FinalVerdictAgent
from utils import TextExtractor
import json


class HiringFramework:
    """
    Main orchestrator for the Tech Hiring Agentic Framework
    Implements Steps 1, 2, and 3 of the evaluation pipeline
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the hiring framework with Google ADK agents"""
        self.jd_agent = JobDescriptionProcessorAgent(api_key=api_key)
        self.resume_agent = ResumeEvaluatorAgent(api_key=api_key)
        self.github_agent = GitHubAnalyzerAgent(api_key=api_key)
        self.verdict_agent = FinalVerdictAgent(api_key=api_key)
        self.text_extractor = TextExtractor()
        
        # State management
        self.current_jd = None
        self.current_rubric = None
        self.evaluation_results = []
        
        # Track latest evaluations for final verdict
        self.latest_level_1 = None
        self.latest_level_2 = None
        self.latest_level_3 = None
        self.latest_final_verdict = None
    
    # ==================== STEP 1: JD Processing ====================
    
    def process_jd(self, jd_text: str = None, jd_file_path: str = None) -> Dict[str, Any]:
        """
        Step 1.1: Process Job Description and extract requirements
        
        Args:
            jd_text: Raw JD text
            jd_file_path: Path to JD file
            
        Returns:
            Extracted JD information
        """
        if jd_file_path:
            jd_text = self.text_extractor.extract_text(file_path=jd_file_path)
        
        if not jd_text:
            raise ValueError("Either jd_text or jd_file_path must be provided")
        
        print("📄 Processing Job Description...")
        self.current_jd = self.jd_agent.extract_jd_requirements(jd_text)
        print("✓ Job Description processed successfully\n")
        
        return self.current_jd
    
    def generate_rubric(self) -> Dict[str, Any]:
        """
        Step 1.2: Generate evaluation rubric based on JD
        
        Returns:
            Generated rubric
        """
        if not self.current_jd:
            raise ValueError("Job Description must be processed first. Call process_jd()")
        
        print("📋 Generating evaluation rubric...")
        rubric_data = self.jd_agent.generate_rubric(self.current_jd)
        self.current_rubric = rubric_data['rubric']
        print("✓ Rubric generated successfully\n")
        
        return rubric_data
    
    def refine_rubric_with_feedback(self, user_feedback: str) -> Dict[str, Any]:
        """
        Step 1.3: Refine rubric based on user feedback
        
        Args:
            user_feedback: User's feedback on the rubric
            
        Returns:
            Refined rubric
        """
        if not self.current_rubric:
            raise ValueError("Rubric must be generated first. Call generate_rubric()")
        
        print("🔄 Refining rubric based on feedback...")
        refined = self.jd_agent.refine_rubric(self.current_rubric, user_feedback)
        self.current_rubric = refined['rubric']
        print("✓ Rubric refined successfully\n")
        
        return refined
    
    # ==================== STEP 2: Resume Evaluation ====================
    
    def evaluate_resume_level_1(
        self, 
        resume_text: str = None, 
        resume_file_path: str = None
    ) -> Dict[str, Any]:
        """
        Step 2: Evaluate resume at Level 1 (Resume vs JD comparison)
        
        Args:
            resume_text: Raw resume text
            resume_file_path: Path to resume file
            
        Returns:
            Level 1 evaluation results
        """
        if not self.current_jd or not self.current_rubric:
            raise ValueError(
                "Job Description and Rubric must be set up first. "
                "Call process_jd() and generate_rubric()"
            )
        
        # Extract resume text if file path provided
        if resume_file_path:
            print(f"📄 Extracting text from resume: {resume_file_path}")
            resume_text = self.text_extractor.extract_text(file_path=resume_file_path)
        
        if not resume_text:
            raise ValueError("Either resume_text or resume_file_path must be provided")
        
        # Extract structured resume information
        print("🔍 Analyzing resume...")
        resume_info = self.resume_agent.extract_resume_text(resume_text)
        
        # Perform Level 1 evaluation
        print("⚖️  Evaluating against Job Description (Level 1)...")
        evaluation = self.resume_agent.evaluate_level_1(
            resume_info=resume_info,
            jd_info=self.current_jd,
            rubric=self.current_rubric
        )
        
        # Store evaluation result
        self.evaluation_results.append(evaluation)
        self.latest_level_1 = evaluation
        
        print("✓ Level 1 Evaluation completed\n")
        
        return evaluation
    
    # ==================== Workflow Methods ====================
    
    def complete_step_1_workflow(
        self, 
        jd_text: str = None, 
        jd_file_path: str = None,
        auto_approve_rubric: bool = False
    ) -> Dict[str, Any]:
        """
        Complete Step 1 workflow: JD processing and rubric generation
        
        Args:
            jd_text: Raw JD text
            jd_file_path: Path to JD file
            auto_approve_rubric: If True, skip user feedback
            
        Returns:
            Complete Step 1 results
        """
        print("=" * 60)
        print("STEP 1: JOB DESCRIPTION PROCESSING & RUBRIC GENERATION")
        print("=" * 60 + "\n")
        
        # Process JD
        jd_info = self.process_jd(jd_text=jd_text, jd_file_path=jd_file_path)
        
        # Generate rubric
        rubric_data = self.generate_rubric()
        
        print("─" * 60)
        print("GENERATED RUBRIC:")
        print("─" * 60)
        print(self.current_rubric)
        print("─" * 60 + "\n")
        
        return {
            "jd_info": jd_info,
            "rubric": rubric_data,
            "status": "step_1_completed"
        }
    
    def complete_step_2_workflow(
        self, 
        resume_text: str = None, 
        resume_file_path: str = None
    ) -> Dict[str, Any]:
        """
        Complete Step 2 workflow: Resume evaluation Level 1
        
        Args:
            resume_text: Raw resume text
            resume_file_path: Path to resume file
            
        Returns:
            Complete Step 2 results
        """
        print("=" * 60)
        print("STEP 2: RESUME EVALUATION - LEVEL 1")
        print("=" * 60 + "\n")
        
        # Evaluate resume
        evaluation = self.evaluate_resume_level_1(
            resume_text=resume_text,
            resume_file_path=resume_file_path
        )
        
        # Display results
        summary = self.resume_agent.get_evaluation_summary(evaluation)
        print(summary)
        
        # Check if passed threshold
        if evaluation['passed']:
            print("✅ Candidate PASSED Level 1 - Eligible for Level 2 evaluation")
        else:
            print("❌ Candidate FAILED Level 1 - Does not meet minimum requirements")
        
        print("\n" + "=" * 60)
        
        return evaluation
    
    def get_evaluation_report(self) -> str:
        """
        Generate a comprehensive evaluation report
        
        Returns:
            Formatted evaluation report
        """
        if not self.evaluation_results:
            return "No evaluations performed yet."
        
        report = "\n" + "=" * 60 + "\n"
        report += "EVALUATION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        for idx, result in enumerate(self.evaluation_results, 1):
            report += f"Candidate #{idx}\n"
            report += f"Level: {result['level']}\n"
            report += f"Score: {result['score']}/{result['max_score']}\n"
            report += f"Passed: {'Yes' if result['passed'] else 'No'}\n"
            report += f"Threshold: {result['threshold']}\n"
            report += "─" * 60 + "\n"
            report += result['evaluation'] + "\n"
            report += "=" * 60 + "\n\n"
        
        return report
    
    # ==================== LEVEL 2: GitHub Analysis ====================
    
    def analyze_github(self, github_url: str) -> Dict[str, Any]:
        """
        Level 2: Analyze GitHub profile/repositories
        
        Args:
            github_url: GitHub profile URL or username
            
        Returns:
            GitHub analysis results
        """
        if not self.current_jd:
            raise ValueError("Must process JD first (Step 1) before GitHub analysis")
        
        print("🔍 Analyzing GitHub profile...")
        
        # Perform GitHub analysis
        result = self.github_agent.analyze_github_profile(
            github_url=github_url,
            jd_info=self.current_jd
        )
        
        # Store result
        self.evaluation_results.append(result)
        self.latest_level_2 = result
        
        print("✓ GitHub analysis completed\n")
        
        return result
    
    # ==================== STEP 5: Final Verdict ====================
    
    def generate_final_verdict(
        self,
        level_1_result: Dict[str, Any] = None,
        level_2_result: Dict[str, Any] = None,
        level_3_result: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Step 5: Generate final hiring verdict combining all evaluation levels
        
        Args:
            level_1_result: Level 1 (Resume) evaluation results (uses latest if None)
            level_2_result: Level 2 (GitHub) evaluation results (uses latest if None)
            level_3_result: Level 3 (Coding) evaluation results (optional)
            
        Returns:
            Final verdict with hiring recommendation
        """
        if not self.current_jd:
            raise ValueError("Job Description must be processed first")
        
        # Use provided results or latest stored results
        l1_result = level_1_result or self.latest_level_1
        l2_result = level_2_result or self.latest_level_2
        l3_result = level_3_result or self.latest_level_3
        
        if not l1_result:
            raise ValueError("Level 1 (Resume) evaluation must be completed first")
        if not l2_result:
            raise ValueError("Level 2 (GitHub) evaluation must be completed first")
        
        print("🎯 Generating Final Verdict...")
        
        # Generate comprehensive final verdict
        verdict = self.verdict_agent.generate_final_verdict(
            jd_info=self.current_jd,
            level_1_result=l1_result,
            level_2_result=l2_result,
            level_3_result=l3_result
        )
        
        # Store final verdict
        self.latest_final_verdict = verdict
        self.evaluation_results.append(verdict)
        
        print("✓ Final Verdict generated\n")
        
        return verdict
    
    def complete_step_5_workflow(self) -> Dict[str, Any]:
        """
        Complete Step 5 workflow: Generate final hiring verdict
        
        Returns:
            Complete Step 5 results with final verdict
        """
        print("=" * 60)
        print("STEP 5: FINAL VERDICT - HIRING DECISION")
        print("=" * 60 + "\n")
        
        # Generate final verdict
        verdict = self.generate_final_verdict()
        
        # Display results
        self._display_final_verdict(verdict)
        
        print("\n" + "=" * 60)
        
        return verdict
    
    def _display_final_verdict(self, verdict: Dict[str, Any]):
        """Display final verdict in a formatted way"""
        decision = verdict.get('decision', 'NO_HIRE')
        confidence = verdict.get('confidence', 'Medium')
        composite_score = verdict.get('composite_score', 0)
        
        # Visual formatting
        if decision == "HIRE":
            decision_emoji = "✅"
            decision_color = "HIRE"
        else:
            decision_emoji = "❌"
            decision_color = "NO HIRE"
        
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 18 + "FINAL VERDICT" + " " * 27 + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║  {decision_emoji} DECISION: {decision_color}" + " " * (48 - len(decision_color)) + "║")
        print(f"║  📊 COMPOSITE SCORE: {composite_score}/10" + " " * (39 - len(str(composite_score))) + "║")
        print(f"║  🎯 CONFIDENCE: {confidence}" + " " * (44 - len(confidence)) + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║  L1 (Resume): {verdict.get('level_1_score', 0)}/10" + " " * 39 + "║")
        print(f"║  L2 (GitHub): {verdict.get('level_2_score', 0)}/10" + " " * 39 + "║")
        if verdict.get('level_3_score') is not None:
            print(f"║  L3 (Coding): {verdict.get('level_3_score', 0)}/10" + " " * 39 + "║")
        print("╚" + "═" * 58 + "╝")
        print()
        print(verdict.get('verdict_text', ''))
    
    def reset(self):
        """Reset the framework state"""
        self.current_jd = None
        self.current_rubric = None
        self.evaluation_results = []
        self.latest_level_1 = None
        self.latest_level_2 = None
        self.latest_level_3 = None
        self.latest_final_verdict = None
        print("✓ Framework state reset")
