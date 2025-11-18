# DOCX Document Parser Tool

## Overview

The DOCX Document Parser is a comprehensive tool for parsing Microsoft Word documents (.docx), extracting metadata, and managing document content with intelligent caching. It enables both users and agents to efficiently work with DOCX documents by providing structured access to document content through pages or sections.

This tool is designed with flexibility in mind, allowing for complete preservation of document content while maintaining the ability to reconstruct the original document from parsed data (though reconstruction is not currently implemented).

## Key Features

- **Complete Document Parsing**: Extracts all content from DOCX documents including text, headings, and images
- **Metadata Extraction**: Retrieves document metadata such as page count, character count, section count, and image count
- **Section-Based Organization**: Automatically identifies document sections based on heading styles and splits content accordingly
- **Local Caching**: Caches parsed content locally in a structured format for fast retrieval
- **Flexible Content Retrieval**: Access content by page number or section title
- **Image Processing**: Extracts and saves embedded images with options to return base64-encoded data or file paths
- **Job Management**: Uses unique job IDs to manage multiple parsed documents simultaneously
- **Cache Management**: Provides utilities to clean up cached data when no longer needed

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Required Dependencies

Install the required packages using pip:

```bash
pip install python-docx Pillow strands
```

**Package details:**
- `python-docx`: For parsing DOCX documents
- `Pillow`: For image processing and manipulation
- `strands`: For tool decoration and SDK compliance

## Architecture

### Cache Structure

The tool uses a hierarchical cache structure:

```
.cache/docx_parser/
└── {job_id}/
    ├── metadata.json          # Document metadata
    ├── sections/              # Section content files
    │   ├── section_1.json
    │   ├── section_2.json
    │   └── ...
    └── images/                # Extracted images
        ├── image_001.png
        ├── image_002.jpg
        └── ...
```

### Page Estimation

Page counts are estimated based on:
- Character count (approximately 3000 characters per page)
- Image count (approximately 2 images per page)

**Note**: Page estimation is approximate and may differ from actual page counts in Word.

## API Documentation

### 1. parse_document

Parses a DOCX document and extracts comprehensive metadata.

**Function Signature:**
```python
@tool
def parse_document(doc_path: str, job_id: Optional[str] = None) -> str
```

**Parameters:**
- `doc_path` (str, required): Path to the DOCX document file
- `job_id` (str, optional): Custom job ID. If not provided, a UUID will be generated automatically

**Returns:**
JSON string containing:
- `status`: Operation status ("success" or "error")
- `job_id`: Unique identifier for this parsing job
- `document`: Dictionary with metadata
  - `page_count`: Estimated number of pages
  - `char_count`: Total character count
  - `section_count`: Number of sections identified
  - `image_count`: Number of images extracted
- `sections`: Array of section objects with `id`, `title`, and `level`
- `images`: Array of image objects with `id` and `filename`

**Example:**
```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import parse_document

# Parse a document
result = parse_document("./documents/sample.docx")
print(result)

# Output:
# {
#   "status": "success",
#   "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "document": {
#     "page_count": 10,
#     "char_count": 28500,
#     "section_count": 5,
#     "image_count": 3
#   },
#   "sections": [
#     {"id": "section_1", "title": "Introduction", "level": 1},
#     {"id": "section_2", "title": "Methodology", "level": 1}
#   ],
#   "images": [
#     {"id": "image_001", "filename": "image_001.png"},
#     {"id": "image_002", "filename": "image_002.jpg"}
#   ]
# }
```

**Error Handling:**
- Returns error if file does not exist
- Returns error if file is not a valid DOCX document
- Returns error for parsing failures

---

### 2. get_page_content

Retrieves content for a specific page number.

**Function Signature:**
```python
@tool
def get_page_content(job_id: str, page_num: int) -> str
```

**Parameters:**
- `job_id` (str, required): Job ID from parse_document
- `page_num` (int, required): Page number to retrieve (1-indexed)

**Returns:**
JSON string containing:
- `status`: Operation status
- `job_id`: Job identifier
- `page`: Requested page number
- `content`: Array of content items on this page
  - `index`: Content index
  - `type`: Content type (e.g., "paragraph")
  - `text`: Text content
  - `is_heading`: Boolean indicating if this is a heading
  - `heading_level`: Heading level (0 if not a heading)
- `sections`: Array of sections that appear on this page

**Example:**
```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import get_page_content

# Get content from page 2
result = get_page_content("a1b2c3d4-e5f6-7890-abcd-ef1234567890", 2)
print(result)

# Output:
# {
#   "status": "success",
#   "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "page": 2,
#   "content": [
#     {
#       "index": 15,
#       "type": "paragraph",
#       "text": "This is the content on page 2...",
#       "is_heading": false,
#       "heading_level": 0
#     }
#   ],
#   "sections": [
#     {"id": "section_2", "title": "Methodology", "level": 1}
#   ]
# }
```

**Error Handling:**
- Returns error if job_id does not exist
- Returns error if page_num is out of range

---

### 3. get_section_content

Retrieves all content from a specific section by title.

**Function Signature:**
```python
@tool
def get_section_content(job_id: str, section_title: str) -> str
```

**Parameters:**
- `job_id` (str, required): Job ID from parse_document
- `section_title` (str, required): Exact title of the section to retrieve

**Returns:**
JSON string containing:
- `status`: Operation status
- `job_id`: Job identifier
- `section`: Section metadata
  - `id`: Section identifier
  - `title`: Section title
  - `level`: Heading level
- `content`: Array of all content items in this section
- `images`: Array of images in the document

**Example:**
```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import get_section_content

# Get content from "Introduction" section
result = get_section_content("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "Introduction")
print(result)

# Output:
# {
#   "status": "success",
#   "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "section": {
#     "id": "section_1",
#     "title": "Introduction",
#     "level": 1
#   },
#   "content": [
#     {
#       "index": 0,
#       "type": "paragraph",
#       "text": "Introduction",
#       "is_heading": true,
#       "heading_level": 1
#     },
#     {
#       "index": 1,
#       "type": "paragraph",
#       "text": "This document introduces...",
#       "is_heading": false,
#       "heading_level": 0
#     }
#   ],
#   "images": [...]
# }
```

**Error Handling:**
- Returns error if job_id does not exist
- Returns error if section_title is not found

---

### 4. get_image

Retrieves a specific image from the document.

**Function Signature:**
```python
@tool
def get_image(job_id: str, image_id: str, return_type: str = "path") -> str
```

**Parameters:**
- `job_id` (str, required): Job ID from parse_document
- `image_id` (str, required): Image ID (e.g., "image_001")
- `return_type` (str, optional): Return format - "base64" or "path" (default: "path")

**Returns:**
JSON string containing:
- `status`: Operation status
- `job_id`: Job identifier
- `image_id`: Image identifier
- `return_type`: Format used for return
- `data` (if base64): Base64-encoded image data
- `path` (if path): File system path to image
- `format`: Image format (png, jpg, etc.)

**Example (Path):**
```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import get_image

# Get image as file path
result = get_image("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "image_001", "path")
print(result)

# Output:
# {
#   "status": "success",
#   "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "image_id": "image_001",
#   "return_type": "path",
#   "path": ".cache/docx_parser/a1b2c3d4-e5f6-7890-abcd-ef1234567890/images/image_001.png",
#   "format": "png"
# }
```

**Example (Base64):**
```python
# Get image as base64
result = get_image("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "image_001", "base64")
print(result)

# Output:
# {
#   "status": "success",
#   "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "image_id": "image_001",
#   "return_type": "base64",
#   "data": "iVBORw0KGgoAAAANSUhEUgAAA...",
#   "format": "png"
# }
```

**Error Handling:**
- Returns error if job_id does not exist
- Returns error if image_id is not found
- Returns error if image file is missing

---

### 5. clean_cache

Removes all cached data for a specific job.

**Function Signature:**
```python
@tool
def clean_cache(job_id: str) -> str
```

**Parameters:**
- `job_id` (str, required): Job ID to clean

**Returns:**
JSON string containing:
- `status`: Operation status
- `message`: Confirmation message

**Example:**
```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import clean_cache

# Clean cache for a job
result = clean_cache("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
print(result)

# Output:
# {
#   "status": "success",
#   "message": "Cache cleaned for job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890"
# }
```

**Error Handling:**
- Returns error if job_id does not exist

## Usage Examples

### Complete Workflow Example

```python
from tools.generated_tools.tool_build_docx_parser.docx_parser import (
    parse_document, 
    get_page_content, 
    get_section_content, 
    get_image, 
    clean_cache
)
import json

# Step 1: Parse the document
print("Parsing document...")
parse_result = json.loads(parse_document("./documents/report.docx"))
job_id = parse_result["job_id"]
print(f"Job ID: {job_id}")
print(f"Pages: {parse_result['document']['page_count']}")
print(f"Sections: {parse_result['document']['section_count']}")

# Step 2: Get content from first page
print("\nRetrieving page 1 content...")
page_content = json.loads(get_page_content(job_id, 1))
print(f"Page 1 has {len(page_content['content'])} content items")

# Step 3: Get content from a specific section
print("\nRetrieving section content...")
section_name = parse_result['sections'][0]['title']
section_content = json.loads(get_section_content(job_id, section_name))
print(f"Section '{section_name}' has {len(section_content['content'])} paragraphs")

# Step 4: Get an image if available
if parse_result['images']:
    print("\nRetrieving first image...")
    image_id = parse_result['images'][0]['id']
    
    # Get as file path
    image_path = json.loads(get_image(job_id, image_id, "path"))
    print(f"Image path: {image_path['path']}")
    
    # Get as base64
    image_base64 = json.loads(get_image(job_id, image_id, "base64"))
    print(f"Image base64 length: {len(image_base64['data'])} characters")

# Step 5: Clean up when done
print("\nCleaning cache...")
clean_result = json.loads(clean_cache(job_id))
print(clean_result['message'])
```

### Agent Integration Example

```python
# Example of how an agent might use this tool
def process_document_for_agent(doc_path: str):
    """Process a document and extract key information for an agent."""
    
    # Parse document
    result = json.loads(parse_document(doc_path))
    
    if result.get("error"):
        return f"Error: {result['message']}"
    
    job_id = result['job_id']
    
    # Extract all section titles
    sections = result['sections']
    
    # Get content from each section
    all_content = {}
    for section in sections:
        section_data = json.loads(get_section_content(job_id, section['title']))
        all_content[section['title']] = section_data['content']
    
    # Clean up
    clean_cache(job_id)
    
    return all_content
```

## Error Handling

All functions return JSON strings with consistent error formatting:

```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

Common error types:
- **File not found**: Document path does not exist
- **Invalid file format**: File is not a DOCX document
- **Invalid DOCX file**: File is corrupted or not a valid DOCX
- **Job not found**: No cached data exists for the given job_id
- **Invalid page number**: Page number is out of range
- **Section not found**: Section title does not exist
- **Image not found**: Image ID does not exist
- **Image file not found**: Image file is missing from cache

## Limitations and Notes

1. **Page Count Estimation**: Page counts are estimated based on character and image counts. Actual page counts may vary depending on formatting, fonts, and layout.

2. **Section Recognition**: Sections are identified based on Word heading styles (Heading 1-6, Title). Documents without proper heading styles may not be split correctly.

3. **Image Support**: Only embedded images are supported. Images linked from external sources are not extracted.

4. **Document Reconstruction**: While the tool is designed to preserve all content for potential reconstruction, the reconstruction functionality is not currently implemented.

5. **Cache Management**: Cached data persists until explicitly cleaned. Monitor cache size for large documents or high-volume usage.

6. **Concurrent Access**: The tool does not currently handle concurrent access to the same job_id. Ensure sequential processing for the same document.

## Technical Details

### Supported Document Elements

- Paragraphs (text content)
- Headings (Heading 1-6, Title styles)
- Images (PNG, JPEG, GIF, BMP)
- Tables (as paragraph content)

### Character Encoding

All text content is processed with UTF-8 encoding to support international characters.

### File Format Support

- **Supported**: .docx (Office Open XML)
- **Not Supported**: .doc (legacy Word format), .rtf, .odt

## Troubleshooting

### Issue: "File not found" error
**Solution**: Verify the document path is correct and the file exists. Use absolute paths to avoid ambiguity.

### Issue: Section not found
**Solution**: Ensure the section title exactly matches (case-sensitive). Use the sections list from parse_document to get exact titles.

### Issue: Page content is empty
**Solution**: The page may be outside the estimated page range. Check the page_count from parse_document results.

### Issue: Images not extracted
**Solution**: Verify images are embedded in the document (not linked). Only embedded images are extracted.

## Contributing

This tool was generated by the Tool Build Workflow system. For enhancements or bug reports, please follow the standard workflow contribution guidelines.

## License

This tool is part of the nexus-ai platform and follows the platform's licensing terms.

## Version History

- **v1.0.0** (2025-11-18): Initial release
  - Document parsing and metadata extraction
  - Section-based content splitting and caching
  - Page-based content retrieval
  - Section-based content retrieval
  - Image extraction with base64/path options
  - Cache management utilities