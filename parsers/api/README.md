# 🚀 PDF Parser API

FastAPI-based service for converting PDF files to enhanced Markdown with AI image analysis.

## 📁 Project Structure

This API uses **shared configuration** from the parent directory:
- `../config.py` - Centralized configuration for all parsers
- `../pdf_utils.py` - Shared utility functions for PDF processing
- `parser_service.py` - API-specific service logic
- `main.py` - FastAPI application

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in the **parent directory** (`parsers/.env`):

```env
# Required: API Authentication
PDF_PARSER_API_KEY=your-secret-api-key-here

# Optional: Azure OpenAI for image analysis
AZURE_API_KEY=your_azure_openai_api_key
AZURE_API_BASE=https://your_resource.openai.azure.com/
```

**Note:** Configuration is now centralized in `../config.py` which loads these environment variables.

### 3. Start Server

```bash
python main.py
```

Server runs at: <http://localhost:8000>

## 📡 API Usage

### Parse PDF (JSON Response)

```bash
curl -X POST "http://localhost:8000/parse-pdf" \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Parse PDF (Download .md File)

```bash
curl -X POST "http://localhost:8000/parse-pdf-file" \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -o "document.md"
```

**Parameters:**
- `azure_analysis`: Use AI for image analysis (default: true)
- `images_inline`: Include images inline in markdown (default: true)  
- `include_page_numbers`: Add page markers (default: false)

**JSON Response:**
```json
{
  "success": true,
  "markdown": "# Document\n\n**Image 1:**\n<image>\nSubject: Logo\n</image>\n\nContent...",
  "metadata": {
    "pages_processed": 5,
    "images_processed": 3,
    "tables_processed": 2
  }
}
```

## 🔧 Configuration

All configuration is managed through the shared `../config.py` file:

- **Azure OpenAI**: Image analysis with GPT-4.1
- **Processing**: File size limits, image formats
- **Output**: Page numbering, cleanup options
- **Formatting**: Markdown templates and styling

Modify `../config.py` to customize parser behavior across both CLI and API.

## 📊 Features

- ✅ **PDF to Markdown** conversion with Docling
- ✅ **AI Image Analysis** with Azure OpenAI GPT-4.1  
- ✅ **Smart Data Extraction** from tables and charts
- ✅ **Shared Configuration** with CLI parser
- ✅ **Table Extraction** from PDF documents
- ✅ **API Authentication** with Bearer tokens
- ✅ **Interactive Docs** at `/docs`

Perfect for document processing and RAG systems!
