"""
Shared Configuration for PDF Parsers
Configuration settings used by both multimodal CLI parser and API service
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== AZURE OPENAI CONFIGURATION =====
AZURE_CONFIG = {
    "api_key": os.getenv("AZURE_API_KEY"),
    "endpoint": os.getenv("AZURE_API_BASE"), 
    "api_version": "2024-10-01-preview",
    "deployment_name": "gpt-4.1"
}

# ===== PROCESSING CONFIGURATION =====
PROCESSING_CONFIG = {
    "process_images": True,
    "max_image_size": 20*1024*1024,  # 20MB
    "max_pdf_size": 100*1024*1024,  # 100MB maximum PDF file size
    "supported_formats": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"],
    "images_inline": True,  # If True, place images inline. If False, place at end
    "image_analysis_prompt": """Analyze this image for document search and data extraction.

## Initial Assessment:
First, quickly assess the image:
- **If trivial/decorative** (logos, icons, decorative elements, generic stock photos): Provide a brief one-line description
- **If simple/basic** (single text block, simple screenshot, basic photo): Provide a short paragraph description
- **If data-rich** (tables, charts, diagrams, structured content): Follow detailed analysis below

---

## For Trivial/Simple Images:

### Format:
**Type:** [DECORATIVE/SIMPLE/SCREENSHOT/PHOTO]
**Description:** [Brief description of content and relevance]

Example:
**Type:** [DECORATIVE]
**Description:** Company logo watermark, no data content

---

## For Data-Rich Images - Detailed Analysis:

### Analysis Instructions:

1. **For Tables:**
   - Extract the complete table structure with all rows and columns
   - Preserve the original column headers exactly
   - Maintain row order and relationships
   - Note any merged cells or special formatting

2. **For Charts/Graphs:**
   - Identify chart type (bar, line, pie, scatter, etc.)
   - Extract all data points with their exact values
   - Include axis labels, units, and scales
   - Note legend information and color/pattern associations
   - Capture any trend lines or annotations

3. **For Diagrams:**
   - Describe the diagram type and structure
   - Extract all text labels and their relationships
   - Note connections, flows, or hierarchies
   - Include any numerical values or percentages

### Output Format (Use Markdown):

#### 1. Content Type
Specify: `[TABLE]`, `[CHART: type]`, `[DIAGRAM: type]`, or `[MIXED]`

#### 2. Title/Caption
**Title:** [Extract main title]
**Caption/Description:** [Any subtitle or description]

#### 3. Extracted Data

##### For Tables:
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```

##### For Charts:
**Chart Type:** [Bar/Line/Pie/etc.]
**X-Axis:** [Label (Unit)]
**Y-Axis:** [Label (Unit)]

**Data Points:**
- Series 1: Label
  - Point A: Value
  - Point B: Value
- Series 2: Label
  - Point A: Value
  - Point B: Value

##### For Pie Charts:
**Total:** [If shown]
| Category | Value | Percentage |
|----------|-------|------------|
| Item 1   | 100   | 25%        |
| Item 2   | 300   | 75%        |

#### 4. Key Insights
- Notable trends or patterns
- Highest/lowest values
- Important relationships

#### 5. Data Quality Notes
- Any unclear or ambiguous elements
- Missing data marked as [unclear] or [missing]
- Approximations marked with ~

## Special Instructions:
- If text is partially obscured, mark with [partial: visible_text...]
- For illegible content, use [illegible]
- Preserve original language but add translations in parentheses if needed
- Include all footnotes, sources, and references
- For complex nested tables, use indentation or sub-tables
- If colors are significant, note them: [blue bar], [red line]

## Priority Guidelines:
- **Skip detailed analysis for:** Page numbers, headers/footers, decorative borders, standard icons
- **Brief description for:** Simple text paragraphs, basic photos without data, UI screenshots without data
- **Full analysis for:** Any image containing numbers, statistics, relationships, or structured information

Be precise and avoid repetition. Use the appropriate level of detail based on the image's content value."""
}

# ===== OUTPUT CONFIGURATION =====
OUTPUT_CONFIG = {
    "include_page_numbers": True,  # If True, add page numbers to content
    "include_tables_section": False,  # If True, add "## 📊 Tables" section at end
    "include_images_section": False,  # If True, add "## 🖼️ Images and Figures" section (when images not inline)
    "cleanup_markdown": True,  # If True, clean up excessive whitespace and formatting issues
}

# ===== MARKDOWN FORMATTING CONFIGURATION =====
# NOTE: Set any template to empty string ("") to disable that formatting element
FORMATTING_CONFIG = {
    # Page numbering format
    "page_marker_template": "--- Page {page_num} ---",  # Template for page markers (empty = no page markers)
    "page_placeholder": "___PAGE_BREAK_MARKER___",     # Internal placeholder for processing
    
    # Image formatting
    "image_wrapper_start": "<image>",                   # Opening tag for image descriptions
    "image_wrapper_end": "</image>",                    # Closing tag for image descriptions
    "image_title_template": "**Image {image_num}:**",   # Template for image titles (empty = no titles, inline mode)
    "image_header_template": "### Image {image_num}",   # Template for image headers (empty = no headers, section mode)
    
    # Table formatting  
    "table_header_template": "### Table {table_num}",   # Template for table headers (empty = no headers)
    "table_size_template": "**Size:** {rows} rows × {cols} columns",  # Template for table size info (empty = no size info)
    
    # Section headers
    "images_section_header": "## 🖼️ Images and Figures",  # Header for images section (empty = no section header)
    "tables_section_header": "## 📊 Tables",               # Header for tables section (empty = no section header)
    
    # Cleanup configuration
    "max_consecutive_linebreaks": 2,                    # Maximum allowed consecutive line breaks
    "preserve_code_blocks": True,                       # Preserve formatting in code blocks
    "normalize_whitespace": True,                       # Remove trailing spaces and normalize tabs
    "fix_heading_spacing": True,                        # Ensure proper spacing around headings
}
