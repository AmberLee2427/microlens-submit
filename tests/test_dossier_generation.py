#!/usr/bin/env python3
"""
Test script for microlens-submit dossier generation.

This script demonstrates the complete workflow:
1. Initialize a submission project
2. Add sample solutions with various model types
3. Generate a dossier
4. Open the generated HTML file in a browser

Usage:
    python tests/test_dossier_generation.py
    # or from the project root:
    python -m tests.test_dossier_generation
"""

import subprocess
import sys
import webbrowser
from pathlib import Path
import time
import json
import os
import shlex


def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
    if check and result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def main():
    print("🚀 Testing microlens-submit dossier generation...")
    
    # Get the project root directory (parent of tests/)
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)  # Change to project root for consistent paths
    
    # Create test directories in project root
    project_dir = project_root / "test_submission_project"
    dossier_dir = project_root / "test_dossier_output"
    
    # Clean up any existing test directories
    if project_dir.exists():
        print(f"Removing existing project directory: {project_dir}")
        subprocess.run(f"rm -rf {project_dir}", shell=True)
    
    if dossier_dir.exists():
        print(f"Removing existing dossier directory: {dossier_dir}")
        subprocess.run(f"rm -rf {dossier_dir}", shell=True)
    
    print("\n📁 Creating test submission project...")
    
    # Initialize the project
    run_command(f"microlens-submit init --team-name 'Test Team Alpha' --tier 'advanced' {project_dir}")
    
    print("\n📊 Adding sample solutions...")
    
    # Add a simple 1S1L solution
    run_command(f"""microlens-submit add-solution EVENT001 1S1L {project_dir} \
        --param t0=2459123.5 \
        --param u0=0.15 \
        --param tE=20.5 \
        --log-likelihood -1234.56 \
        --n-data-points 1250 \
        --cpu-hours 2.5 \
        --wall-time-hours 0.5 \
        --relative-probability 0.6 \
        --notes "# Single Lens Solution\n\nThis is a simple point source, point lens fit for EVENT001." """)
    
    # Add a solution with elaborate markdown notes for testing
    elaborate_md = "example_note.md"
    escaped_md = elaborate_md.replace('"', '\\"').replace('\n', '\\n')
    run_command(f'microlens-submit add-solution EVENT001 1S1L {project_dir} '
                f'--param t0=2459123.6 '
                f'--param u0=0.16 '
                f'--param tE=21.0 '
                f'--log-likelihood -1200.00 '
                f'--n-data-points 1300 '
                f'--cpu-hours 3.0 '
                f'--wall-time-hours 0.7 '
                f'--relative-probability 0.5 '
                f'--notes-file "{escaped_md}"')
    
    # Add a binary lens solution with higher-order effects
    run_command(f"""microlens-submit add-solution EVENT001 1S2L {project_dir} \
        --param t0=2459123.5 \
        --param u0=0.12 \
        --param tE=22.1 \
        --param q=0.001 \
        --param s=1.15 \
        --param alpha=45.2 \
        --log-likelihood -1189.34 \
        --n-data-points 1250 \
        --cpu-hours 15.2 \
        --wall-time-hours 3.8 \
        --relative-probability 0.4 \
        --higher-order-effect parallax \
        --higher-order-effect finite-source \
        --t-ref 2459123.0 \
        --notes "# Binary Lens Solution\n\nThis solution includes parallax and finite source effects." """)
    
    # Add a second event with different characteristics
    run_command(f"""microlens-submit add-solution EVENT002 1S2L {project_dir} \
        --param t0=2459156.2 \
        --param u0=0.08 \
        --param tE=35.7 \
        --param q=0.0005 \
        --param s=0.95 \
        --param alpha=78.3 \
        --log-likelihood -2156.78 \
        --n-data-points 2100 \
        --cpu-hours 28.5 \
        --wall-time-hours 7.2 \
        --relative-probability 1.0 \
        --higher-order-effect parallax \
        --t-ref 2459156.0 \
        --notes "# Complex Binary Event\n\nThis event shows clear caustic crossing features." """)
    
    # Add a third event with different model type
    run_command(f"""microlens-submit add-solution EVENT003 2S1L {project_dir} \
        --param t0=2459180.0 \
        --param u0=0.25 \
        --param tE=18.3 \
        --log-likelihood -987.65 \
        --n-data-points 800 \
        --cpu-hours 8.1 \
        --wall-time-hours 1.5 \
        --relative-probability 1.0 \
        --notes "# Binary Source Event\n\nThis event shows evidence of a binary source." """)
    
    print("\n🔍 Validating submission...")
    
    # Validate the submission
    result = run_command(f"microlens-submit validate-submission {project_dir}", check=False)
    if result.returncode == 0:
        print("✅ Submission validation passed!")
    else:
        print("⚠️  Submission validation warnings (this is normal for test data):")
        print(result.stdout)
    
    print("\n📋 Listing solutions...")
    
    # List solutions for each event
    for event_id in ["EVENT001", "EVENT002", "EVENT003"]:
        print(f"\n--- Solutions for {event_id} ---")
        result = run_command(f"microlens-submit list-solutions {event_id} {project_dir}")
        print(result.stdout)
    
    print("\n🎨 Generating dossier...")
    
    # Generate the dossier
    try:
        run_command(f"microlens-submit generate-dossier {project_dir}")
    except:
        print("Dossier generation failed")
        pass
    else: 
        print(f"\n✅ Dossier generated successfully!")
        
    
    # Check what was created
    print(f"\n📁 Dossier files created:")
    dossier_path = project_dir / "dossier"
    for file_path in dossier_path.rglob("*"):
        if file_path.is_file():
            print(f"  {file_path.relative_to(dossier_path)}")
    
    # Verify the main HTML file exists
    index_html = dossier_path / "index.html"
    if not index_html.exists():
        print("❌ Error: index.html was not created!")
        sys.exit(1)
    
    
    print(f"📄 Main dashboard: {index_html.absolute()}")
    print(f"📁 Assets directory: {(dossier_path / 'assets').absolute()}")
    print(f"📁 Events directory: {(dossier_path / 'events').absolute()}")
    
    # Try to open the HTML file in the default browser
    print(f"\n🌐 Opening dashboard in browser...")
    try:
        webbrowser.open(f"file://{index_html.absolute()}")
        print("✅ Browser should have opened with the dashboard!")
    except Exception as e:
        print(f"⚠️  Could not automatically open browser: {e}")
        print(f"   Please manually open: {index_html.absolute()}")
    
    print(f"\n🎉 Test completed successfully!")
    print(f"\n📝 Next steps:")
    print(f"   1. View the dashboard in your browser")
    print(f"   2. Check the responsive design on different screen sizes")
    print(f"   3. Verify all the statistics and information are correct")
    print(f"   4. Test the event links (they'll be placeholders for now)")
    print(f"\n🧹 To clean up test files:")
    print(f"   rm -rf {project_dir} {dossier_dir}")


if __name__ == "__main__":
    main() 