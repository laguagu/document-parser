"""
Shared PDF Processing Utilities
Common functions used by both CLI and API parsers
"""

import base64
import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

# Import shared configuration
from config import AZURE_CONFIG, FORMATTING_CONFIG, PROCESSING_CONFIG
from openai import AzureOpenAI

# Configure logging
logger = logging.getLogger(__name__)

# ===== SHARED UTILITY FUNCTIONS =====

def validate_pdf_data(pdf_data: bytes) -> bool:
    """
    Validate PDF data for safety and compatibility.
    
    Args:
        pdf_data: PDF file bytes
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If file is invalid or too large
    """
    try:
        # Check file size
        file_size = len(pdf_data)
        max_size = PROCESSING_CONFIG["max_pdf_size"]
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

def validate_pdf_file(file_path: str) -> bool:
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

def encode_image_to_base64(image_data: bytes) -> str:
    """Encode image bytes to base64."""
    try:
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        return ""

def analyze_image_with_azure(azure_client: Optional[AzureOpenAI], image_data: bytes, image_info: str = "") -> str:
    """
    Analyze image using Azure OpenAI GPT-4.1 with structured outputs and retry logic.
    
    Args:
        azure_client: Initialized Azure OpenAI client (or None)
        image_data: Image bytes
        image_info: Additional info about the image
        
    Returns:
        Formatted image description
    """
    if not azure_client:
        return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info}{FORMATTING_CONFIG['image_wrapper_end']}"
    
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            base64_image = encode_image_to_base64(image_data)
            if not base64_image:
                return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - Failed to encode{FORMATTING_CONFIG['image_wrapper_end']}"
            
            response = azure_client.chat.completions.create(
                model=AZURE_CONFIG["deployment_name"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document analyst specializing in extracting structured information from charts, tables, and diagrams. Follow the provided format exactly to create comprehensive markdown-formatted analysis."
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
                max_tokens=1500,  # More tokens for detailed markdown output
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content
            if not analysis_text:
                return f"{FORMATTING_CONFIG['image_wrapper_start']}{image_info} - No analysis generated{FORMATTING_CONFIG['image_wrapper_end']}"
            
            # Return the full markdown analysis wrapped in image tags
            return f"{FORMATTING_CONFIG['image_wrapper_start']}\n{analysis_text}\n{FORMATTING_CONFIG['image_wrapper_end']}"
            
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

def extract_images_from_document(docling_result, azure_client: Optional[AzureOpenAI], azure_analysis: bool = True) -> List[Dict[str, Any]]:
    """
    Extract images from Docling document result.
    
    Args:
        docling_result: Docling conversion result
        azure_client: Azure OpenAI client for image analysis
        azure_analysis: Whether to perform Azure analysis
        
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
                    
                    # Analyze image if data available and Azure analysis enabled
                    if image_data and azure_analysis:
                        description = analyze_image_with_azure(
                            azure_client,
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

def extract_tables_from_document(docling_result) -> List[Dict[str, Any]]:
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

def cleanup_markdown(markdown_content: str) -> str:
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

def add_page_numbers_to_content(docling_result, markdown_content: str) -> str:
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
