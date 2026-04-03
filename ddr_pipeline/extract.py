import base64
import hashlib
import re
from typing import Literal
import pdfplumber
import fitz
from .models import ExtractionResult, ImageRef, RawObservation

def extract_pdf(pdf_path: str, doc_type: Literal["inspection", "thermal"]) -> ExtractionResult:
    # Step 1: Extract text using pdfplumber
    raw_text_by_page = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            
            # Fix 2: Handle pages with no extracted text
            if len(page_text.strip()) < 30:
                # Fallback to pymupdf text extraction
                doc = fitz.open(pdf_path)
                fitz_page = doc[page_num - 1]
                page_text = fitz_page.get_text("text")
                doc.close()
            
            raw_text_by_page[page_num] = page_text
    
    # Step 2: Extract images using pymupdf
    all_images = []
    doc = fitz.open(pdf_path)
    seen_hashes = set()
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = raw_text_by_page[page_num + 1]
        image_list = page.get_images(full=True)
        
        for img in image_list:
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Content-based deduplication
                img_hash = hashlib.md5(image_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                seen_hashes.add(img_hash)
                
                # Fix 1: Filter out small/junk images
                if base_image.get("width", 0) < 200 or base_image.get("height", 0) < 200:
                    continue
                
                # Skip images from first 2 pages of inspection PDFs
                if doc_type == "inspection" and page_num <= 1:  # page_num is 0-indexed, so <=1 means pages 1-2
                    continue
                    
                b64 = base64.b64encode(image_bytes).decode("utf-8")
            except Exception:
                continue

            # Get caption from page text — just use the full page text truncated to 300 chars
            caption = page_text[:300].strip().replace("\n", " ")

            # Area tag: scan page_text for Area:/Location:/Room:/Zone: patterns
            area_tag = ""
            for pattern in [r"Area[:\s]+([^\n]+)", r"Location[:\s]+([^\n]+)", r"Room[:\s]+([^\n]+)", r"Zone[:\s]+([^\n]+)"]:
                m = re.search(pattern, page_text, re.IGNORECASE)
                if m:
                    area_tag = m.group(1).strip()[:60]
                    break

            image_ref = ImageRef(page=page_num + 1, index=img[0], caption=caption, area_tag=area_tag, b64=b64)
            all_images.append(image_ref)
    
    doc.close()
    
    # Step 3: Segment text into observations
    observations = []
    area_patterns = [r'(?:Area|Location|Room|Zone):\s*(.+?)(?:\n|$)', 
                    r'(?:AREA|LOCATION|ROOM|ZONE):\s*(.+?)(?:\n|$)']
    
    for page_num, page_text in raw_text_by_page.items():
        # Split on double newlines, numbered lists, or ALL CAPS lines
        segments = re.split(r'\n\s*\n|\n\d+\.|\n[A-Z][A-Z\s]+:', page_text)
        
        page_observations = []
        for segment in segments:
            segment = segment.strip()
            if not segment or len(segment) < 10:  # Skip empty or very short segments
                continue
            
            # Try to extract area name from segment
            area = "General"
            for pattern in area_patterns:
                matches = re.findall(pattern, segment, re.IGNORECASE)
                if matches:
                    area = matches[0].strip()
                    break
            
            obs = RawObservation(
                source=doc_type,
                area=area,
                text=segment,
                page=page_num,
                images=[]
            )
            observations.append(obs)
            page_observations.append(obs)
        
        # Fix 3: Always create at least one observation per page
        if not page_observations and page_text.strip():
            obs = RawObservation(
                source=doc_type,
                area="General",
                text=page_text,
                page=page_num,
                images=[]
            )
            observations.append(obs)
            page_observations.append(obs)
        
        # Fix 4: Handle pages with no text at all
        if not page_observations:
            obs = RawObservation(
                source=doc_type,
                area="General",
                text="[Image-only page - no extractable text]",
                page=page_num,
                images=[]
            )
            observations.append(obs)
    
    # Step 4: Associate images to observations
    for image in all_images:
        # Find observations on the same page
        page_observations = [obs for obs in observations if obs.page == image.page]
        
        if page_observations:
            # Find the observation with text closest to the image position
            # For simplicity, assign to the first observation on the page
            page_observations[0].images.append(image)
    
    return ExtractionResult(
        source_file=pdf_path,
        doc_type=doc_type,
        observations=observations,
        all_images=all_images,
        raw_text_by_page=raw_text_by_page
    )

if __name__ == "__main__":
    import sys
    result = extract_pdf(sys.argv[1], sys.argv[2])
    print(f"Pages: {len(result.raw_text_by_page)}")
    print(f"Observations: {len(result.observations)}")
    print(f"Images: {len(result.all_images)}")
    for obs in result.observations[:5]:
        print(f"  [{obs.area}] p{obs.page}: {obs.text[:80]!r}")
