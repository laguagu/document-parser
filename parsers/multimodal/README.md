# 📄 Advanced PDF Parser (CLI)

Command-line PDF parser using Docling + Azure OpenAI for document analysis with AI-powered image analysis.

## 📁 Project Structure

This CLI parser uses **shared configuration** with the API:

- `../config.py` - Centralized configuration for all parsers
- `../pdf_utils.py` - Shared utility functions for PDF processing  
- `main.py` - Command-line interface

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in the **parent directory** (`parsers/.env`):

```env
# Optional: Azure OpenAI for image analysis
AZURE_API_KEY=your_azure_openai_api_key
AZURE_API_BASE=https://your_resource.openai.azure.com/
```

**Note:** Configuration is now centralized in `../config.py` which loads these environment variables.

### 3. Add Your PDF

Place your PDF file in the `input/` directory:
```
input/
  pdf-example.pdf
  your-document.pdf
```

### 4. Run Parser

```bash
uv run main.py input/your-document.pdf
```

Results will be saved to the `output/` directory.

## 🔧 Configuration

All configuration is managed through the shared `../config.py` file:

### Key Settings:

- **Azure OpenAI**: GPT-4.1 model for intelligent image analysis
- **Processing**: Smart image analysis prompts that adapt to content
- **Output**: Page numbering, cleanup options, section headers
- **Formatting**: Markdown templates and styling

### Modify Behavior:

Edit `../config.py` to customize:

- Image analysis prompts (now intelligently handles trivial vs data-rich images)
- Output formatting templates
- File size and processing limits
- Page numbering and section organization

## 📊 Features

- ✅ **PDF to Markdown** conversion with Docling
- ✅ **AI Image Analysis** with Azure OpenAI GPT-4.1
- ✅ **Smart Data Extraction** from tables and charts
- ✅ **Shared Configuration** with API service
- ✅ **Table Extraction** and formatting
- ✅ **Page Number** insertion
- ✅ **Markdown Cleanup** and optimization

## 💡 Usage Examples

The parser automatically:

1. Extracts text and structure from PDFs
2. Identifies and analyzes images/charts with AI
3. Extracts tables and preserves formatting
4. Links data points to their labels in charts
5. Generates clean, searchable Markdown

Perfect for:

- Document processing pipelines
- RAG (Retrieval Augmented Generation) systems
- Research paper analysis
- Business document digitization

## � Shared Architecture

This CLI parser shares utilities with the API service, ensuring consistent behavior:

- Same image analysis logic
- Identical configuration options
- Shared PDF processing pipeline
- Common utility functions

Changes to `../config.py` affect both CLI and API automatically.

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

### 📂 File Structure

```
├── main.py                   # Main parser script
├── requirements.txt          # Dependencies
├── .env                     # Azure credentials (create this)
├── input/                   # Place PDF files here
│   └── pdf-example.pdf      # Default input file (script looks for this)
└── output/                  # Generated markdown files
    ├── pdf-example_inline.md     # Result with inline images
    └── pdf-example_enhanced.md   # Result with images at end
```

**Input:** Script looks for `input/pdf-example.pdf` by default  
**Output:** Results saved to `output/` with automatic naming based on processing mode

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

```bash
# Run with default settings
uv run main.py input/document.pdf

# Or just place your PDF in input/ and run:
uv run main.py
```

The parser will automatically:

1. Extract text and structure from PDFs
2. Intelligently analyze images (brief for decorative, detailed for data-rich)
3. Extract tables and preserve formatting
4. Generate clean, searchable Markdown

Perfect for RAG systems and document processing pipelines.

## ⚙️ Configuration

All settings are configured in the shared `../config.py` file. The configuration includes:

- **Smart Image Analysis**: Automatically adapts analysis depth based on content type
- **Azure OpenAI Integration**: GPT-4.1 for intelligent image understanding  
- **Output Formatting**: Customizable templates and cleanup options
- **Processing Limits**: File size and format validation

### Advanced Configuration

Edit `../config.py` to customize behavior:

- Modify image analysis prompts
- Adjust output formatting templates  
- Set file size limits
- Configure Azure OpenAI settings

The configuration is shared between CLI and API for consistency.

## 📋 Usage Examples

### Example 1: Basic Usage

```bash
# Parse a specific PDF
uv run main.py input/document.pdf

# Parse default PDF (looks for pdf-example.pdf)
uv run main.py
```

### Example 2: Custom Configuration

Edit `../config.py` to customize:

- **Smart image analysis**: Handles trivial vs data-rich images automatically
- **Output formatting**: Page markers, image titles, section headers
- **Processing limits**: File sizes, image formats
- **Azure settings**: API keys, model configuration

### Example 3: Understanding Output

The parser automatically categorizes images:

- **Decorative images**: Brief description (logos, icons, decorations)
- **Data-rich images**: Full analysis (charts, tables, diagrams)
- **Simple content**: Moderate detail (screenshots, basic photos)

## 🏷️ Output Format

### Intelligent Image Analysis

The parser now automatically adapts analysis depth:

```markdown
## Document Title

**Image 1:**
<image>
**Type:** [DECORATIVE]
**Description:** Company logo, no data content.
</image>

Content continues...

**Image 2:**
<image>
#### 1. Content Type
[CHART: Horizontal Bar Chart]

#### 2. Title/Caption
**Title:** Market Share Analysis
**Caption:** Quarterly performance data

#### 3. Extracted Data
| Product | Q1 | Q2 | Q3 | Q4 |
|---------|----|----|----|----|
| Product A | 25% | 30% | 35% | 40% |
| Product B | 75% | 70% | 65% | 60% |

#### 4. Key Insights
- Product A shows consistent growth throughout the year
- Product B shows declining market share

#### 5. Data Quality Notes
- All values clearly visible
- No missing data points
</image>

--- Page 1 ---

More content...
```

### Benefits for RAG Systems

- **Trivial images**: Quick processing, no information overload
- **Data-rich images**: Comprehensive extraction for accurate search
- **Structured output**: Easy to parse and index for vector databases

## 🔧 Advanced Features

### Smart Image Analysis

The enhanced image analysis now features:

- 🎯 **Automatic Content Detection**: Distinguishes decorative, simple, and data-rich images
- 📊 **Structured Data Extraction**: Comprehensive analysis for charts, tables, and diagrams  
- ⚡ **Efficient Processing**: Brief descriptions for trivial content, detailed analysis when needed
- 🎨 **Color Recognition**: Notes significant colors in charts and diagrams

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

## 🔮 Integration Ready

This parser is designed for seamless integration:

- **Shared Configuration**: Same settings work for both CLI and API
- **Consistent Output**: Identical processing logic across environments  
- **RAG Optimized**: Perfect for vector databases and search systems
- **API Ready**: Easy conversion to web service endpoints
