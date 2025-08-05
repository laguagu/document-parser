# 📄 PDF Parsers

Collection of PDF parsing tools using different approaches and technologies.

## 📁 Available Parsers

### Docling-based Parsers

Located in `parsers/` directory:

- **`multimodal/`** - 🤖 **Advanced PDF Parser with AI Image Analysis**

  - Azure OpenAI GPT-4.1 integration
  - Intelligent image analysis with structured outputs
  - Configurable markdown formatting templates
  - Page numbering, table extraction, cleanup features
  - Full-featured parser for production use

- **`simple/`** - 📝 **Minimal Text Parser**

  - Basic PDF to markdown conversion
  - Lightweight and fast
  - No AI analysis or advanced features
  - Perfect for simple text extraction

- **`api/`** - 🚀 **FastAPI REST Endpoint**

  - RESTful API with Bearer token authentication
  - JSON response or direct .md file download
  - Azure OpenAI GPT-4.1 integration for image analysis
  - Configurable parameters (images_inline, page_numbers, azure_analysis)
  - Perfect for web applications and integrations

## 🚀 Quick Start

Choose the parser that fits your needs:

- **Need REST API?** → Use `api/` (FastAPI server)
- **Need AI image analysis?** → Use `multimodal/` (CLI)
- **Just want text extraction?** → Use `simple/` (CLI)

See individual README files in each directory for detailed setup instructions.
