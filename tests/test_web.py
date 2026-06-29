import json
import pytest
from pathlib import Path
from esp_lab.diagnostics.web import generate_diagnostics_webpage


def test_generate_webpage_success(tmp_path):
    # Create mock figures.json
    mock_data = {
        "updated": "2026-06-29T10:00:00Z",
        "figures": [
            {
                "file": "fig_nao_skill.png",
                "mode": "NAO",
                "metric": "skill",
                "title": "Seasonal NAO Skill",
                "caption": "Verification details here",
            }
        ],
    }
    
    manifest_file = tmp_path / "figures.json"
    with open(manifest_file, "w", encoding="utf-8") as fh:
        json.dump(mock_data, fh, indent=2)

    # Generate webpage
    output_html = generate_diagnostics_webpage(tmp_path)
    
    assert output_html.exists()
    assert output_html.name == "index.html"
    
    # Read generated HTML and verify content
    with open(output_html, "r", encoding="utf-8") as fh:
        html_content = fh.read()
        
    assert "ESP-Lab Diagnostic Viewer" in html_content
    # Check if mock figures.json was correctly embedded
    assert "fig_nao_skill.png" in html_content
    assert "Seasonal NAO Skill" in html_content


def test_generate_webpage_missing_directory():
    non_existent_dir = Path("/non/existent/path/for/diagnostics/webpage")
    with pytest.raises(FileNotFoundError):
        generate_diagnostics_webpage(non_existent_dir)


def test_generate_webpage_missing_manifest(tmp_path):
    # No figures.json created in tmp_path
    with pytest.raises(FileNotFoundError):
        generate_diagnostics_webpage(tmp_path)
