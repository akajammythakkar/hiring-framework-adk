"""
Configuration file for Tech Hiring Framework
Allows customization of evaluation thresholds and parameters
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Framework configuration"""
    
    # API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Evaluation Thresholds (out of 10)
    LEVEL_1_THRESHOLD = float(os.getenv("LEVEL_1_THRESHOLD", "7.0"))
    LEVEL_2_THRESHOLD = float(os.getenv("LEVEL_2_THRESHOLD", "6.0"))
    LEVEL_3_THRESHOLD = float(os.getenv("LEVEL_3_THRESHOLD", "8.0"))
    
    # Scoring Scales
    LEVEL_1_MAX_SCORE = 10
    LEVEL_2_MAX_SCORE = 10
    LEVEL_3_MAX_SCORE = 10
    
    # Model Configuration
    MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash-exp")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    @classmethod
    def get_threshold(cls, level: int) -> float:
        """Get threshold for a specific level"""
        thresholds = {
            1: cls.LEVEL_1_THRESHOLD,
            2: cls.LEVEL_2_THRESHOLD,
            3: cls.LEVEL_3_THRESHOLD
        }
        return thresholds.get(level, 7.0)
    
    @classmethod
    def set_threshold(cls, level: int, value: float):
        """Set threshold for a specific level"""
        if level == 1:
            cls.LEVEL_1_THRESHOLD = value
        elif level == 2:
            cls.LEVEL_2_THRESHOLD = value
        elif level == 3:
            cls.LEVEL_3_THRESHOLD = value


# Create default config instance
config = Config()
