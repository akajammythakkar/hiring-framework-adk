"""
Main CLI Application for Tech Hiring Agentic Framework
Demonstrates Steps 1 and 2 of the evaluation pipeline
"""

import warnings
# Suppress async cleanup warnings
warnings.filterwarnings('ignore', message='Event loop is closed')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*Event loop is closed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited.*')

import os
from dotenv import load_dotenv
from hiring_framework import HiringFramework
import sys


def print_header():
    """Print application header"""
    print("\n" + "=" * 70)
    print(" " * 15 + "TECH HIRING AGENTIC FRAMEWORK")
    print(" " * 20 + "Powered by Google ADK")
    print("=" * 70 + "\n")


def get_user_input(prompt: str, required: bool = True) -> str:
    """Get user input with validation"""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("❌ This field is required. Please try again.")


def confirm_action(prompt: str) -> bool:
    """Get user confirmation"""
    response = input(f"{prompt} (y/n): ").strip().lower()
    return response in ['y', 'yes']


def main():
    """Main application entry point"""
    
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment variables")
        print("\nPlease:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google API key to the .env file")
        print("3. Run the application again")
        sys.exit(1)
    
    print_header()
    
    # Initialize framework
    print("🚀 Initializing Hiring Framework with Google ADK...\n")
    framework = HiringFramework(api_key=api_key)
    
    try:
        # ==================== STEP 1: JD Processing ====================
        print("\n" + "▓" * 70)
        print("STEP 1: JOB DESCRIPTION PROCESSING")
        print("▓" * 70 + "\n")
        
        # Get JD input
        print("Please provide the Job Description:")
        print("1. Enter text directly")
        print("2. Provide file path")
        
        choice = get_user_input("\nSelect option (1/2): ")
        
        jd_text = None
        jd_file_path = None
        
        if choice == "1":
            print("\nEnter Job Description (press Ctrl+D or Ctrl+Z when done):")
            try:
                jd_text = sys.stdin.read()
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled")
                return
        else:
            jd_file_path = get_user_input("Enter path to JD file: ")
            if not os.path.exists(jd_file_path):
                print(f"❌ File not found: {jd_file_path}")
                return
        
        # Process JD and generate rubric
        step1_result = framework.complete_step_1_workflow(
            jd_text=jd_text,
            jd_file_path=jd_file_path
        )
        
        # Ask for rubric feedback
        if confirm_action("\n📝 Would you like to refine the rubric?"):
            feedback = get_user_input("Enter your feedback: ")
            framework.refine_rubric_with_feedback(feedback)
            print("\n─" * 70)
            print("REFINED RUBRIC:")
            print("─" * 70)
            print(framework.current_rubric)
            print("─" * 70 + "\n")
        
        print("\n✅ Step 1 completed successfully!\n")
        
        # ==================== STEP 2: Resume Evaluation ====================
        
        if not confirm_action("📋 Ready to evaluate resumes?"):
            print("\n👋 Exiting application. Run again when ready.")
            return
        
        # Evaluate multiple resumes
        while True:
            print("\n" + "▓" * 70)
            print("STEP 2: RESUME EVALUATION - LEVEL 1")
            print("▓" * 70 + "\n")
            
            # Get resume input
            print("Please provide the candidate's resume:")
            print("1. Enter text directly")
            print("2. Provide file path")
            
            choice = get_user_input("\nSelect option (1/2): ")
            
            resume_text = None
            resume_file_path = None
            
            if choice == "1":
                print("\nEnter Resume (press Ctrl+D or Ctrl+Z when done):")
                try:
                    resume_text = sys.stdin.read()
                except KeyboardInterrupt:
                    print("\n❌ Operation cancelled")
                    break
            else:
                resume_file_path = get_user_input("Enter path to resume file: ")
                if not os.path.exists(resume_file_path):
                    print(f"❌ File not found: {resume_file_path}")
                    continue
            
            # Evaluate resume
            evaluation = framework.complete_step_2_workflow(
                resume_text=resume_text,
                resume_file_path=resume_file_path
            )
            
            # Ask to evaluate more resumes
            if not confirm_action("\n🔄 Evaluate another resume?"):
                break
        
        # ==================== Final Report ====================
        
        print("\n" + "▓" * 70)
        print("EVALUATION SUMMARY")
        print("▓" * 70)
        
        report = framework.get_evaluation_report()
        print(report)
        
        print("\n✅ All evaluations completed!")
        print("\n💡 Next Steps:")
        print("   - Candidates who scored ≥7/10 can proceed to Level 2 (GitHub analysis)")
        print("   - Level 2 and Level 3 will be implemented in future versions")
        
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "=" * 70)
        print("Thank you for using Tech Hiring Agentic Framework!")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
