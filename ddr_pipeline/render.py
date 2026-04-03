import json
from jinja2 import Template
from ddr_pipeline.models import DDRReport

def render_html(report: DDRReport, output_path: str) -> None:
    template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Detailed Diagnostic Report - {{ report.property_id }}</title>
    <style>
        body {
            font-family: Georgia, Times, serif;
            max-width: 900px;
            margin: auto;
            padding: 40px;
            color: #222;
            line-height: 1.6;
        }
        
        h1, h2, h3 {
            font-family: Arial, sans-serif;
        }
        
        .cover {
            background: #1a2744;
            color: white;
            padding: 40px;
            margin-bottom: 40px;
            border-radius: 4px;
            text-align: center;
        }
        
        .cover h1 {
            margin: 0 0 20px 0;
            font-size: 28px;
            font-weight: bold;
        }
        
        .cover p {
            margin: 8px 0;
            font-size: 16px;
        }
        
        h2 {
            border-bottom: 2px solid #1a2744;
            padding-bottom: 8px;
            margin-top: 40px;
            color: #1a2744;
        }
        
        .area-block {
            background: #f9f9f7;
            padding: 24px;
            margin: 24px 0;
            border-radius: 4px;
            border-left: 4px solid #1a2744;
        }
        
        .area-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .area-title {
            font-size: 20px;
            font-weight: bold;
            margin-right: 12px;
        }
        
        .severity-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            color: white;
            font-family: Arial;
            font-size: 13px;
            font-weight: bold;
        }
        
        .severity-critical { background: #c0392b; }
        .severity-high { background: #e67e22; }
        .severity-moderate { background: #f39c12; }
        .severity-low { background: #27ae60; }
        .severity-informational { background: #2980b9; }
        
        .callout {
            padding: 16px;
            border-radius: 4px;
            margin: 16px 0;
        }
        
        .callout-conflict {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
        }
        
        .callout-missing {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
        }
        
        .images-container {
            margin: 20px 0;
        }
        
        .image-item {
            margin: 16px 0;
        }
        
        .image-item img {
            max-width: 500px;
            width: 100%;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 12px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .image-caption {
            font-size: 12px;
            color: #666;
            font-style: italic;
            margin-bottom: 16px;
        }
        
        .no-images {
            font-style: italic;
            color: #999;
            margin: 20px 0;
        }
        
        .severity-reasoning {
            background: #f8f9fa;
            padding: 16px;
            border-radius: 4px;
            margin: 16px 0;
            border-left: 3px solid #6c757d;
        }
        
        .actions-list, .global-actions-list {
            margin: 16px 0;
            padding-left: 20px;
        }
        
        .actions-list li, .global-actions-list li {
            margin: 8px 0;
        }
        
        .footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            font-size: 12px;
            color: #888;
            font-family: Arial;
            text-align: center;
        }
        
        .section {
            margin: 40px 0;
        }
        
        .missing-list {
            margin: 16px 0;
            padding-left: 20px;
        }
        
        .missing-list li {
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="cover">
        <h1>DETAILED DIAGNOSTIC REPORT</h1>
        <p><strong>Property ID:</strong> {{ report.property_id }}</p>
        <p><strong>Generated:</strong> {{ report.generated_at[:10] }}</p>
    </div>

    <div class="section">
        <h2>Property Issue Summary</h2>
        <p>{{ report.property_issue_summary }}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <p>{{ report.executive_summary }}</p>
    </div>

    {% for area in report.area_reports %}
    <div class="area-block">
        <div class="area-header">
            <span class="area-title">{{ area.area }}</span>
            <span class="severity-badge severity-{{ area.severity.value.lower() }}">{{ area.severity.value }}</span>
        </div>

        <h3>Observations</h3>
        <p>{{ area.observations }}</p>

        <h3>Images</h3>
        <div class="images-container">
            {% if area.images %}
                {% for img in area.images[:5] %}
                <div class="image-item">
                    <img src="data:image/png;base64,{{ img.b64 }}" alt="Image from page {{ img.page }}">
                    <div class="image-caption">{{ img.caption or "Image from page " + img.page|string }}</div>
                </div>
                {% endfor %}
                {% if area.images|length > 5 %}
                <p><em>Showing first 5 of {{ area.images|length }} images</em></p>
                {% endif %}
            {% else %}
                <p class="no-images">Image Not Available</p>
            {% endif %}
        </div>

        <h3>Probable Root Cause</h3>
        <p>{{ area.probable_root_cause }}</p>

        <h3>Severity Assessment</h3>
        <div class="severity-reasoning">
            <strong>Reasoning:</strong> {{ area.severity_reasoning }}
        </div>

        <h3>Recommended Actions</h3>
        <ol class="actions-list">
            {% for action in area.recommended_actions %}
            <li>{{ action }}</li>
            {% endfor %}
        </ol>

        {% if area.conflicts_noted %}
        <h3>Conflicts Noted</h3>
        <div class="callout callout-conflict">
            {% for conflict in area.conflicts_noted %}
            <p>{{ conflict }}</p>
            {% endfor %}
        </div>
        {% endif %}

        {% if area.missing_info %}
        <h3>Missing Information</h3>
        <div class="callout callout-missing">
            {% for missing in area.missing_info %}
            <p>{{ missing }}</p>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% endfor %}

    <div class="section">
        <h2>Global Recommended Actions</h2>
        <ol class="global-actions-list">
            {% for action in report.global_recommended_actions %}
            <li>{{ action }}</li>
            {% endfor %}
        </ol>
    </div>

    <div class="section">
        <h2>Additional Notes</h2>
        <p>{{ report.additional_notes }}</p>
    </div>

    <div class="section">
        <h2>Missing or Unclear Information</h2>
        {% if report.missing_or_unclear %}
            <ul class="missing-list">
                {% for item in report.missing_or_unclear %}
                <li>{{ item }}</li>
                {% endfor %}
            </ul>
        {% else %}
            <p>None identified</p>
        {% endif %}
    </div>

    <div class="footer">
        <p>This report was generated by an automated diagnostic system. All findings should be verified by a qualified professional before remediation.</p>
    </div>
</body>
</html>
    """
    
    template = Template(template_str)
    html_content = template.render(report=report)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Save JSON
    json_path = output_path.replace('.html', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report.model_dump(), f, indent=2)

if __name__ == "__main__":
    import sys
    import os
    from ddr_pipeline.extract import extract_pdf
    from ddr_pipeline.fuse import fuse
    from ddr_pipeline.generate import generate_ddr

    inspection = extract_pdf(sys.argv[1], "inspection")
    thermal = extract_pdf(sys.argv[2], "thermal")
    fusion = fuse(inspection, thermal)
    report = generate_ddr(fusion, os.environ["GROQ_API_KEY"])

    output = sys.argv[3] if len(sys.argv) > 3 else "ddr_report.html"
    render_html(report, output)
    print(f"Report saved to: {output}")
    print(f"JSON saved to: {output.replace('.html', '.json')}")
