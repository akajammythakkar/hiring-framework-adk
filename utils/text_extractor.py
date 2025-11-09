"""
Text extraction utilities for various document formats
"""

import PyPDF2
from typing import Optional
import io


class TextExtractor:
    """Utility class for extracting text from various document formats"""
    
    @staticmethod
    def extract_from_pdf(file_path: str = None, file_bytes: bytes = None) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            file_bytes: Bytes content of PDF file
            
        Returns:
            Extracted text content
        """
        try:
            if file_path:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
            
            elif file_bytes:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
            
            else:
                raise ValueError("Either file_path or file_bytes must be provided")
                
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    @staticmethod
    def extract_from_text(file_path: str = None, file_bytes: bytes = None) -> str:
        """
        Extract text from plain text file
        
        Args:
            file_path: Path to text file
            file_bytes: Bytes content of text file
            
        Returns:
            Text content
        """
        try:
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            elif file_bytes:
                return file_bytes.decode('utf-8')
            
            else:
                raise ValueError("Either file_path or file_bytes must be provided")
                
        except Exception as e:
            raise Exception(f"Error extracting text: {str(e)}")
    
    @staticmethod
    def extract_text(file_path: str = None, file_bytes: bytes = None, 
                     file_extension: str = None) -> str:
        """
        Auto-detect and extract text from file
        
        Args:
            file_path: Path to file
            file_bytes: Bytes content of file
            file_extension: File extension (e.g., '.pdf', '.txt')
            
        Returns:
            Extracted text content
        """
        if not file_extension and file_path:
            file_extension = file_path.split('.')[-1].lower()
        
        file_extension = file_extension.lower().strip('.')
        
        if file_extension == 'pdf':
            return TextExtractor.extract_from_pdf(file_path, file_bytes)
        elif file_extension in ['txt', 'text']:
            return TextExtractor.extract_from_text(file_path, file_bytes)
        else:
            # Try as text first, then PDF
            try:
                return TextExtractor.extract_from_text(file_path, file_bytes)
            except:
                return TextExtractor.extract_from_pdf(file_path, file_bytes)
