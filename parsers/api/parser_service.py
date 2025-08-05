"""
PDF Parser Service
Refactored parsing logic from multimodal/main.py for API use
"""

import logging
import os
# Import shared configuration and utilities
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))
from config import AZURE_CONFIG, FORMATTING_CONFIG
from pdf_utils import (add_page_numbers_to_content, cleanup_markdown,
                       extract_images_from_document,
                       extract_tables_from_document, validate_pdf_data)

# Load environment variables FIRST - from parent directory
load_dotenv(Path(__file__).parent.parent / '.env')

# ===== PYDANTIC MODELS =====
class ParseResult(BaseModel):
    """Result model for PDF parsing."""
    success: bool
    markdown: Optional[str] = None
    pages_processed: int = 0
    images_processed: int = 0
    tables_processed: int = 0
    text_length: int = 0
    azure_analysis: bool = False
    error: Optional[str] = None

class ParseConfig(BaseModel):
    """Configuration for individual parse requests."""
    images_inline: bool = True
    include_page_numbers: bool = True
    include_tables_section: bool = False
    include_images_section: bool = False
    cleanup_markdown: bool = True
    azure_analysis: bool = True

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFParserService:
    """
    PDF Parser Service for API use.
    Refactored from multimodal/main.py
    """
    
    def __init__(self):
        """Initialize the parser service."""
        
        # Configure pipeline for image extraction
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        
        # Initialize Docling
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        logger.info("✅ PDF parser service initialized")
        
        # Initialize Azure OpenAI if configured
        self.azure_client = None
        if AZURE_CONFIG["api_key"] and AZURE_CONFIG["endpoint"]:
            try:
                self.azure_client = AzureOpenAI(
                    api_key=AZURE_CONFIG["api_key"],
                    api_version=AZURE_CONFIG["api_version"],
                    azure_endpoint=AZURE_CONFIG["endpoint"]
                )
                logger.info("✅ Azure OpenAI client initialized")
            except Exception as e:
                logger.warning(f"❌ Azure OpenAI initialization failed: {e}")
        else:
            logger.info("📝 Azure config missing - parsing without image analysis")
    
    def create_enhanced_markdown(self, markdown_content: str, images: List[Dict[str, Any]], 
                               config: ParseConfig) -> str:
        """Create enhanced markdown with images."""
        enhanced_markdown = markdown_content
        
        # Handle inline images
        if config.images_inline and images:
            image_index = 0
            lines = enhanced_markdown.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == "<!-- image -->" and image_index < len(images):
                    image = images[image_index]
                    
                    image_title_template = FORMATTING_CONFIG["image_title_template"]
                    if image_title_template.strip():
                        image_title = image_title_template.format(image_num=image['index'] + 1)
                        lines[i] = f"\n{image_title}\n{image['description']}\n"
                    else:
                        lines[i] = f"\n{image['description']}\n"
                    image_index += 1
            enhanced_markdown = '\n'.join(lines)
        
        # Clean up if enabled
        if config.cleanup_markdown:
            enhanced_markdown = cleanup_markdown(enhanced_markdown)
        
        return enhanced_markdown
    
    def parse_pdf_from_bytes(self, pdf_data: bytes, filename: str = "document.pdf", 
                           config: Optional[ParseConfig] = None) -> ParseResult:
        """Parse PDF from bytes data."""
        if config is None:
            config = ParseConfig()
            
        try:
            # Validate PDF
            validate_pdf_data(pdf_data)
            
            # Create temporary file for Docling
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            try:
                # Convert PDF with Docling
                logger.info("Converting PDF to structured document...")
                result = self.doc_converter.convert(tmp_path)
                
                # Export to Markdown
                logger.info("Exporting to Markdown...")
                markdown_content = result.document.export_to_markdown()
                
                # Extract images and tables (use config to control processing)
                images = []
                if config.azure_analysis:
                    logger.info("Extracting and analyzing images...")
                    images = extract_images_from_document(result, self.azure_client, config.azure_analysis)
                
                logger.info("Extracting tables...")
                tables = extract_tables_from_document(result)
                
                # Add page numbers if enabled
                if config.include_page_numbers:
                    markdown_content = add_page_numbers_to_content(result, markdown_content)
                
                # Create enhanced markdown
                enhanced_markdown = self.create_enhanced_markdown(markdown_content, images, config)
                
                # Get stats
                pages_count = len(result.document.pages) if hasattr(result.document, 'pages') else 1
                
                return ParseResult(
                    success=True,
                    markdown=enhanced_markdown,
                    pages_processed=pages_count,
                    images_processed=len(images),
                    tables_processed=len(tables),
                    text_length=len(enhanced_markdown),
                    azure_analysis=self.azure_client is not None
                )
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                    logger.debug(f"✅ Cleaned up temporary file: {tmp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to clean up temporary file {tmp_path}: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return ParseResult(
                success=False,
                error=str(e)
            )
