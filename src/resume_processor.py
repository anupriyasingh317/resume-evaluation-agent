import os
import logging
from pathlib import Path
from typing import List, Optional
import PyPDF2
from docx import Document
import chardet

logger = logging.getLogger(__name__)

class ResumeProcessor:
    """Handles parsing of resume files (PDF, DOCX, TXT) to extract text content."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.doc'}
    
    def __init__(self, resume_directory: str):
        self.resume_directory = Path(resume_directory)
        if not self.resume_directory.exists():
            raise FileNotFoundError(f"Resume directory not found: {resume_directory}")
    
    def get_resume_files(self) -> List[Path]:
        """Get all supported resume files from the directory."""
        files = []
        for file_path in self.resume_directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(file_path)
        return sorted(files)
    
    def extract_text_from_pdf(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return None
    
    def extract_text_from_docx(self, file_path: Path) -> Optional[str]:
        """Extract text from DOCX file."""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error reading DOCX {file_path}: {e}")
            return None
    
    def extract_text_from_txt(self, file_path: Path) -> Optional[str]:
        """Extract text from TXT file with encoding detection."""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                encoding = chardet.detect(raw_data)['encoding']
                if encoding:
                    return raw_data.decode(encoding)
                else:
                    # Fallback to utf-8
                    return raw_data.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error reading TXT {file_path}: {e}")
            return None
    
    def extract_text(self, file_path: Path) -> Optional[str]:
        """Extract text from supported file types."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif extension == '.docx':
            return self.extract_text_from_docx(file_path)
        elif extension == '.txt':
            return self.extract_text_from_txt(file_path)
        elif extension == '.doc':
            # .doc files are not directly supported, would need additional library
            logger.warning(f"DOC format not supported: {file_path}")
            return None
        else:
            logger.error(f"Unsupported file format: {extension}")
            return None
    
    def process_all_resumes(self) -> dict:
        """Process all resume files and return dict of {filename: text}."""
        files = self.get_resume_files()
        results = {}
        
        for file_path in files:
            logger.info(f"Processing: {file_path.name}")
            text = self.extract_text(file_path)
            if text:
                results[file_path.name] = text
            else:
                logger.warning(f"Failed to extract text from: {file_path.name}")
        
        return results
    
    def process_single_resume(self, filename: str) -> Optional[str]:
        """Process a single resume file."""
        file_path = self.resume_directory / filename
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            return None
        
        return self.extract_text(file_path)
