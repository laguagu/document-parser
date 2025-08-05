# 📄 Document Parser Project

Advanced PDF parsing system with both CLI and API interfaces, featuring AI-powered image analysis and shared configuration architecture.

## 📁 Project Structure

```text
parsers/
├── config.py              # 🔧 Shared configuration (Azure, formatting, etc.)
├── pdf_utils.py           # 🛠️ Shared utility functions
├── .env                   # 🔐 Environment variables (create this)
├── multimodal/            # 📄 CLI Parser
│   ├── main.py           
│   ├── requirements.txt   
│   ├── input/            # 📂 Put your PDFs here
│   └── output/           # 📂 Generated Markdown files
└── api/                   # 🚀 REST API Service
    ├── main.py           
    ├── parser_service.py  
    └── requirements.txt   
```

## 🏗️ Shared Architecture

This project uses a **centralized configuration** approach:

### 🔧 `config.py` - Central Configuration

- Azure OpenAI settings
- Processing parameters (file sizes, formats)
- Smart image analysis prompts that adapt to content type
- Output formatting templates
- Markdown cleanup rules

### 🛠️ `pdf_utils.py` - Shared Utilities

- PDF validation functions
- Intelligent image analysis with Azure GPT-4.1
- Table and image extraction
- Markdown cleanup and formatting
- Page numbering logic

Changes to configuration automatically affect both CLI and API!

## 🚀 Quick Start

### 1. Environment Setup

Create `parsers/.env`:

```env
# Required for API authentication
PDF_PARSER_API_KEY=your-secret-api-key-here

# Optional for AI image analysis
AZURE_API_KEY=your_azure_openai_api_key
AZURE_API_BASE=https://your_resource.openai.azure.com/
```

### 2. Choose Your Interface

**CLI Usage** (multimodal/):

```bash
cd parsers/multimodal

# Option 1: Using uv (recommended)
pip install uv
uv venv
uv pip install -r requirements.txt
uv run main.py input/your-document.pdf

# Option 2: Traditional virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python main.py input/your-document.pdf
```

**API Usage** (api/):

```bash
cd parsers/api

# Option 1: Using uv (recommended)  
pip install uv
uv venv
uv pip install -r requirements.txt
uv run main.py

# Option 2: Traditional virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python main.py
# Server at http://localhost:8000
```

**Note:** Each interface has its own `requirements.txt` with specific dependencies.

## 📊 Features

### Core Capabilities

- ✅ **PDF to Markdown** conversion with Docling
- ✅ **AI Image Analysis** with Azure OpenAI GPT-4.1
- ✅ **Smart Data Extraction** from tables and charts
- ✅ **Table Extraction** with proper formatting
- ✅ **Page Numbering** with customizable templates
- ✅ **Markdown Cleanup** and optimization

### Advanced Features

- 🎯 **Smart Image Analysis**: Automatically adapts analysis depth based on content type
- � **Structured Data Extraction**: Comprehensive analysis for charts, tables, and diagrams  
- ⚡ **Efficient Processing**: Brief descriptions for trivial content, detailed analysis when needed
- 🔄 **Retry Logic**: Robust Azure API error handling

## 🔧 Configuration

Edit `config.py` to customize behavior:

```python
# Smart image analysis prompt
PROCESSING_CONFIG = {
    "image_analysis_prompt": """Your custom prompt here..."""
}

# Output formatting
FORMATTING_CONFIG = {
    "image_title_template": "**Figure {image_num}:**",  # Custom image titles
    "page_marker_template": "=== Page {page_num} ===",  # Custom page markers
    "image_wrapper_start": "[IMAGE]",                   # Custom image tags
}

# Disable features (set to empty string)
FORMATTING_CONFIG = {
    "page_marker_template": "",        # Disable page numbers
    "image_title_template": "",        # Disable image titles
}
```
