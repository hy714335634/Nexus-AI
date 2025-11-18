---
name: docx-document-parsing
description: Parse and extract content from Microsoft Word DOCX documents, including metadata, sections, pages, and images with structured caching for efficient retrieval
---

# DOCX Document Parsing

Use this skill when you need to analyze, extract, or retrieve content from Microsoft Word DOCX documents. This skill enables you to parse documents comprehensively, access specific sections or pages, extract images, and manage cached document data efficiently.

## When to Use This Skill

Activate this skill when:

- A user needs to extract information from a DOCX document
- You need to analyze document structure, sections, or metadata
- You want to retrieve specific pages or sections from a document
- You need to extract and process images from a document
- You're working with large documents and need efficient content access
- You need to preserve document content for later reconstruction
- You're building workflows that process multiple DOCX documents

## Core Capabilities

### 1. Document Parsing
Parse DOCX documents to extract comprehensive metadata including:
- Total page count (estimated)
- Character count
- Section structure with titles and hierarchy levels
- Embedded images with metadata
- Automatic section-based content splitting and caching

### 2. Content Retrieval by Page
Access document content by specific page numbers:
- Retrieve all paragraphs on a given page
- Identify sections that appear on the page
- Access both text content and structural information

### 3. Content Retrieval by Section
Access document content by section titles:
- Retrieve complete section content including all paragraphs
- Get section metadata (title, level, ID)
- Access images associated with sections

### 4. Image Processing
Extract and retrieve embedded images:
- Save images to local cache
- Return images as base64-encoded data for immediate use
- Return file paths for file system access
- Support for multiple image formats (PNG, JPEG, GIF, BMP)

### 5. Cache Management
Efficiently manage parsed document data:
- Structured local caching with job-based organization
- Clean up cache when documents are no longer needed
- Support for concurrent processing of multiple documents

## Usage Instructions

### Step 1: Parse the Document

Always start by parsing the document to create a cached version:

```
Use parse_document with the document file path. Optionally provide a custom job_id, or let the system generate one automatically. Save the returned job_id for subsequent operations.
```

**Key information from parsing:**
- `job_id`: Required for all subsequent operations
- `page_count`: Total estimated pages
- `sections`: List of section titles and structure
- `images`: List of available image IDs

### Step 2: Access Content

Choose the appropriate method based on user needs:

**For page-based access:**
```
Use get_page_content with the job_id and page number (1-indexed). This returns all content on the specified page.
```

**For section-based access:**
```
Use get_section_content with the job_id and exact section title. This returns all content within that section.
```

### Step 3: Retrieve Images (if needed)

If the document contains images:

```
Use get_image with the job_id and image_id. Specify return_type as "base64" for encoded data or "path" for file system path.
```

### Step 4: Clean Up

When finished processing:

```
Use clean_cache with the job_id to remove all cached data and free up storage.
```

## Examples

### Example 1: Extract Document Summary

**User Request:** "Give me a summary of the document structure in report.docx"

**Your Response:**
1. Parse the document: `parse_document("./report.docx")`
2. Extract metadata from the result: page count, section count, character count
3. List all section titles and their hierarchy
4. Mention if images are present
5. Clean cache when done

### Example 2: Get Specific Section Content

**User Request:** "Show me the content from the 'Methodology' section"

**Your Response:**
1. Parse the document first if not already parsed
2. Use `get_section_content(job_id, "Methodology")`
3. Present the content in a readable format
4. Mention any images in that section

### Example 3: Extract Images

**User Request:** "Extract all images from the document"

**Your Response:**
1. Parse the document to get the list of image IDs
2. For each image ID, use `get_image(job_id, image_id, "path")`
3. Provide the user with file paths or base64 data as requested
4. Report total number of images extracted

### Example 4: Page-by-Page Analysis

**User Request:** "Analyze the first 3 pages of the document"

**Your Response:**
1. Parse the document
2. Loop through pages 1-3 using `get_page_content(job_id, page_num)`
3. Analyze and summarize content from each page
4. Identify which sections appear on these pages

## Guidelines

### Best Practices

- **Always parse first**: Never attempt to retrieve content without first parsing the document
- **Use exact section titles**: Section retrieval is case-sensitive and requires exact matching
- **Validate job_id**: Check that parsing was successful before proceeding with content retrieval
- **Choose appropriate return type**: Use "path" for images when possible to reduce response size
- **Clean up after completion**: Always clean cache when the document processing is complete
- **Handle errors gracefully**: Check for error messages in responses and provide clear feedback to users

### Error Handling

When errors occur:
- Explain the error to the user in plain language
- Suggest corrective actions (e.g., "The section title 'Introduction' was not found. Available sections are: ...")
- Verify inputs (file paths, job IDs, page numbers) before retrying

### Performance Considerations

- **Large documents**: For very large documents, consider processing sections individually rather than retrieving all content at once
- **Images**: Use "path" return type for large images unless base64 encoding is specifically required
- **Cache management**: Clean cache regularly to prevent excessive storage usage
- **Concurrent jobs**: Each document parse creates a separate job_id, allowing parallel processing

### Limitations to Communicate

- **Page estimation**: Explain that page counts are estimates and may differ from Word's actual page count
- **Section recognition**: Sections are identified by heading styles; documents without proper formatting may not split correctly
- **Image support**: Only embedded images are extracted; linked images are not supported
- **No reconstruction**: While content is preserved, document reconstruction is not currently available

## Integration Patterns

### Pattern 1: Document Analysis Workflow
1. Parse document → 2. Get metadata → 3. Iterate through sections → 4. Analyze content → 5. Clean cache

### Pattern 2: Targeted Content Extraction
1. Parse document → 2. Identify target section/page → 3. Retrieve specific content → 4. Process content → 5. Clean cache

### Pattern 3: Image Extraction Pipeline
1. Parse document → 2. Get image list → 3. Extract each image → 4. Process/save images → 5. Clean cache

### Pattern 4: Multi-Document Processing
1. Parse document A (job_id_A) → 2. Parse document B (job_id_B) → 3. Process both → 4. Clean both caches

## Common User Intents

**"Parse this document"** → Use parse_document, provide summary of structure

**"Show me page X"** → Use get_page_content, present content clearly

**"What's in the [section] section?"** → Use get_section_content, format output

**"Extract the images"** → Parse, then use get_image for each image

**"How many pages/sections?"** → Parse and report metadata

**"Compare two sections"** → Retrieve both sections and analyze differences

**"Find content about [topic]"** → Parse, search through sections/pages

## Tips for Optimal Results

1. **Structure your workflow**: Parse once, retrieve multiple times, clean once
2. **Provide context**: When presenting content, include section titles and page numbers
3. **Be specific**: Use exact section titles and valid page numbers
4. **Batch operations**: When processing multiple items (pages, sections, images), plan the sequence efficiently
5. **User feedback**: Keep users informed about progress, especially for large documents
6. **Validate inputs**: Check file paths and formats before parsing
7. **Cache awareness**: Remember that job_ids remain valid until cache is cleaned

## Advanced Usage

### Selective Section Processing
For documents with many sections, ask the user which sections they're interested in before retrieving all content.

### Progressive Loading
For large documents, retrieve content incrementally (page by page or section by section) rather than all at once.

### Content Filtering
After retrieving content, apply filters or searches to find specific information the user needs.

### Metadata-Driven Decisions
Use metadata from parse_document to guide subsequent operations (e.g., skip image extraction if image_count is 0).
