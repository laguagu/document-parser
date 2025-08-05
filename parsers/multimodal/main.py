"""
Advanced PDF Parser using Docling + Azure OpenAI
A tool to parse PDF files with image analysis using Azure GPT-4o
"""

import base64
import io
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Load environment variables FIRST
load_dotenv()

# ===== PYDANTIC MODELS =====
class ImageAnalysis(BaseModel):
    """Structured model for image analysis results."""
    text_content: Optional[str] = Field(None, description="Any readable text, titles, labels, or captions found in the image")
    data_numbers: Optional[str] = Field(None, description="Key statistics, values, or quantitative information visible")
    subject_matter: str = Field(..., description="Brief description of the main topic or concept depicted")

# ===== CONFIGURATION =====
# Azure OpenAI Configuration
AZURE_CONFIG = {
    "api_key": os.getenv("AZURE_API_KEY"),
    "endpoint": os.getenv("AZURE_API_BASE"), 
    "deployment_name": "gpt-4.1",  # Updated to latest GPT-4.1 model
    "api_version": "2024-10-01-preview"
}

# Processing Configuration  
PROCESSING_CONFIG = {
    "process_images": True,
    "max_image_size": 20*1024*1024,  # 20MB
    "max_pdf_size": 100*1024*1024,  # 100MB maximum PDF file size
    "supported_formats": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"],
    "images_inline": True,  # If True, place images inline. If False, place at end
    "image_analysis_prompt": """Analyze this image for document search. Identify relevant content for each category:

- text_content: Only include if readable text, titles, labels, or captions are visible (exclude irrelevant details like classroom exercises)
- data_numbers: Only include if meaningful statistics, values, or quantitative information are present  
- subject_matter: Brief description of the main topic or concept

Be concise and focus on information useful for document search and retrieval."""
}

# Output Configuration
OUTPUT_CONFIG = {
    "include_page_numbers": True,  # If True, add page numbers to content
    "include_tables_section": False,  # If True, add "## 📊 Tables" section at end
    "include_images_section": False,  # If True, add "## 🖼️ Images and Figures" section (when images not inline)
    "cleanup_markdown": True,  # If True, clean up excessive whitespace and formatting issues
}

# Markdown Formatting Configuration
# NOTE: Set any template to empty string ("") to disable that formatting element
FORMATTING_CONFIG = {
    # Page numbering format
    "page_marker_template": "--- Page {page_num} ---",  # Template for page markers (empty = no page markers)
    "page_placeholder": "___PAGE_BREAK_MARKER___",     # Internal placeholder for processing
    
    # Image formatting
    "image_wrapper_start": "<image>",                   # Opening tag for image descriptions
    "image_wrapper_end": "</image>",                    # Closing tag for image descriptions
    "image_title_template": "**Image {image_num}:**",   # Template for image titles (empty = no titles, inline mode)
    "image_header_template": "### Image {image_num}",   # Template for image headers (empty = no headers, section mode)
    
    # Table formatting  
    "table_header_template": "### Table {table_num}",   # Template for table headers (empty = no headers)
    "table_size_template": "**Size:** {rows} rows × {cols} columns",  # Template for table size info (empty = no size info)
    
    # Section headers
    "images_section_header": "## 🖼️ Images and Figures",  # Header for images section (empty = no section header)
    "tables_section_header": "## 📊 Tables",               # Header for tables section (empty = no section header)
    
    # Cleanup configuration
    "max_consecutive_linebreaks": 2,                    # Maximum allowed consecutive line breaks
    "preserve_code_blocks": True,                       # Preserve formatting in code blocks
    "normalize_whitespace": True,                       # Remove trailing spaces and normalize tabs
    "fix_heading_spacing": True,                        # Ensure proper spacing around headings
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedPDFParser:
    """
    Advanced PDF parser using Docling + Azure OpenAI.
    Converts PDF files to Markdown with image analysis.
    """
    
    def __init__(self):
        """Initialize Docling converter and Azure OpenAI client."""
        # Configure pipeline for image extraction
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 2.0  # Higher resolution for better quality
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        
        # Initialize Docling with proper options
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        logger.info("✅ Docling PDF parser initialized with image extraction enabled")
        
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
                logger.info("📝 Will parse without image analysis")
        else:
            logger.info("📝 Azure config missing - parsing without image analysis")
    
    def validate_pdf(self, file_path: str) -> bool:
        """
        Validate PDF file for safety and compatibility.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If file is invalid or too large
        """
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size = PROCESSING_CONFIG["max_pdf_size"]
            if file_size > max_size:
                raise ValueError(f"File too large: {file_size:,} bytes (max: {max_size:,} bytes)")
            
            # Check PDF header
            with open(file_path, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
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
        """
        Analyze image using Azure OpenAI GPT-4.1 with structured outputs and retry logic.
        
        Args:
            image_data: Image bytes
            image_info: Additional info about the image
            
        Returns:
            Formatted image description
        """
        if not self.azure_client:
            return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info}{FORMATTING_CONFIG['image_wrapper_end']}"
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                base64_image = self.encode_image_to_base64(image_data)
                if not base64_image:
                    return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Failed to encode{FORMATTING_CONFIG['image_wrapper_end']}"
                
                response = self.azure_client.beta.chat.completions.parse(
                    model=AZURE_CONFIG["deployment_name"],
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert document analyst. Extract key factual information from images for use in search and retrieval systems. Focus on content that would be valuable for business intelligence and research purposes."
                        },
                        {
                            "role": "user", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": PROCESSING_CONFIG["image_analysis_prompt"]
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
                    return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - No analysis generated{FORMATTING_CONFIG['image_wrapper_end']}"
                
                # Format the structured output
                formatted_parts = []
                if analysis.text_content:
                    formatted_parts.append(f"Text content: {analysis.text_content}")
                if analysis.data_numbers:
                    formatted_parts.append(f"Data/Numbers: {analysis.data_numbers}")
                formatted_parts.append(f"Subject matter: {analysis.subject_matter}")
                
                formatted_description = "\n".join(formatted_parts)
                return f"{FORMATTING_CONFIG['image_wrapper_start']}\n{formatted_description}\n{FORMATTING_CONFIG['image_wrapper_end']}"
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Azure API attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Azure API failed after {max_retries} attempts: {e}")
                    return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Analysis failed after retries: {str(e)}{FORMATTING_CONFIG['image_wrapper_end']}"
        
        # This should never be reached, but just in case
        return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Unexpected error{FORMATTING_CONFIG['image_wrapper_end']}"
    
    def extract_images_from_document(self, docling_result) -> List[Dict[str, Any]]:
        """
        Extract images from Docling document result.
        
        Args:
            docling_result: Docling conversion result
            
        Returns:
            List of image information
        """
        images = []
        
        try:
            # Debug: print document structure
            logger.info(f"Document has pictures attribute: {hasattr(docling_result.document, 'pictures')}")
            if hasattr(docling_result.document, 'pictures'):
                logger.info(f"Number of pictures: {len(docling_result.document.pictures) if docling_result.document.pictures else 0}")
            
            # Get pictures from document
            if hasattr(docling_result.document, 'pictures') and docling_result.document.pictures:
                for i, picture in enumerate(docling_result.document.pictures):
                    try:
                        logger.info(f"Processing picture {i+1}: {type(picture)}")
                        logger.info(f"Picture attributes: {[attr for attr in dir(picture) if not attr.startswith('_')]}")
                        
                        # Get image data
                        image_data = None
                        if hasattr(picture, 'get_image') and callable(picture.get_image):
                            try:
                                logger.info(f"Attempting to call get_image(doc) for picture {i+1}")
                                # Try with document parameter
                                pil_image = picture.get_image(docling_result.document)
                                logger.info(f"get_image() returned: {type(pil_image)}, value: {pil_image}")
                                if pil_image:
                                    # Convert PIL image to bytes
                                    buffer = io.BytesIO()
                                    pil_image.save(buffer, format='PNG')  # type: ignore
                                    image_data = buffer.getvalue()
                                    logger.info(f"Found PIL image via get_image(doc), converted to bytes, size: {len(image_data)}")
                                else:
                                    logger.warning(f"get_image(doc) returned None for picture {i+1}")
                            except Exception as e:
                                logger.warning(f"Error calling get_image(doc): {e}")
                        elif hasattr(picture, 'image') and picture.image:
                            image_data = picture.image
                            logger.info(f"Found image data via 'image' attribute, size: {len(image_data) if image_data else 0}")
                        elif hasattr(picture, 'data') and picture.data:
                            image_data = picture.data
                            logger.info(f"Found image data via 'data' attribute, size: {len(image_data) if image_data else 0}")
                        elif hasattr(picture, 'pil_image') and picture.pil_image:
                            # Convert PIL image to bytes
                            buffer = io.BytesIO()
                            picture.pil_image.save(buffer, format='PNG')  # type: ignore
                            image_data = buffer.getvalue()
                            logger.info(f"Found PIL image, converted to bytes, size: {len(image_data)}")
                        else:
                            logger.warning(f"No image data found for picture {i+1}")
                            
                        logger.info(f"Final image_data for picture {i+1}: {image_data is not None}, size: {len(image_data) if image_data else 0}")
                        
                        # Get image info
                        image_info = {
                            "index": i,
                            "caption": getattr(picture, 'caption', ''),
                            "page": getattr(picture, 'page', 'unknown'),
                            "has_data": image_data is not None
                        }
                        
                        # Analyze image if data available
                        if image_data and PROCESSING_CONFIG["process_images"]:
                            description = self.analyze_image_with_azure(
                                image_data, 
                                f"Image {i+1} from page {image_info['page']}"
                            )
                            image_info["description"] = description
                        else:
                            image_info["description"] = f"[Image {i+1}: {image_info['caption'] or 'No caption'}]"
                        
                        images.append(image_info)
                        logger.info(f"Processed image {i+1}")
                        
                    except Exception as e:
                        logger.error(f"Error processing image {i}: {e}")
                        images.append({
                            "index": i,
                            "description": f"[Image {i+1}: Processing failed]",
                            "error": str(e)
                        })
            else:
                logger.info("No pictures found in document")
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
        
        logger.info(f"Total images extracted: {len(images)}")
        return images
    
    def extract_tables_from_document(self, docling_result) -> List[Dict[str, Any]]:
        """
        Extract tables from Docling document result.
        
        Args:
            docling_result: Docling conversion result
            
        Returns:
            List of table information
        """
        tables = []
        
        try:
            # Get tables from document
            if hasattr(docling_result.document, 'tables') and docling_result.document.tables:
                for i, table in enumerate(docling_result.document.tables):
                    try:
                        # Get table info
                        table_info = {
                            "index": i,
                            "caption": getattr(table, 'caption', ''),
                            "page": getattr(table, 'page', 'unknown'),
                            "rows": getattr(table, 'num_rows', 'unknown'),
                            "cols": getattr(table, 'num_cols', 'unknown')
                        }
                        
                        # Get table content as text/markdown
                        if hasattr(table, 'export_to_markdown'):
                            table_content = table.export_to_markdown()
                        elif hasattr(table, 'text'):
                            table_content = table.text
                        else:
                            table_content = str(table)
                        
                        table_info["content"] = table_content
                        tables.append(table_info)
                        logger.info(f"Processed table {i+1}")
                        
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
        """
        Clean up markdown content by removing excessive whitespace and fixing formatting issues.
        
        Args:
            markdown_content: Raw markdown content to clean
            
        Returns:
            Cleaned markdown content
        """
        content = markdown_content
        
        # Skip cleanup if content is too short
        if len(content.strip()) < 10:
            return content
            
        try:
            # 1. Normalize line endings to \n
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # 2. Remove trailing whitespace from each line (but preserve code blocks)
            if FORMATTING_CONFIG["normalize_whitespace"]:
                lines = content.split('\n')
                cleaned_lines = []
                in_code_block = False
                
                for line in lines:
                    # Track code blocks to preserve their formatting
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        cleaned_lines.append(line.rstrip())
                    elif in_code_block and FORMATTING_CONFIG["preserve_code_blocks"]:
                        # Preserve whitespace in code blocks
                        cleaned_lines.append(line)
                    else:
                        # Remove trailing whitespace, convert tabs to spaces
                        cleaned_lines.append(line.rstrip().expandtabs(4))
                
                content = '\n'.join(cleaned_lines)
            
            # 3. Limit consecutive line breaks
            max_breaks = FORMATTING_CONFIG["max_consecutive_linebreaks"]
            if max_breaks > 0:
                # Replace 3+ consecutive line breaks with max allowed
                pattern = r'\n{' + str(max_breaks + 1) + r',}'
                replacement = '\n' * max_breaks
                content = re.sub(pattern, replacement, content)
            
            # 4. Fix spacing around headings
            if FORMATTING_CONFIG["fix_heading_spacing"]:
                # Ensure single line break before headings (except at start of document)
                content = re.sub(r'\n{3,}(#{1,6} )', r'\n\n\1', content)
                
                # Ensure single line break after headings
                content = re.sub(r'(#{1,6} .+)\n{3,}', r'\1\n\n', content)
                
                # Fix spacing around page markers (only if template is not empty)
                page_marker_template = FORMATTING_CONFIG["page_marker_template"]
                if page_marker_template.strip():
                    page_marker_pattern = re.escape(page_marker_template.split('{')[0])
                    content = re.sub(rf'\n{{3,}}({page_marker_pattern})', r'\n\n\1', content)
                    content = re.sub(rf'({page_marker_pattern}[^\n]+)\n{{3,}}', r'\1\n\n', content)
            
            # 5. Remove excessive whitespace around image blocks (only if template is not empty)
            image_title_template = FORMATTING_CONFIG["image_title_template"]
            if image_title_template.strip():
                content = re.sub(r'\n{3,}(\*\*Image \d+:\*\*)', r'\n\n\1', content)
            content = re.sub(r'(<\/image>)\n{3,}', r'\1\n\n', content)
            
            # 6. Clean up document start and end
            content = content.strip()
            
            # 7. Ensure document doesn't end with excessive line breaks
            content = re.sub(r'\n{3,}$', '\n\n', content)
            
            logger.info("✅ Markdown content cleaned up successfully")
            return content
            
        except Exception as e:
            logger.warning(f"⚠️ Error during markdown cleanup: {e}")
            return markdown_content  # Return original if cleanup fails

    def _add_page_numbers_to_content(self, docling_result, markdown_content: str) -> str:
        """
        Add inline page numbers to markdown content.
        Since Docling doesn't automatically replace {page_no}, we need to do it manually.
        
        Args:
            docling_result: Docling conversion result with document structure
            markdown_content: Original markdown content
            
        Returns:
            Enhanced markdown with inline page markers
        """
        try:
            # First, export with placeholder to get page break positions
            placeholder = FORMATTING_CONFIG["page_placeholder"]
            markdown_with_markers = docling_result.document.export_to_markdown(
                page_break_placeholder=f"\n{placeholder}\n"
            )
            
            # Now we need to replace markers with actual page numbers
            # Get all page numbers from the document
            if hasattr(docling_result.document, 'pages') and docling_result.document.pages:
                page_numbers = sorted(docling_result.document.pages.keys())
                
                # Split by our placeholder and reassemble with page numbers
                parts = markdown_with_markers.split(placeholder)
                
                # Build the final markdown with page numbers
                final_markdown = parts[0]  # First part before any page break
                
                for i, part in enumerate(parts[1:], 1):
                    # Determine the page number
                    if i <= len(page_numbers):
                        page_num = page_numbers[i-1]  # Use actual page number
                    else:
                        page_num = i  # Fallback to sequential numbering
                    
                    # Only add page marker if template is not empty
                    page_marker_template = FORMATTING_CONFIG["page_marker_template"]
                    if page_marker_template.strip():
                        page_marker = page_marker_template.format(page_num=page_num)
                        final_markdown += f"\n{page_marker}\n{part}"
                    else:
                        # No page marker, just add the content
                        final_markdown += part
                
                logger.info(f"Added {len(parts)-1} page markers to markdown")
                return final_markdown
                
            else:
                logger.warning("No pages found in document, using original markdown")
                return markdown_content
                
        except Exception as e:
            logger.warning(f"Failed to add page markers: {e}")
            return markdown_content
    
    def create_enhanced_markdown(self, markdown_content: str, images: List[Dict[str, Any]], tables: List[Dict[str, Any]], 
                               images_inline: bool = True, include_page_numbers: bool = True,
                               include_tables_section: bool = True, 
                               include_images_section: bool = True) -> str:
        """
        Create enhanced markdown with image descriptions and table extracts.
        
        Args:
            markdown_content: Original markdown from Docling (may already have page numbers)
            images: List of image information
            tables: List of table information
            images_inline: If True, place images inline. If False, place at end.
            include_page_numbers: Ignored - page numbers should be added before calling this method
            include_tables_section: If True, add tables section at end
            include_images_section: If True, add images section (when not images_inline)
            
        Returns:
            Enhanced markdown with image descriptions and tables
        """
        enhanced_markdown = markdown_content
        
        if images_inline:
            # Inline behavior: replace <!-- image --> with actual descriptions
            # Replace image placeholders with descriptions
            if images:
                image_index = 0
                lines = enhanced_markdown.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == "<!-- image -->" and image_index < len(images):
                        # Replace with image description using config template
                        image = images[image_index]
                        
                        # Only add image title if template is not empty
                        image_title_template = FORMATTING_CONFIG["image_title_template"]
                        if image_title_template.strip():
                            image_title = image_title_template.format(image_num=image['index'] + 1)
                            lines[i] = f"\n{image_title}\n{image['description']}\n"
                        else:
                            # No title, just the description
                            lines[i] = f"\n{image['description']}\n"
                        image_index += 1
                enhanced_markdown = '\n'.join(lines)
        else:
            # Images at end: add image descriptions section only if enabled
            if images and include_images_section:
                # Only add section header if template is not empty
                images_section_template = FORMATTING_CONFIG["images_section_header"]
                if images_section_template.strip():
                    enhanced_markdown += f"\n\n{images_section_template}\n\n"
                else:
                    enhanced_markdown += "\n\n"
                
                for image in images:
                    # Only add image header if template is not empty
                    image_header_template = FORMATTING_CONFIG["image_header_template"]
                    if image_header_template.strip():
                        image_header = image_header_template.format(image_num=image['index'] + 1)
                        enhanced_markdown += f"{image_header}\n"
                    
                    if image.get('caption'):
                        enhanced_markdown += f"**Caption:** {image['caption']}\n\n"
                    enhanced_markdown += f"{image['description']}\n\n"
        
        # Add tables section only if enabled
        if tables and include_tables_section:
            # Only add section header if template is not empty
            tables_section_template = FORMATTING_CONFIG["tables_section_header"]
            if tables_section_template.strip():
                enhanced_markdown += f"\n\n{tables_section_template}\n\n"
            else:
                enhanced_markdown += "\n\n"
            
            for table in tables:
                # Only add table header if template is not empty
                table_header_template = FORMATTING_CONFIG["table_header_template"]
                if table_header_template.strip():
                    table_header = table_header_template.format(table_num=table['index'] + 1)
                    enhanced_markdown += f"{table_header}\n"
                
                if table.get('caption'):
                    enhanced_markdown += f"**Caption:** {table['caption']}\n\n"
                
                # Only add table size if template is not empty
                table_size_template = FORMATTING_CONFIG["table_size_template"]
                if (table.get('rows') != 'unknown' and table.get('cols') != 'unknown' 
                    and table_size_template.strip()):
                    table_size = table_size_template.format(rows=table['rows'], cols=table['cols'])
                    enhanced_markdown += f"{table_size}\n\n"
                
                enhanced_markdown += f"{table['content']}\n\n"
        
        # Clean up the final markdown content if enabled
        if OUTPUT_CONFIG["cleanup_markdown"]:
            enhanced_markdown = self.cleanup_markdown(enhanced_markdown)
        
        return enhanced_markdown
    
    def parse_pdf(self, pdf_path: str, output_file: Optional[str] = None, 
                  images_inline: Optional[bool] = None, 
                  include_page_numbers: Optional[bool] = None,
                  include_tables_section: Optional[bool] = None,
                  include_images_section: Optional[bool] = None) -> Dict[str, Any]:
        """
        Parse PDF file and save as enhanced Markdown with image analysis.
        
        Args:
            pdf_path: Path to PDF file
            output_file: Optional output file path (defaults to PDF name + .md)
            images_inline: If True, place images inline. If False, at end. If None, use config default.
            include_page_numbers: If True, add page numbers. If None, use config default.
            include_tables_section: If True, add tables section. If None, use config default.
            include_images_section: If True, add images section. If None, use config default.
            
        Returns:
            Parse results
        """
        # Apply configuration defaults
        images_inline = images_inline if images_inline is not None else PROCESSING_CONFIG["images_inline"]
        include_page_numbers = include_page_numbers if include_page_numbers is not None else OUTPUT_CONFIG["include_page_numbers"]
        include_tables_section = include_tables_section if include_tables_section is not None else OUTPUT_CONFIG["include_tables_section"]
        include_images_section = include_images_section if include_images_section is not None else OUTPUT_CONFIG["include_images_section"]
        
        logger.info(f"Parsing file: {pdf_path}")
        logger.info(f"Config: images_inline={images_inline}, page_numbers={include_page_numbers}, tables={include_tables_section}, images={include_images_section}")
        
        # Validate PDF file first
        try:
            self.validate_pdf(pdf_path)
        except ValueError as e:
            return {
                "success": False,
                "error": f"PDF validation failed: {e}"
            }
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"File not found: {pdf_path}"
            }
        
        # Check file extension
        file_ext = Path(pdf_path).suffix.lower()
        if file_ext != '.pdf':
            return {
                "success": False,
                "error": f"Unsupported file format: {file_ext}. Only PDF files are supported."
            }
        
        try:
            # Convert PDF with Docling
            logger.info("Converting PDF to structured document...")
            result = self.doc_converter.convert(pdf_path)
            
            # Export to Markdown
            logger.info("Exporting to Markdown...")
            markdown_content = result.document.export_to_markdown()
            
            # Extract and analyze images
            logger.info("Extracting and analyzing images...")
            images = self.extract_images_from_document(result)
            
            # Extract tables
            logger.info("Extracting tables...")
            tables = self.extract_tables_from_document(result)
            
            # Add page numbers to markdown if enabled
            if include_page_numbers:
                markdown_content = self._add_page_numbers_to_content(result, markdown_content)
            
            # Create enhanced markdown
            enhanced_markdown = self.create_enhanced_markdown(
                markdown_content, images, tables, images_inline, False,  # Page numbers already added
                include_tables_section, include_images_section
            )
            
            # Determine output file
            if not output_file:
                pdf_name = Path(pdf_path).stem
                suffix = "_inline" if images_inline else "_enhanced"
                output_file = f"output/{pdf_name}{suffix}.md"
            
            # Save enhanced Markdown file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(enhanced_markdown)
            
            # Get document stats
            pages_count = len(result.document.pages) if hasattr(result.document, 'pages') else 1
            text_length = len(enhanced_markdown)
            images_count = len(images)
            tables_count = len(tables)
            
            logger.info(f"Saved to: {output_file}")
            
            return {
                "success": True,
                "input_file": pdf_path,
                "output_file": output_file,
                "pages_processed": pages_count,
                "images_processed": images_count,
                "tables_processed": tables_count,
                "text_length": text_length,
                "images": images,
                "tables": tables,
                "azure_analysis": self.azure_client is not None,
                "markdown_preview": enhanced_markdown[:500] + "..." if len(enhanced_markdown) > 500 else enhanced_markdown
            }
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """Example usage of the advanced PDF parser."""
    
    # Initialize parser
    parser = AdvancedPDFParser()
    
    # File to process
    file_path = "input/pdf-example.pdf"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        print("Please place your PDF file in the input/ directory")
        return
    
    print(f"📄 Found PDF: {file_path}")
    print(f"🔄 Parsing {file_path}...")
    
    # Parse PDF using configuration settings
    # Configuration can be changed in OUTPUT_CONFIG at the top of the file
    result = parser.parse_pdf(file_path)
    
    # Display results
    print(f"\n{'='*50}")
    print("PARSING RESULTS")
    print(f"{'='*50}")
    
    if result['success']:
        print(f"✅ Success!")
        print(f"📄 Input: {result['input_file']}")
        print(f"📝 Output: {result['output_file']}")
        print(f"📄 Pages: {result['pages_processed']}")
        print(f"🖼️ Images: {result['images_processed']}")
        print(f"📊 Tables: {result['tables_processed']}")
        print(f"🤖 Azure Analysis: {'Enabled' if result['azure_analysis'] else 'Disabled'}")
        print(f"📝 Text length: {result['text_length']} characters")
        
        if result['images_processed'] > 0:
            print(f"\n🖼️ Image Analysis:")
            for image in result['images'][:3]:  # Show first 3
                desc = image['description'][:100] + "..." if len(image['description']) > 100 else image['description']
                print(f"   Image {image['index'] + 1}: {desc}")
        
        if result['tables_processed'] > 0:
            print(f"\n📊 Tables Found:")
            for table in result['tables'][:2]:  # Show first 2
                caption = table.get('caption', 'No caption')[:50]
                size = f"{table.get('rows', '?')}×{table.get('cols', '?')}"
                print(f"   Table {table['index'] + 1}: {caption} ({size})")
        
        print(f"\n📋 Preview:")
        print(f"{result['markdown_preview']}")
        print(f"\n💾 Full enhanced Markdown saved to: {result['output_file']}")
        print("🎉 Ready for RAG with images and tables!")
    else:
        print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    main()
