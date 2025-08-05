"""
PDF Parser Service
Refactored parsing logic from multimodal/main.py for API use
"""

import base64
import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# ===== PYDANTIC MODELS =====
class ImageAnalysis(BaseModel):
    """Structured model for image analysis results."""
    text_content: Optional[str] = Field(None, description="Any readable text, titles, labels, or captions found in the image")
    data_numbers: Optional[str] = Field(None, description="Key statistics, values, or quantitative information visible")
    subject_matter: str = Field(..., description="Brief description of the main topic or concept depicted")

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

# ===== CONFIGURATION =====
class ParserConfig:
    """Configuration for PDF parser."""
    
    # Azure OpenAI Configuration
    AZURE_CONFIG = {
        "api_key": os.getenv("AZURE_API_KEY"),
        "endpoint": os.getenv("AZURE_API_BASE"), 
        "deployment_name": "gpt-4.1",
        "api_version": "2024-10-01-preview"
    }

    # Processing Configuration  
    PROCESSING_CONFIG = {
        "process_images": True,
        "max_image_size": 20*1024*1024,  # 20MB
        "max_pdf_size": 100*1024*1024,  # 100MB
        "supported_formats": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"],
        "images_inline": True,
        "image_analysis_prompt": """Analyze this image for document search. Identify relevant content for each category:

- text_content: Only include if readable text, titles, labels, or captions are visible (exclude irrelevant details like classroom exercises)
- data_numbers: Only include if meaningful statistics, values, or quantitative information are present  
- subject_matter: Brief description of the main topic or concept

Be concise and focus on information useful for document search and retrieval."""
    }

    # Output Configuration
    OUTPUT_CONFIG = {
        "include_page_numbers": True,
        "include_tables_section": False,
        "include_images_section": False,
        "cleanup_markdown": True,
    }

    # Markdown Formatting Configuration
    FORMATTING_CONFIG = {
        "page_marker_template": "--- Page {page_num} ---",
        "page_placeholder": "___PAGE_BREAK_MARKER___",
        "image_wrapper_start": "<image>",
        "image_wrapper_end": "</image>",
        "image_title_template": "**Image {image_num}:**",
        "image_header_template": "### Image {image_num}",
        "table_header_template": "### Table {table_num}",
        "table_size_template": "**Size:** {rows} rows × {cols} columns",
        "images_section_header": "## 🖼️ Images and Figures",
        "tables_section_header": "## 📊 Tables",
        "max_consecutive_linebreaks": 2,
        "preserve_code_blocks": True,
        "normalize_whitespace": True,
        "fix_heading_spacing": True,
    }

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFParserService:
    """
    PDF Parser Service for API use.
    Refactored from multimodal/main.py
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize the parser service."""
        self.config = config or ParserConfig()
        
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
        if self.config.AZURE_CONFIG["api_key"] and self.config.AZURE_CONFIG["endpoint"]:
            try:
                self.azure_client = AzureOpenAI(
                    api_key=self.config.AZURE_CONFIG["api_key"],
                    api_version=self.config.AZURE_CONFIG["api_version"],
                    azure_endpoint=self.config.AZURE_CONFIG["endpoint"]
                )
                logger.info("✅ Azure OpenAI client initialized")
            except Exception as e:
                logger.warning(f"❌ Azure OpenAI initialization failed: {e}")
        else:
            logger.info("📝 Azure config missing - parsing without image analysis")
    
    def validate_pdf(self, pdf_data: bytes) -> bool:
        """Validate PDF data."""
        try:
            # Check file size
            file_size = len(pdf_data)
            max_size = self.config.PROCESSING_CONFIG["max_pdf_size"]
            if file_size > max_size:
                raise ValueError(f"File too large: {file_size:,} bytes (max: {max_size:,} bytes)")
            
            # Check PDF header
            if pdf_data[:5] != b'%PDF-':
                raise ValueError("Not a valid PDF file - missing PDF header")
            
            logger.info(f"✅ PDF validation passed: {file_size:,} bytes")
            return True
            
        except Exception as e:
            logger.error(f"❌ PDF validation failed: {e}")
            raise
    
    def encode_image_to_base64(self, image_data: bytes) -> str:
        """Encode image bytes to base64."""
        try:
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            return ""
    
    def analyze_image_with_azure(self, image_data: bytes, image_info: str = "") -> str:
        """Analyze image using Azure OpenAI."""
        if not self.azure_client:
            return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}{image_info}{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                base64_image = self.encode_image_to_base64(image_data)
                if not base64_image:
                    return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Failed to encode{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
                
                response = self.azure_client.beta.chat.completions.parse(
                    model=self.config.AZURE_CONFIG["deployment_name"],
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert document analyst. Extract key factual information from images for use in search and retrieval systems."
                        },
                        {
                            "role": "user", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.config.PROCESSING_CONFIG["image_analysis_prompt"]
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    response_format=ImageAnalysis,
                    max_tokens=500,
                    temperature=0.1
                )
                
                analysis = response.choices[0].message.parsed
                if not analysis:
                    return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}{image_info} - No analysis generated{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
                
                # Format the structured output
                formatted_parts = []
                if analysis.text_content:
                    formatted_parts.append(f"Text content: {analysis.text_content}")
                if analysis.data_numbers:
                    formatted_parts.append(f"Data/Numbers: {analysis.data_numbers}")
                formatted_parts.append(f"Subject matter: {analysis.subject_matter}")
                
                formatted_description = "\n".join(formatted_parts)
                return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}\n{formatted_description}\n{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Azure API attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Azure API failed after {max_retries} attempts: {e}")
                    return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Analysis failed{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
        
        return f"{self.config.FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Unexpected error{self.config.FORMATTING_CONFIG['image_wrapper_end']}"
    
    def extract_images_from_document(self, docling_result, config: ParseConfig) -> List[Dict[str, Any]]:
        """Extract images from Docling document result."""
        images = []
        
        try:
            if hasattr(docling_result.document, 'pictures') and docling_result.document.pictures:
                for i, picture in enumerate(docling_result.document.pictures):
                    try:
                        # Get image data
                        image_data = None
                        if hasattr(picture, 'get_image') and callable(picture.get_image):
                            try:
                                pil_image = picture.get_image(docling_result.document)
                                if pil_image:
                                    from PIL import Image
                                    if isinstance(pil_image, Image.Image):
                                        buffer = io.BytesIO()
                                        pil_image.save(buffer, format='PNG')
                                        image_data = buffer.getvalue()
                            except Exception as e:
                                logger.warning(f"Error getting image {i}: {e}")
                        
                        # Get image info
                        image_info = {
                            "index": i,
                            "caption": getattr(picture, 'caption', ''),
                            "page": getattr(picture, 'page', 'unknown'),
                            "has_data": image_data is not None
                        }
                        
                        # Analyze image if data available and Azure analysis enabled
                        if image_data and config.azure_analysis:
                            description = self.analyze_image_with_azure(
                                image_data, 
                                f"Image {i+1} from page {image_info['page']}"
                            )
                            image_info["description"] = description
                        else:
                            image_info["description"] = f"[Image {i+1}: {image_info['caption'] or 'No caption'}]"
                        
                        images.append(image_info)
                        
                    except Exception as e:
                        logger.error(f"Error processing image {i}: {e}")
                        images.append({
                            "index": i,
                            "description": f"[Image {i+1}: Processing failed]",
                            "error": str(e)
                        })
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
        
        logger.info(f"Total images extracted: {len(images)}")
        return images
    
    def extract_tables_from_document(self, docling_result) -> List[Dict[str, Any]]:
        """Extract tables from Docling document result."""
        tables = []
        
        try:
            if hasattr(docling_result.document, 'tables') and docling_result.document.tables:
                for i, table in enumerate(docling_result.document.tables):
                    try:
                        table_info = {
                            "index": i,
                            "caption": getattr(table, 'caption', ''),
                            "page": getattr(table, 'page', 'unknown'),
                            "rows": getattr(table, 'num_rows', 'unknown'),
                            "cols": getattr(table, 'num_cols', 'unknown')
                        }
                        
                        # Get table content
                        if hasattr(table, 'export_to_markdown'):
                            table_content = table.export_to_markdown()
                        elif hasattr(table, 'text'):
                            table_content = table.text
                        else:
                            table_content = str(table)
                        
                        table_info["content"] = table_content
                        tables.append(table_info)
                        
                    except Exception as e:
                        logger.error(f"Error processing table {i}: {e}")
                        tables.append({
                            "index": i,
                            "content": f"[Table {i+1}: Processing failed]",
                            "error": str(e)
                        })
            
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
        
        return tables
    
    def cleanup_markdown(self, markdown_content: str) -> str:
        """Clean up markdown content."""
        content = markdown_content
        
        if len(content.strip()) < 10:
            return content
            
        try:
            # Normalize line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Remove trailing whitespace
            if self.config.FORMATTING_CONFIG["normalize_whitespace"]:
                lines = content.split('\n')
                cleaned_lines = []
                in_code_block = False
                
                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        cleaned_lines.append(line.rstrip())
                    elif in_code_block and self.config.FORMATTING_CONFIG["preserve_code_blocks"]:
                        cleaned_lines.append(line)
                    else:
                        cleaned_lines.append(line.rstrip().expandtabs(4))
                
                content = '\n'.join(cleaned_lines)
            
            # Limit consecutive line breaks
            max_breaks = self.config.FORMATTING_CONFIG["max_consecutive_linebreaks"]
            if max_breaks > 0:
                pattern = r'\n{' + str(max_breaks + 1) + r',}'
                replacement = '\n' * max_breaks
                content = re.sub(pattern, replacement, content)
            
            # Fix spacing around headings
            if self.config.FORMATTING_CONFIG["fix_heading_spacing"]:
                content = re.sub(r'\n{3,}(#{1,6} )', r'\n\n\1', content)
                content = re.sub(r'(#{1,6} .+)\n{3,}', r'\1\n\n', content)
            
            # Clean up image blocks
            content = re.sub(r'(<\/image>)\n{3,}', r'\1\n\n', content)
            
            # Clean up document
            content = content.strip()
            content = re.sub(r'\n{3,}$', '\n\n', content)
            
            return content
            
        except Exception as e:
            logger.warning(f"⚠️ Error during markdown cleanup: {e}")
            return markdown_content
    
    def add_page_numbers_to_content(self, docling_result, markdown_content: str) -> str:
        """Add page numbers to markdown content."""
        try:
            placeholder = self.config.FORMATTING_CONFIG["page_placeholder"]
            markdown_with_markers = docling_result.document.export_to_markdown(
                page_break_placeholder=f"\n{placeholder}\n"
            )
            
            if hasattr(docling_result.document, 'pages') and docling_result.document.pages:
                page_numbers = sorted(docling_result.document.pages.keys())
                parts = markdown_with_markers.split(placeholder)
                final_markdown = parts[0]
                
                for i, part in enumerate(parts[1:], 1):
                    if i <= len(page_numbers):
                        page_num = page_numbers[i-1]
                    else:
                        page_num = i
                    
                    page_marker_template = self.config.FORMATTING_CONFIG["page_marker_template"]
                    if page_marker_template.strip():
                        page_marker = page_marker_template.format(page_num=page_num)
                        final_markdown += f"\n{page_marker}\n{part}"
                    else:
                        final_markdown += part
                
                return final_markdown
            else:
                return markdown_content
                
        except Exception as e:
            logger.warning(f"Failed to add page markers: {e}")
            return markdown_content
    
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
                    
                    image_title_template = self.config.FORMATTING_CONFIG["image_title_template"]
                    if image_title_template.strip():
                        image_title = image_title_template.format(image_num=image['index'] + 1)
                        lines[i] = f"\n{image_title}\n{image['description']}\n"
                    else:
                        lines[i] = f"\n{image['description']}\n"
                    image_index += 1
            enhanced_markdown = '\n'.join(lines)
        
        # Clean up if enabled
        if config.cleanup_markdown:
            enhanced_markdown = self.cleanup_markdown(enhanced_markdown)
        
        return enhanced_markdown
    
    def parse_pdf_from_bytes(self, pdf_data: bytes, filename: str = "document.pdf", 
                           config: Optional[ParseConfig] = None) -> ParseResult:
        """Parse PDF from bytes data."""
        if config is None:
            config = ParseConfig()
            
        try:
            # Validate PDF
            self.validate_pdf(pdf_data)
            
            # Create temporary file for Docling
            import tempfile
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
                    images = self.extract_images_from_document(result, config)
                
                logger.info("Extracting tables...")
                tables = self.extract_tables_from_document(result)
                
                # Add page numbers if enabled
                if config.include_page_numbers:
                    markdown_content = self.add_page_numbers_to_content(result, markdown_content)
                
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
