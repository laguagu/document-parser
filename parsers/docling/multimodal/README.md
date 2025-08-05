# 🤖 Advanced PDF Parser with AI Image Analysis

Advanced PDF parser using **Docling** + **Azure OpenAI GPT-4.1** with **Pydantic structured outputs**. Converts PDF files to enhanced Markdown with intelligent image analysis, automatic page numbering, and desi## 🔮 Future API Endpointrmatting.

## ✨ Features

- 🔍 **AI-Powered Image Analysis** - GPT-4.1 analyzes images with structured Pydantic outputs
- 📊 **Table Extraction** - Automatically extracts and formats tables from PDFs
- 📄 **Smart Page Numbers** - Accurate inline page markers using Docling's document structure
- 🎛️ **Flexible Configuration** - Fully configurable templates for all formatting elements
- 🏷️ **Image Tags** - Wraps image descriptions in `<image></image>` tags for easy parsing
- 🧹 **Markdown Cleanup** - Removes excessive whitespace and fixes formatting issues
- 🔒 **PDF Validation** - Built-in file size and format validation
- 🔄 **Retry Logic** - Automatic retry for Azure API calls with exponential backoff
- ⚙️ **Template System** - Use empty templates (`""`) to disable specific formatting elements

## 🚀 Quick Start

### Environment Setup

**Option 1: Using UV (recommended)**

```bash
# Install UV (recommended package manager)
pip install uv

# Create environment and install dependencies
# (ensure you are in the parsers/docling/multimodal directory)
uv venv
uv pip install -r requirements.txt
```

**Option 2: Using standard venv**

```bash
# Create virtual environment
python -m venv myenv

# Activate environment (Windows)
myenv\Scripts\Activate.ps1
# Or on Linux/Mac: source myenv/bin/activate

# Install dependencies
# (ensure you are in the parsers/docling/multimodal directory)
pip install -r requirements.txt
```

## Azure OpenAI Configuration

Create `.env` file with your credentials:

```env
AZURE_API_KEY=your_azure_openai_api_key
AZURE_API_BASE=https://your_resource.openai.azure.com/
```

## Basic Usage

```python
from main_with_images import AdvancedPDFParser

# Initialize parser
parser = AdvancedPDFParser()

# Parse PDF with default settings
result = parser.parse_pdf("input/document.pdf")

# Check results
if result['success']:
    print(f"✅ Processed {result['pages_processed']} pages")
    print(f"🖼️ Analyzed {result['images_processed']} images")
    print(f"📊 Found {result['tables_processed']} tables")
    print(f"📝 Output: {result['output_file']}")
```

## ⚙️ Configuration

All settings are configured at the top of `main_with_images.py`. Simply edit the configuration dictionaries to customize behavior.

### Processing Configuration

```python
PROCESSING_CONFIG = {
    "process_images": True,                  # Enable/disable image analysis
    "max_image_size": 20*1024*1024,         # 20MB max image size
    "max_pdf_size": 100*1024*1024,          # 100MB max PDF size
    "images_inline": True,                   # True: inline, False: at end
    "image_analysis_prompt": "..."           # Custom AI analysis prompt
}
```

### Output Configuration

```python
OUTPUT_CONFIG = {
    "include_page_numbers": True,            # Add page markers like "--- Page 1 ---"
    "include_tables_section": False,         # Add "## 📊 Tables" section at end
    "include_images_section": False,         # Add "## 🖼️ Images" section (when not inline)
    "cleanup_markdown": True,                # Clean up excessive whitespace
}
```

### Template Configuration (🆕 New Feature)

Control exactly what appears in your markdown by editing templates. **Set any template to `""` to disable that element:**

```python
FORMATTING_CONFIG = {
    # Page numbering
    "page_marker_template": "--- Page {page_num} ---",  # Empty = no page markers

    # Image formatting
    "image_wrapper_start": "<image>",                   # Opening tag
    "image_wrapper_end": "</image>",                    # Closing tag
    "image_title_template": "**Image {image_num}:**",   # Empty = no image titles

    # Table formatting
    "table_header_template": "### Table {table_num}",   # Empty = no table headers
    "table_size_template": "**Size:** {rows} rows × {cols} columns",

    # Section headers
    "images_section_header": "## 🖼️ Images and Figures",  # Empty = no section header
    "tables_section_header": "## 📊 Tables",

    # Cleanup settings
    "max_consecutive_linebreaks": 2,         # Max consecutive line breaks allowed
    "normalize_whitespace": True,            # Remove trailing spaces
    "fix_heading_spacing": True,             # Fix spacing around headings
}
```

## 📋 Usage Examples

### Example 1: Clean Output (No Extra Elements)

```python
# Edit FORMATTING_CONFIG in main_with_images.py:
"page_marker_template": "",                # No page numbers
"image_title_template": "",                # No image titles
"table_header_template": "",               # No table headers

# Result: Just content with <image>descriptions</image>
```

### Example 2: Custom Page Markers

```python
# Finnish page markers
"page_marker_template": "=== Sivu {page_num} ===",

# Or simple numbers
"page_marker_template": "Page {page_num}",

# Or disable completely
"page_marker_template": "",
```

### Example 3: Different Image Formats

```python
# Bold titles (default)
"image_title_template": "**Image {image_num}:**",

# Simple titles
"image_title_template": "Image {image_num}:",

# No titles, just descriptions
"image_title_template": "",
```

## 🏷️ Output Format

### With All Features Enabled

```markdown
## Document Title

**Image 1:**
<image>
Text content: WORLD ECONOMIC FORUM
Subject matter: Logo of the World Economic Forum organization
</image>

Content continues...

--- Page 1 ---

## Section Title

More content...

--- Page 2 ---

### Table 1

**Size:** 5 rows × 3 columns
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data... | Data... | Data... |
```

### With Minimal Configuration (Clean)

```markdown
## Document Title

<image>
Text content: WORLD ECONOMIC FORUM
Subject matter: Logo of the World Economic Forum organization
</image>

Content continues without page markers or extra headers...

<image>
Subject matter: Professional headshot photo
</image>

More content...
```

## 🔧 Advanced Features

### PDF Validation

The parser automatically validates PDFs:

- ✅ File size limits (configurable, default 100MB)
- ✅ Valid PDF header check
- ✅ File existence verification

### Retry Logic

Azure API calls include automatic retry with exponential backoff:

- 🔄 3 attempts maximum
- ⏱️ 1s, 2s, 4s delays
- 📝 Detailed logging of failures

### Markdown Cleanup

Automatic cleanup includes:

- 🧹 Removes excessive line breaks (configurable limit)
- 📏 Normalizes whitespace and tabs
- 📐 Fixes spacing around headings and page markers
- 🚫 Preserves code block formatting

## � File Structure

```
├── main_with_images.py      # Main parser with all features
├── requirements.txt         # Dependencies
├── README.md               # This documentation
├── .env                    # Azure credentials (create this)
├── input/                  # Place PDF files here
│   └── pdf-example.pdf     # Sample file
└── output/                 # Generated markdown files
    ├── pdf-example_inline.md     # Default output
    └── pdf-example_enhanced.md   # Alternative format
```

## 🔮 Future API Endpoint

This parser is designed to be easily converted to an API endpoint. The structured configuration and return values make it perfect for web service integration.
