"""
FastAPI server for PDF parsing
Simple API endpoint that accepts PDF files and returns enhanced markdown
"""

import logging
import os
from typing import Any, Dict

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from parser_service import ParseConfig, ParseResult, PDFParserService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API key configuration
API_KEY = os.getenv("PDF_PARSER_API_KEY", "your-default-api-key-here")  # Change this!

# Security scheme
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Initialize FastAPI app
app = FastAPI(
    title="PDF Parser API",
    description="Advanced PDF to Markdown converter with AI image analysis",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize parser service
parser_service = PDFParserService()


@app.get("/")
async def root():
    """Public health check endpoint."""
    return {
        "message": "PDF Parser API is running",
        "version": "1.0.0",
        "status": "healthy",
        "authentication": "required"
    }


@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {
        "status": "healthy",
        "service": "pdf-parser-api",
        "authentication": "API key required for /parse-pdf endpoint"
    }


@app.post("/parse-pdf")
async def parse_pdf(
    file: UploadFile = File(..., description="PDF file to parse"),
    images_inline: bool = Query(
        True, description="Whether to include images inline in markdown"
    ),
    include_page_numbers: bool = Query(
        False, description="Whether to include page numbers in output"
    ),
    azure_analysis: bool = Query(
        True, description="Whether to use Azure OpenAI for image analysis (if false, images are processed but not analyzed)"
    ),
    _: str = Depends(verify_api_key)  # Authentication dependency (not a parameter)
) -> Dict[str, Any]:
    """
    Parse PDF file and return enhanced markdown.

    Args:
        file: PDF file upload

    Returns:
        JSON response with markdown content and metadata

    Example response:
        {
            "success": true,
            "markdown": "# Document Title\\n\\n**Image 1:**\\n<image>...",
            "metadata": {
                "pages_processed": 5,
                "images_processed": 3,
                "tables_processed": 2,
                "text_length": 15420,
                "azure_analysis": true,
                "filename": "document.pdf"
            }
        }
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are supported.",
            )

        # Read file data
        logger.info(f"Processing PDF file: {file.filename}")
        pdf_data = await file.read()

        if not pdf_data:
            raise HTTPException(status_code=400, detail="Empty file received")

        # Create configuration from parameters
        config = ParseConfig(
            images_inline=images_inline,
            include_page_numbers=include_page_numbers,
            azure_analysis=azure_analysis,
        )

        # Parse PDF
        result: ParseResult = parser_service.parse_pdf_from_bytes(
            pdf_data, file.filename, config
        )

        if not result.success:
            raise HTTPException(
                status_code=422, detail=f"PDF processing failed: {result.error}"
            )

        # Return response
        response = {
            "success": True,
            "markdown": result.markdown,
            "metadata": {
                "pages_processed": result.pages_processed,
                "images_processed": result.images_processed,
                "tables_processed": result.tables_processed,
                "text_length": result.text_length,
                "azure_analysis": result.azure_analysis,
                "filename": file.filename,
            },
        }

        logger.info(
            f"✅ Successfully processed {file.filename}: "
            f"{result.pages_processed} pages, "
            f"{result.images_processed} images, "
            f"{result.tables_processed} tables"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Unexpected error processing {file.filename if file else 'unknown'}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/parse-pdf-file")
async def parse_pdf_file(
    file: UploadFile = File(..., description="PDF file to parse"),
    images_inline: bool = Query(
        True, description="Whether to include images inline in markdown"
    ),
    include_page_numbers: bool = Query(
        False, description="Whether to include page numbers in output"
    ),
    azure_analysis: bool = Query(
        True, description="Whether to use Azure OpenAI for image analysis"
    ),
    _: str = Depends(verify_api_key)  # Authentication dependency
):
    """
    Parse PDF and return markdown as downloadable .md file.
    
    Returns the markdown content directly as a file download.
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are supported.",
            )

        # Read file data
        logger.info(f"Processing PDF file for download: {file.filename}")
        pdf_data = await file.read()

        if not pdf_data:
            raise HTTPException(status_code=400, detail="Empty file received")

        # Create configuration from parameters
        config = ParseConfig(
            images_inline=images_inline,
            include_page_numbers=include_page_numbers,
            azure_analysis=azure_analysis,
        )

        # Parse PDF
        result: ParseResult = parser_service.parse_pdf_from_bytes(
            pdf_data, file.filename, config
        )

        if not result.success:
            raise HTTPException(
                status_code=422, detail=f"PDF processing failed: {result.error}"
            )

        # Generate filename
        base_name = file.filename.rsplit('.', 1)[0] if file.filename else "document"
        markdown_filename = f"{base_name}.md"

        # Return markdown as downloadable file
        return Response(
            content=result.markdown or "",
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={markdown_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing {file.filename if file else 'unknown'}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
