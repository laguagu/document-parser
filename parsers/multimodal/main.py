"""
Advanced PDF Parser using Docling + Azure OpenAI
A tool to parse PDF files with image analysis using Azure GPT-4o
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from openai import AzureOpenAI

# Import shared configuration and utilities
sys.path.append(str(Path(__file__).parent.parent))
from config import (AZURE_CONFIG, FORMATTING_CONFIG, OUTPUT_CONFIG,
                    PROCESSING_CONFIG)
from pdf_utils import (add_page_numbers_to_content, cleanup_markdown,
                       extract_images_from_document,
                       extract_tables_from_document, validate_pdf_file)

# Load environment variables FIRST - from parent directory  
load_dotenv(Path(__file__).parent.parent / '.env')

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
            enhanced_markdown = cleanup_markdown(enhanced_markdown)
        
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
            validate_pdf_file(pdf_path)
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
            images = extract_images_from_document(result, self.azure_client, True)
            
            # Extract tables
            logger.info("Extracting tables...")
            tables = extract_tables_from_document(result)
            
            # Add page numbers to markdown if enabled
            if include_page_numbers:
                markdown_content = add_page_numbers_to_content(result, markdown_content)
            
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
    file_path = "input/pdf-with-complex-tables.pdf" # If you want to test with a different file, change this path
    # file_path = "input/pdf-example.pdf" 
    
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
        print("✅ Success!")
        print(f"📄 Input: {result['input_file']}")
        print(f"📝 Output: {result['output_file']}")
        print(f"📄 Pages: {result['pages_processed']}")
        print(f"🖼️ Images: {result['images_processed']}")
        print(f"📊 Tables: {result['tables_processed']}")
        print(f"🤖 Azure Analysis: {'Enabled' if result['azure_analysis'] else 'Disabled'}")
        print(f"📝 Text length: {result['text_length']} characters")
        
        if result['images_processed'] > 0:
            print("\n🖼️ Image Analysis:")
            for image in result['images'][:3]:  # Show first 3
                desc = image['description'][:100] + "..." if len(image['description']) > 100 else image['description']
                print(f"   Image {image['index'] + 1}: {desc}")
        
        if result['tables_processed'] > 0:
            print("\n📊 Tables Found:")
            for table in result['tables'][:2]:  # Show first 2
                caption = table.get('caption', 'No caption')[:50]
                size = f"{table.get('rows', '?')}×{table.get('cols', '?')}"
                print(f"   Table {table['index'] + 1}: {caption} ({size})")
        
        print("\n📋 Preview:")
        print(f"{result['markdown_preview']}")
        print(f"\n💾 Full enhanced Markdown saved to: {result['output_file']}")
        print("🎉 Ready for RAG with images and tables!")
    else:
        print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    main()