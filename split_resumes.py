import PyPDF2
import pdfplumber
import re
from pathlib import Path

class ResumeSplitter:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
    
    def find_resume_pages_flexible(self):
        """More flexible approach to find resume start pages"""
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Get candidates from ALL TOC pages (first few pages might be TOC)
            candidates = []
            resume_pages = []
            
            # Flexible TOC search - check more pages and different patterns
            max_toc_pages = min(15, len(pdf.pages))  # Check up to 15 pages
            
            for page_num in range(max_toc_pages):
                toc_text = pdf.pages[page_num].extract_text()
                if not toc_text:
                    continue
                    
                page_candidates = []
                for line in toc_text.split('\n'):
                    # Try multiple TOC patterns
                    patterns = [
                        r'(\d+)\.\s*(.+?)\s+(C\d+)',  # Original pattern
                        r'(.+?)\s+(C\d+)\s*$',         # Name then ID at end
                        r'(C\d+)\s+(.+?)\s*$',         # ID then name
                        r'(\d+)\s+(.+?)\s+(C\d+)',    # Number space name space ID
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line.strip())
                        if match:
                            if len(match.groups()) == 3:  # Pattern with number
                                name = match.group(2).strip()
                                candidate_id = match.group(3)
                            else:  # Pattern without number
                                if pattern.startswith('(C'):
                                    candidate_id = match.group(1)
                                    name = match.group(2).strip()
                                else:
                                    name = match.group(1).strip()
                                    candidate_id = match.group(2)
                            
                            # Skip if already found (avoid duplicates)
                            if not any(c['id'] == candidate_id for c in candidates):
                                page_candidates.append({'name': name, 'id': candidate_id})
                            break  # Found match, no need to try other patterns
                
                # Add candidates from this page
                candidates.extend(page_candidates)
                
                # Stop if we haven't found candidates in last few pages
                if not page_candidates and page_num > 5:
                    recent_pages_empty = True
                    for check_page in range(max(0, page_num-2), page_num):
                        check_text = pdf.pages[check_page].extract_text() or ""
                        if re.search(r'C\d+', check_text):
                            recent_pages_empty = False
                            break
                    if recent_pages_empty:
                        break
            
            print(f"Found {len(candidates)} candidates from TOC pages")
            
            # Dynamically find where TOC ends
            last_toc_page = 0
            for page_num in range(min(15, len(pdf.pages))):
                page_text = pdf.pages[page_num].extract_text() or ""
                if re.search(r'C\d+', page_text):
                    last_toc_page = page_num
            
            start_page = max(1, last_toc_page + 1)
            print(f"Starting resume search from page {start_page + 1} (after TOC)")
            for page_num in range(start_page, len(pdf.pages)):
                page_text = pdf.pages[page_num].extract_text() or ""
                
                # Skip cover letter pages during initial detection
                if self.is_cover_letter_page(page_text):
                    print(f"Skipping cover letter on page {page_num + 1}")
                    continue
                
                for candidate in candidates:
                    # Skip if already found
                    if any(rp['id'] == candidate['id'] for rp in resume_pages):
                        continue
                    
                    # Clean up name for better matching (remove apostrophes, extra spaces)
                    clean_name = re.sub(r"['\-\.]", " ", candidate['name']).strip()
                    name_parts = clean_name.split()
                    
                    # Prepare text for searching - remove newlines for multi-line names
                    page_text_no_newlines = page_text.replace('\n', ' ')
                    page_upper = page_text.upper()
                    page_upper_no_newlines = page_text_no_newlines.upper()
                    
                    # Method 1: Check if full name appears (handle line breaks like "Ezra\nBUNNELL")
                    if clean_name.upper() in page_upper_no_newlines[:600]:
                        resume_pages.append({
                            'name': candidate['name'],
                            'id': candidate['id'],
                            'page': page_num
                        })
                        print(f"Method 1 (no newlines) - Found: {candidate['name']} on page {page_num + 1}")
                        continue
                    
                    # Method 2: Check original name too (case-insensitive)
                    if candidate['name'].upper() in page_upper[:600]:
                        resume_pages.append({
                            'name': candidate['name'],
                            'id': candidate['id'],
                            'page': page_num
                        })
                        print(f"Method 2 - Found: {candidate['name']} on page {page_num + 1}")
                        continue
                    
                    # Method 3: Deep search for names buried in cover letters/contact info (search more text)
                    if candidate['name'].upper() in page_upper[:2000]:
                        resume_pages.append({
                            'name': candidate['name'],
                            'id': candidate['id'],
                            'page': page_num
                        })
                        print(f"Method 3 (deep search) - Found: {candidate['name']} on page {page_num + 1}")
                        continue
                    
                    # Method 4: Check name parts separately (good for names split across lines)
                    if len(name_parts) >= 2:
                        found_parts = 0
                        for part in name_parts:
                            if len(part) > 2 and part.upper() in page_upper_no_newlines[:800]:
                                found_parts += 1
                        
                        if found_parts >= 2:  # At least 2 name parts found
                            resume_pages.append({
                                'name': candidate['name'],
                                'id': candidate['id'],
                                'page': page_num
                            })
                            print(f"Method 4 (name parts) - Found: {candidate['name']} on page {page_num + 1}")
                            continue
                    
                    # Method 5: Last name + first name pattern (case-insensitive, more text)
                    if len(name_parts) >= 2:
                        first_name = name_parts[0].upper()
                        last_name = name_parts[-1].upper()
                        
                        if first_name in page_upper_no_newlines[:1000] and last_name in page_upper_no_newlines[:1000]:
                            resume_pages.append({
                                'name': candidate['name'],
                                'id': candidate['id'],
                                'page': page_num
                            })
                            print(f"Method 5 (first+last) - Found: {candidate['name']} on page {page_num + 1}")
                            continue
            
            # Sort by page number
            resume_pages.sort(key=lambda x: x['page'])
            
            # ENHANCED: Find missing resumes with multiple fallback methods
            if len(resume_pages) < len(candidates):
                print(f"Found {len(resume_pages)} out of {len(candidates)} - using fallback detection...")
                
                found_candidates = [rp['id'] for rp in resume_pages]
                missing_candidates = [c for c in candidates if c['id'] not in found_candidates]
                
                print(f"Missing candidates: {[c['id'] for c in missing_candidates]}")
                
                # Method 1: Look for candidate IDs anywhere in the document
                for missing in missing_candidates:
                    for page_num in range(start_page, len(pdf.pages)):
                        page_text = pdf.pages[page_num].extract_text() or ""
                        
                        # Look for candidate ID (C001, C002, etc.)
                        if missing['id'] in page_text.upper():
                            # Make sure this page isn't already assigned
                            if not any(rp['page'] == page_num for rp in resume_pages):
                                resume_pages.append({
                                    'name': missing['name'],
                                    'id': missing['id'],
                                    'page': page_num
                                })
                                print(f"Fallback Method 1 - Found {missing['id']} on page {page_num + 1}")
                                break
                
                # Method 2: Pattern-based resume detection (common resume keywords)
                found_candidates = [rp['id'] for rp in resume_pages]
                still_missing = [c for c in candidates if c['id'] not in found_candidates]
                
                if still_missing:
                    resume_indicators = [
                        "EXPERIENCE", "EDUCATION", "SKILLS", "OBJECTIVE",
                        "SUMMARY", "EMPLOYMENT", "WORK HISTORY", "QUALIFICATIONS",
                        "CONTACT", "EMAIL", "PHONE", "ADDRESS"
                    ]
                    
                    for missing in still_missing:
                        best_page = None
                        max_indicators = 0
                        
                        for page_num in range(start_page, len(pdf.pages)):
                            # Skip if page already assigned
                            if any(rp['page'] == page_num for rp in resume_pages):
                                continue
                                
                            page_text = pdf.pages[page_num].extract_text() or ""
                            page_upper = page_text.upper()
                            
                            # Count resume indicators
                            indicator_count = sum(1 for indicator in resume_indicators if indicator in page_upper)
                            
                            # Also check for partial name matches
                            name_parts = missing['name'].upper().split()
                            name_matches = sum(1 for part in name_parts if len(part) > 2 and part in page_upper)
                            
                            total_score = indicator_count + (name_matches * 2)  # Weight name matches higher
                            
                            if total_score > max_indicators and total_score >= 3:  # Minimum threshold
                                max_indicators = total_score
                                best_page = page_num
                        
                        if best_page is not None:
                            resume_pages.append({
                                'name': missing['name'],
                                'id': missing['id'],
                                'page': best_page
                            })
                            print(f"Fallback Method 2 - Found {missing['id']} on page {best_page + 1} (score: {max_indicators})")
                
                # Method 3: Distribute remaining candidates evenly across unassigned pages
                found_candidates = [rp['id'] for rp in resume_pages]
                still_missing = [c for c in candidates if c['id'] not in found_candidates]
                
                if still_missing:
                    assigned_pages = sorted([rp['page'] for rp in resume_pages])
                    total_pages = len(pdf.pages)
                    
                    # Find gaps between assigned pages
                    unassigned_pages = []
                    for i in range(start_page, total_pages):
                        if i not in assigned_pages:
                            unassigned_pages.append(i)
                    
                    # Distribute missing candidates across unassigned pages
                    if unassigned_pages:
                        for i, missing in enumerate(still_missing):
                            if i < len(unassigned_pages):
                                page_to_assign = unassigned_pages[i]
                                resume_pages.append({
                                    'name': missing['name'],
                                    'id': missing['id'],
                                    'page': page_to_assign
                                })
                                print(f"Fallback Method 3 - Assigned {missing['id']} to page {page_to_assign + 1}")
            
            # Sort again after adding missing ones
            resume_pages.sort(key=lambda x: x['page'])
            return resume_pages
    
    def is_cover_letter_page(self, page_text):
        """Comprehensive cover letter detection with formatting handling"""
        # Clean text for better matching - handle various formatting issues
        clean_text = page_text.upper()
        clean_text = re.sub(r'\s+', ' ', clean_text)  # Normalize whitespace
        clean_text = re.sub(r'[^\w\s]', ' ', clean_text)  # Remove special chars
        
        # Comprehensive cover letter indicators
        cover_letter_patterns = [
            # Salutations
            r'DEAR\s+(HIRING|SIR|MADAM|MR|MS|MRS)',
            r'TO\s+WHOM\s+IT\s+MAY\s+CONCERN',
            r'DEAR\s+\w+\s+TEAM',
            r'DEAR\s+\w+\s+MANAGER',
            r'HELLO\s+HIRING',
            
            # Cover letter phrases
            r'I\s+AM\s+(WRITING|PLEASED|EXCITED|INTERESTED)',
            r'THANK\s+YOU\s+FOR\s+(CONSIDERING|YOUR\s+TIME)',
            r'I\s+WOULD\s+LIKE\s+TO\s+APPLY',
            r'I\s+AM\s+APPLYING\s+FOR',
            r'PLEASE\s+FIND\s+(MY|ATTACHED)',
            r'I\s+LOOK\s+FORWARD\s+TO',
            r'COVER\s+LETTER',
            
            # Closings
            r'SINCERELY\s+YOURS?',
            r'BEST\s+REGARDS',
            r'YOURS\s+(TRULY|FAITHFULLY)',
            r'KIND\s+REGARDS',
            r'RESPECTFULLY',
            
            # Letter-specific content
            r'RE\s*:\s*\w+',  # Subject line
            r'POSITION\s+(I\s+AM\s+)?APPLYING',
            r'MY\s+RESUME\s+(IS\s+)?ATTACHED',
            r'PLEASE\s+CONSIDER\s+MY',
            r'I\s+BELIEVE\s+(I\s+AM|MY)',
            r'MY\s+QUALIFICATIONS\s+INCLUDE',
            
            # Date patterns at start
            r'^\s*(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)',
            r'^\s*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}',
        ]
        
        # Check if text contains multiple cover letter indicators
        matches = 0
        for pattern in cover_letter_patterns:
            if re.search(pattern, clean_text):
                matches += 1
        
        # If 2+ patterns match, likely a cover letter
        if matches >= 2:
            return True
        
        # Single strong indicators
        strong_indicators = [
            'TO WHOM IT MAY CONCERN',
            'DEAR HIRING MANAGER',
            'DEAR HIRING TEAM',
            'COVER LETTER'
        ]
        
        return any(indicator in clean_text for indicator in strong_indicators)

    def split_resumes(self, output_dir="extracted_resumes"):
        """Split PDF with cover letter removal and enhanced detection"""
        
        resume_pages = self.find_resume_pages_flexible()
        
        if len(resume_pages) == 0:
            print("❌ No resumes found!")
            return
        
        print(f"\nSplitting {len(resume_pages)} resumes:")
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Split the PDF with cover letter removal
        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            for i, resume in enumerate(resume_pages):
                start_page = resume['page']
                
                # End page = start of next resume OR end of PDF
                if i + 1 < len(resume_pages):
                    end_page = resume_pages[i + 1]['page']
                else:
                    end_page = total_pages
                
                # Create new PDF for this resume, filtering out cover letters
                writer = PyPDF2.PdfWriter()
                pages_added = 0
                cover_letters_removed = 0
                
                for page_idx in range(start_page, end_page):
                    # Extract text to check for cover letter
                    with pdfplumber.open(self.pdf_path) as pdf:
                        page_text = pdf.pages[page_idx].extract_text() or ""
                    
                    # Skip cover letter pages
                    if self.is_cover_letter_page(page_text):
                        print(f"  📧 Removing cover letter from page {page_idx + 1}")
                        cover_letters_removed += 1
                        continue
                    
                    # Add non-cover-letter pages
                    writer.add_page(reader.pages[page_idx])
                    pages_added += 1
                
                # Only save if we have actual resume pages
                if pages_added > 0:
                    # Save with clean filename
                    safe_name = re.sub(r'[^\w\s]', '', resume['name']).replace(' ', '_')
                    filename = f"{i+1:02d}_{safe_name}_{resume['id']}.pdf"
                    output_path = Path(output_dir) / filename
                    
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    cover_info = f" (removed {cover_letters_removed} cover letters)" if cover_letters_removed > 0 else ""
                    print(f"✅ {filename} ({pages_added} pages){cover_info}")
                else:
                    print(f"⚠️  {resume['name']} - No resume pages found (all were cover letters)")
        
        print(f"\n🎉 Done! Split {len(resume_pages)} resumes with cover letter removal.")

# Usage
if __name__ == "__main__":
    pdf_file = "your_resume_bundle.pdf"  # CHANGE THIS
    
    splitter = ResumeSplitter(pdf_file)
    splitter.split_resumes()