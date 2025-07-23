# PDF Bundle Splitter

A Python tool that automatically splits multi-resume PDF bundles into individual resume files with cover letter removal.

## What It Does

- **Automatically detects** individual resumes within a bundled PDF
- **Extracts candidate information** from Table of Contents
- **Removes cover letters** automatically
- **Splits into individual PDFs** with clean, organized filenames

## Quick Setup

```bash
pip install PyPDF2 pdfplumber
```

## Usage

```python
from split_resumes import ResumeSplitter

# Initialize and run
splitter = ResumeSplitter("resume_bundle.pdf")
splitter.split_resumes()
```

Or edit the filename in `split_resumes.py` and run:
```bash
python split_resumes.py
```

## Input Requirements

Your PDF needs a Table of Contents with candidate names and IDs:

```
1. John Smith           C107479
2. Jane Doe             C107475
3. Bob Johnson          C107471
```

**Supported formats:**
- `1. Name C123456`
- `Name C123456` 
- `C123456 Name`

## Output

Creates organized files in `extracted_resumes/` folder:
```
01_John_Smith_C107479.pdf
02_Jane_Doe_C107475.pdf
03_Bob_Johnson_C107471.pdf
```

## Key Features

### Smart Detection
- **Multi-page TOC support** - Reads across multiple TOC pages
- **Flexible name matching** - Handles names split across lines
- **Case-insensitive** - Finds names regardless of capitalization
- **Multiple fallback methods** - 3-layer detection system

### Cover Letter Removal
- **20+ detection patterns** for common cover letter phrases
- **Automatic removal** of cover letter pages
- **Clean resume extraction** - Only saves actual resume content

## Performance

- **85-100% success rate** on standard resume bundles
- **Processing time**: ~30-60 seconds for 48 resumes
- **Handles**: 40+ resumes automatically

## Troubleshooting

**No candidates found?**
- Check TOC format matches supported patterns
- Ensure candidate IDs follow C123456 format

**Missing specific resumes?**
- Names might differ between TOC and resume (Nick vs Nicolas)
- Check if names are in contact info sections

**Custom output folder:**
```python
splitter.split_resumes(output_dir="my_folder")
```

## Customization

Easily modify detection patterns in the code:
- `patterns` - for different TOC formats
- `cover_letter_patterns` - for specific cover letter styles
- `resume_indicators` - for different resume keywords

## Limitations

- **Text-based PDFs only** (no scanned/image PDFs)
- **Requires clear TOC** with candidate IDs
- **Manual review** may be needed for 5-15% of edge cases

---

*The tool handles most resume bundles automatically. For complex cases or custom formats, review the code for easy customization options.*
