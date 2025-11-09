"""
Demo Script: Complete Hiring Workflow with Final Verdict
Demonstrates Steps 1-5: JD Processing → Resume Evaluation → GitHub Analysis → Final Verdict
"""

import warnings
warnings.filterwarnings('ignore')

import os
from dotenv import load_dotenv
from hiring_framework import HiringFramework

# Load environment
load_dotenv()

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80 + "\n")


def main():
    """Run complete hiring workflow demo"""
    
    print_header("🚀 TECH HIRING AGENTIC FRAMEWORK - COMPLETE WORKFLOW DEMO")
    
    # Initialize framework
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found!")
        return
    
    framework = HiringFramework(api_key=api_key)
    
    # Sample Job Description
    jd_text = """
    Senior Python Developer
    
    We're looking for an experienced Python developer to join our team.
    
    Requirements:
    - 5+ years of Python development experience
    - Strong experience with Django or Flask
    - Experience with PostgreSQL and database design
    - Knowledge of Docker and containerization
    - Experience with Git and CI/CD pipelines
    - Strong problem-solving skills
    - Experience with RESTful API design
    
    Nice to have:
    - Experience with React or Vue.js
    - AWS or cloud platform experience
    - Open source contributions
    """
    
    # Sample Resume
    resume_text = """
    JOHN DOE
    Email: john.doe@example.com
    GitHub: johndoe
    
    EXPERIENCE
    
    Senior Python Developer | TechCorp Inc.
    2018 - Present (6 years)
    - Developed scalable web applications using Django and PostgreSQL
    - Led migration of monolithic application to microservices architecture
    - Implemented CI/CD pipelines using GitLab and Docker
    - Mentored junior developers and conducted code reviews
    
    Python Developer | StartupXYZ
    2015 - 2018 (3 years)
    - Built RESTful APIs using Flask
    - Integrated payment gateways and third-party services
    - Optimized database queries improving performance by 40%
    
    SKILLS
    - Python, Django, Flask, FastAPI
    - PostgreSQL, MySQL, Redis
    - Docker, Kubernetes
    - Git, CI/CD, Jenkins
    - React (basic knowledge)
    - AWS (EC2, S3, RDS)
    
    EDUCATION
    B.S. Computer Science | State University | 2015
    
    PROJECTS
    - Open source contributor to Django REST Framework
    - Created Python library for data validation (500+ GitHub stars)
    """
    
    # GitHub URL
    github_url = "johndoe"  # Sample GitHub username
    
    try:
        # ==================== STEP 1: Process JD ====================
        print_header("STEP 1: JOB DESCRIPTION PROCESSING & RUBRIC GENERATION")
        
        jd_info = framework.process_jd(jd_text=jd_text)
        print("✓ Job Description processed")
        
        rubric_data = framework.generate_rubric()
        print("✓ Rubric generated")
        
        print("\n" + "-" * 80)
        print("GENERATED RUBRIC:")
        print("-" * 80)
        print(framework.current_rubric[:500] + "...\n")
        
        # ==================== STEP 2: Resume Evaluation ====================
        print_header("STEP 2: RESUME EVALUATION - LEVEL 1")
        
        level_1_result = framework.evaluate_resume_level_1(resume_text=resume_text)
        
        print(f"\n📊 LEVEL 1 SCORE: {level_1_result['score']}/{level_1_result['max_score']}")
        print(f"🎯 Threshold: {level_1_result['threshold']}/10")
        print(f"✅ Status: {'PASSED' if level_1_result['passed'] else 'FAILED'}\n")
        
        if not level_1_result['passed']:
            print("❌ Candidate failed Level 1. Cannot proceed to Level 2.")
            return
        
        # ==================== STEP 3: GitHub Analysis ====================
        print_header("STEP 3: GITHUB ANALYSIS - LEVEL 2")
        
        level_2_result = framework.analyze_github(github_url=github_url)
        
        print(f"\n📊 LEVEL 2 SCORE: {level_2_result['score']}/{level_2_result['max_score']}")
        print(f"🎯 Threshold: {level_2_result['threshold']}/10")
        print(f"✅ Status: {'PASSED' if level_2_result['passed'] else 'FAILED'}\n")
        
        # ==================== STEP 5: Final Verdict ====================
        print_header("STEP 5: FINAL VERDICT - HIRING DECISION")
        
        final_verdict = framework.complete_step_5_workflow()
        
        # ==================== Summary ====================
        print_header("📋 EVALUATION SUMMARY")
        
        print(f"Candidate: John Doe")
        print(f"Position: Senior Python Developer\n")
        
        print(f"Level 1 (Resume): {level_1_result['score']}/10 - {'✓ PASSED' if level_1_result['passed'] else '✗ FAILED'}")
        print(f"Level 2 (GitHub): {level_2_result['score']}/10 - {'✓ PASSED' if level_2_result['passed'] else '✗ FAILED'}")
        print(f"\nComposite Score: {final_verdict['composite_score']}/10")
        print(f"Confidence: {final_verdict['confidence']}")
        print(f"\n{'🎉' if final_verdict['decision'] == 'HIRE' else '⚠️'} FINAL DECISION: {final_verdict['decision']}")
        
        print("\n" + "=" * 80)
        print("✅ Complete workflow executed successfully!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
