"""
Simple PDF Parser using Docling
A simple tool to parse PDF files and save results as Markdown
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from docling.document_converter import DocumentConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplePDFParser:
    """
    Simple PDF parser using Docling.
    Converts PDF files to Markdown format.
    """

    def __init__(self):
        """Initialize Docling converter."""
        self.doc_converter = DocumentConverter()
        print("✅ Docling PDF parser initialized")

    def parse_pdf(
        self, pdf_path: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse PDF file and save as Markdown.

        Args:
            pdf_path: Path to PDF file
            output_file: Optional output file path (defaults to PDF name + .md)

        Returns:
            Parse results
        """
        logger.info(f"Parsing file: {pdf_path}")

        # Check if file exists
        if not os.path.exists(pdf_path):
            return {"success": False, "error": f"File not found: {pdf_path}"}

        # Check file extension
        file_ext = Path(pdf_path).suffix.lower()
        if file_ext != ".pdf":
            return {
                "success": False,
                "error": f"Unsupported file format: {file_ext}. Only PDF files are supported.",
            }

        try:
            # Convert PDF with Docling
            logger.info("Converting PDF to structured document...")
            result = self.doc_converter.convert(pdf_path)

            # Export to Markdown
            logger.info("Exporting to Markdown...")
            markdown_content = result.document.export_to_markdown()

            # Determine output file
            if not output_file:
                pdf_name = Path(pdf_path).stem
                output_file = f"{pdf_name}.md"

            # Save Markdown file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Get document stats
            pages_count = (
                len(result.document.pages) if hasattr(result.document, "pages") else 1
            )
            text_length = len(markdown_content)

            logger.info(f"Saved to: {output_file}")

            return {
                "success": True,
                "input_file": pdf_path,
                "output_file": output_file,
                "pages_processed": pages_count,
                "text_length": text_length,
                "markdown_preview": markdown_content[:500] + "..."
                if len(markdown_content) > 500
                else markdown_content,
            }

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Example usage of the PDF parser."""

    # Initialize parser
    parser = SimplePDFParser()

    # File to process
    file_path = "pdf-example.pdf"

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        print("Please place your PDF file in this directory")
        return

    print(f"📄 Found PDF: {file_path}")
    print(f"🔄 Parsing {file_path}...")

    # Parse PDF
    result = parser.parse_pdf(file_path)

    # Display results
    print(f"\n{'=' * 50}")
    print("PARSING RESULTS")
    print(f"{'=' * 50}")

    if result["success"]:
        print(f"✅ Success!")
        print(f"� Input: {result['input_file']}")
        print(f"📝 Output: {result['output_file']}")
        print(f"📄 Pages: {result['pages_processed']}")
        print(f"� Text length: {result['text_length']} characters")
        print(f"\n� Preview:")
        print(f"{result['markdown_preview']}")
        print(f"\n💾 Full Markdown saved to: {result['output_file']}")
        print("🎉 Ready to use!")
    else:
        print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    main()
