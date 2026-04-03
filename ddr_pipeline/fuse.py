import re
from pathlib import Path
from .models import FusionResult, MergedObservation, ConflictNote, ImageRef

def fuse(inspection, thermal) -> FusionResult:
    # 1. Property ID from filename stem
    property_id = Path(inspection.source_file).stem
    
    # 2. Create single merged observation for entire property
    inspection_texts = [obs.text for obs in inspection.observations if obs.text.strip()]
    thermal_texts = [obs.text for obs in thermal.observations if obs.text.strip()]
    
    # 3. Image selection
    inspection_images = [img for img in inspection.all_images if img.b64.strip()][:30]
    
    # Filter thermal images for temperature readings and cap at 20
    thermal_images_with_temp = []
    for img in thermal.all_images:
        # Find the observation text for this image's page
        page_obs = [obs for obs in thermal.observations if obs.page == img.page]
        if page_obs:
            page_text = " ".join([obs.text for obs in page_obs])
            # Check for temperature pattern
            if re.search(r'\d+\s*°[CF]|\d+\s*deg', page_text, re.IGNORECASE):
                thermal_images_with_temp.append(img)
    
    # Sample thermal images to get spread across pages (max 20)
    thermal_images = thermal_images_with_temp[:20]
    if len(thermal_images_with_temp) > 20:
        step = len(thermal_images_with_temp) // 20
        thermal_images = [thermal_images_with_temp[i] for i in range(0, len(thermal_images_with_temp), step)][:20]
    
    all_images = inspection_images + thermal_images
    
    # 4. Missing detection
    all_texts = inspection_texts + thermal_texts
    missing_phrases = ["not available", "unclear", "n/a", "unknown", "could not", "not visible", "no evidence", "not observed"]
    missing = []
    
    for phrase in missing_phrases:
        for text in all_texts:
            if phrase.lower() in text.lower():
                missing.append(phrase)
                break
    
    missing = list(set(missing))  # Unique matches
    
    # 5. Conflict detection for temperatures
    conflicts = []
    
    # Extract temperatures from inspection
    inspection_temps = []
    for text in inspection_texts:
        matches = re.findall(r'\b(\d+\.?\d*)\s*°[CF]\b', text, re.IGNORECASE)
        inspection_temps.extend([float(m) for m in matches])
    
    # Extract temperatures from thermal
    thermal_temps = []
    for text in thermal_texts:
        matches = re.findall(r'\b(\d+\.?\d*)\s*°[CF]\b', text, re.IGNORECASE)
        thermal_temps.extend([float(m) for m in matches])
    
    # Check for temperature conflicts
    if inspection_temps and thermal_temps:
        insp_min, insp_max = min(inspection_temps), max(inspection_temps)
        therm_min, therm_max = min(thermal_temps), max(thermal_temps)
        
        # Check if ranges don't overlap
        if insp_max < therm_min or therm_max < insp_min:
            conflict = ConflictNote(
                field="Temperature",
                inspection_says=f"{insp_min:.1f}° to {insp_max:.1f}°",
                thermal_says=f"{therm_min:.1f}° to {therm_max:.1f}°"
            )
            conflicts.append(conflict)
    
    # Create merged observation
    merged_obs = MergedObservation(
        area="Property",
        inspection_texts=inspection_texts,
        thermal_texts=thermal_texts,
        images=all_images,
        conflicts=conflicts,
        missing=missing
    )
    
    return FusionResult(
        property_id=property_id,
        areas=[merged_obs],
        unmatched_inspection=[],
        unmatched_thermal=[],
        global_images=[]
    )

if __name__ == "__main__":
    import sys
    from ddr_pipeline.extract import extract_pdf
    inspection = extract_pdf(sys.argv[1], "inspection")
    thermal = extract_pdf(sys.argv[2], "thermal")
    result = fuse(inspection, thermal)
    print(f"Property: {result.property_id}")
    print(f"Areas: {len(result.areas)}")
    for area in result.areas:
        print(f"  [{area.area}] inspection_texts: {len(area.inspection_texts)}, thermal_texts: {len(area.thermal_texts)}, images: {len(area.images)}, missing: {len(area.missing)}, conflicts: {len(area.conflicts)}")
