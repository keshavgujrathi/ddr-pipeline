import sys
import os
from pathlib import Path
from .extract import extract_pdf
from .fuse import fuse
from .generate import generate_ddr
from .render import render_html

def main():
    try:
        # Validate arguments
        if len(sys.argv) < 3:
            print("[ERROR] Usage: python -m ddr_pipeline.main <inspection_pdf> <thermal_pdf> [output_path]", file=sys.stderr)
            sys.exit(1)
        
        inspection_path = sys.argv[1]
        thermal_path = sys.argv[2]
        output_path = sys.argv[3] if len(sys.argv) > 3 else "ddr_report.html"
        
        # Validate files exist and are PDFs
        if not Path(inspection_path).exists():
            print(f"[ERROR] Inspection file not found: {inspection_path}", file=sys.stderr)
            sys.exit(1)
        
        if not Path(thermal_path).exists():
            print(f"[ERROR] Thermal file not found: {thermal_path}", file=sys.stderr)
            sys.exit(1)
        
        if not inspection_path.lower().endswith('.pdf'):
            print(f"[ERROR] Inspection file must be a PDF: {inspection_path}", file=sys.stderr)
            sys.exit(1)
        
        if not thermal_path.lower().endswith('.pdf'):
            print(f"[ERROR] Thermal file must be a PDF: {thermal_path}", file=sys.stderr)
            sys.exit(1)
        
        # Step 1: Extract inspection data
        try:
            inspection_result = extract_pdf(inspection_path, "inspection")
            print(f"[INFO] Extracted {len(inspection_result.observations)} observations, {len(inspection_result.all_images)} images from inspection.", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Inspection extraction: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Step 2: Extract thermal data
        try:
            thermal_result = extract_pdf(thermal_path, "thermal")
            print(f"[INFO] Extracted {len(thermal_result.observations)} observations, {len(thermal_result.all_images)} images from thermal.", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Thermal extraction: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Step 3: Fuse data
        try:
            fusion_result = fuse(inspection_result, thermal_result)
            missing_flags = sum(len(area.missing) for area in fusion_result.areas)
            print(f"[INFO] Fusion complete. Areas: {len(fusion_result.areas)}, Images: {len(fusion_result.areas[0].images) if fusion_result.areas else 0}, Missing flags: {missing_flags}.", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Data fusion: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Step 4: Get API key
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            print("[ERROR] GROQ_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        # Step 5: Generate report
        try:
            report = generate_ddr(fusion_result, groq_api_key)
            severity = report.area_reports[0].severity.value if report.area_reports else "Unknown"
            print(f"[INFO] Report generated. Severity: {severity}.", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Report generation: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Step 6: Render HTML
        try:
            render_html(report, output_path)
            print(output_path)
        except Exception as e:
            print(f"[ERROR] HTML rendering: {e}", file=sys.stderr)
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("[ERROR] Interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
