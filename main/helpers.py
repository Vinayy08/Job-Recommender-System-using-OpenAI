import os
import logging
from docx import Document
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

def preprocess_text(text):
    """Preprocess text by stripping whitespace and converting to lowercase."""
    try:
        return text.strip().lower() if text else ""
    except Exception as e:
        logger.error(f"Error preprocessing text: {e}")
        return ""

def extract_text_from_file(file_path):
    """Extract text from supported file types."""
    if file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.txt'):
        return extract_text_from_txt(file_path)
    else:
        logger.warning(f"Unsupported file format: {file_path}")
        return ""

def extract_text_from_docx(file_path):
    """Extract text from .docx files."""
    try:
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        logger.error(f"Error reading .docx file {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path):
    """Extract text from .pdf files."""
    try:
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        logger.error(f"Error reading .pdf file {file_path}: {e}")
        return ""

def extract_text_from_txt(file_path):
    """Extract text from .txt files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading .txt file {file_path}: {e}")
        return ""
