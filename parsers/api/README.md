# 🚀 PDF Parser API

FastAPI-ba## 📡 API Usage

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

**JSON Response:**converting PDF files to enhanced Markdown with AI image analysis.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
# Required: API Authentication
PDF_PARSER_API_KEY=your-secret-api-key-here

# Optional: Azure OpenAI for image analysis
AZURE_API_KEY=your_azure_openai_api_key
AZURE_API_BASE=https://your_resource.openai.azure.com/
```

### 3. Start Server

```bash
python main.py
```

Server runs at: <http://localhost:8000>

## � API Usage

### Parse PDF

```bash
curl -X POST "http://localhost:8000/parse-pdf" \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

**Parameters:**
- `azure_analysis`: Use AI for image analysis (default: true)
- `images_inline`: Include images inline in markdown (default: true)  
- `include_page_numbers`: Add page markers (default: false)

**Response:**
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

## 📊 Features

- ✅ **PDF to Markdown** conversion with Docling
- ✅ **AI Image Analysis** with Azure OpenAI GPT-4.1
- ✅ **Table Extraction** from PDF documents
- ✅ **API Authentication** with Bearer tokens
- ✅ **Interactive Docs** at `/docs`

Perfect for document processing and RAG systems!
