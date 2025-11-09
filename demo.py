"""
Demo Script for Tech Hiring Agentic Framework
Demonstrates automated evaluation of sample candidates
"""

import warnings
# Suppress async cleanup warnings
warnings.filterwarnings('ignore', message='Event loop is closed')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*Event loop is closed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited.*')

import os
from dotenv import load_dotenv
from hiring_framework import HiringFramework


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def main():
    """Run automated demo with sample data"""
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found")
        print("Please set up your .env file with GOOGLE_API_KEY")
        return
    
    print_section("🚀 TECH HIRING AGENTIC FRAMEWORK - DEMO")
    print("This demo will evaluate 2 sample candidates using Google ADK\n")
    
    # Initialize framework
    print("Initializing framework...")
    framework = HiringFramework(api_key=api_key)
    
    # ==================== STEP 1: Process JD ====================
    
    print_section("STEP 1: JOB DESCRIPTION PROCESSING")
    
    jd_file = "examples/sample_jd.txt"
    print(f"📄 Loading Job Description from: {jd_file}")
    
    step1_result = framework.complete_step_1_workflow(jd_file_path=jd_file)
    
    input("\n⏸️  Press Enter to continue to resume evaluations...")
    
    # ==================== STEP 2: Evaluate Resumes ====================
    
    resumes = [
        ("examples/sample_resume_1.txt", "John Doe - Senior Python Developer"),
        ("examples/sample_resume_2.txt", "Jane Smith - Junior Developer")
    ]
    
    evaluations = []
    
    for resume_file, candidate_name in resumes:
        print_section(f"EVALUATING: {candidate_name}")
        
        print(f"📄 Loading resume from: {resume_file}")
        
        evaluation = framework.complete_step_2_workflow(resume_file_path=resume_file)
        evaluations.append({
            "name": candidate_name,
            "evaluation": evaluation
        })
        
        input("\n⏸️  Press Enter to continue...")
    
    # ==================== FINAL SUMMARY ====================
    
    print_section("📊 FINAL EVALUATION SUMMARY")
    
    print("Candidate Comparison:")
    print("-" * 80)
    
    for result in evaluations:
        name = result['name']
        eval_data = result['evaluation']
        score = eval_data['score']
        passed = eval_data['passed']
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        
        print(f"\n{name}")
        print(f"  Score: {score}/10")
        print(f"  Status: {status}")
        print(f"  Threshold: {eval_data['threshold']}/10")
        
        if passed:
            print(f"  → Proceed to Level 2 (GitHub Analysis)")
        else:
            print(f"  → Does not meet minimum requirements")
    
    print("\n" + "-" * 80)
    
    # Full report
    print("\n" + "=" * 80)
    print("DETAILED EVALUATION REPORT")
    print("=" * 80)
    
    report = framework.get_evaluation_report()
    print(report)
    
    print_section("✅ DEMO COMPLETED")
    
    print("Key Takeaways:")
    print("  • Step 1: Job Description processing and rubric generation")
    print("  • Step 2: Automated Level 1 resume evaluation")
    print("  • Candidates scoring ≥7/10 qualify for Level 2")
    print("\nNext Steps:")
    print("  • Implement Level 2: GitHub profile analysis")
    print("  • Implement Level 3: Overall assessment and work ethics")
    print("  • Add web interface for easier interaction")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
