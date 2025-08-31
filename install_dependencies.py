#!/usr/bin/env python3
"""
Dependency installation helper script for Smart Research Insights project.
This script helps resolve the bertopic/hdbscan installation issues on Windows.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False
    
    return True

def main():
    print("🚀 Smart Research Insights - Dependency Installation Helper")
    print("=" * 60)
    
    # Check if we're on Windows
    if os.name != 'nt':
        print("⚠️  This script is designed for Windows. On other platforms, try:")
        print("   pip install -r requirements.txt")
        return
    
    print("\n📋 Current Status:")
    
    # Test basic imports
    basic_imports = [
        "streamlit", "pandas", "plotly", "yaml", "sqlalchemy", 
        "psycopg2", "pydantic", "python-dotenv", "loguru"
    ]
    
    failed_imports = []
    for module in basic_imports:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_imports.append(module)
    
    # Test bertopic specifically
    try:
        import bertopic
        print("✅ bertopic")
        bertopic_available = True
    except ImportError:
        print("❌ bertopic")
        bertopic_available = False
    
    print(f"\n📊 Summary:")
    print(f"   Basic dependencies: {'✅ All available' if not failed_imports else f'❌ Missing: {failed_imports}'}")
    print(f"   BERTopic: {'✅ Available' if bertopic_available else '❌ Missing'}")
    
    # Install basic dependencies if needed
    if failed_imports:
        print(f"\n🔧 Installing missing basic dependencies...")
        success = run_command(
            "pip install -r requirements_basic.txt",
            "Installing basic dependencies"
        )
        if not success:
            print("❌ Failed to install basic dependencies. Please check your Python environment.")
            return
    
    # Handle bertopic installation
    if not bertopic_available:
        print(f"\n🔧 BERTopic Installation Options:")
        print("=" * 40)
        
        print("\nOption 1: Install Microsoft Visual C++ Build Tools (Recommended)")
        print("   1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("   2. Install with 'C++ build tools' workload")
        print("   3. Restart your terminal")
        print("   4. Run: pip install bertopic")
        
        print("\nOption 2: Use pre-compiled wheels (Alternative)")
        print("   Try installing from a wheel repository:")
        
        # Try to install from alternative source
        print("\n🔄 Attempting to install bertopic from alternative source...")
        success = run_command(
            "pip install bertopic --find-links https://download.pytorch.org/whl/torch_stable.html",
            "Installing bertopic from alternative source"
        )
        
        if not success:
            print("\n🔄 Trying conda installation...")
            success = run_command(
                "conda install -c conda-forge bertopic -y",
                "Installing bertopic via conda"
            )
        
        if not success:
            print("\n❌ Could not install bertopic automatically.")
            print("   Please follow Option 1 above to install Microsoft Visual C++ Build Tools.")
            print("   Then run: pip install bertopic")
    
    print(f"\n🎉 Installation Summary:")
    print("=" * 30)
    
    # Final test
    try:
        import streamlit
        print("✅ Streamlit is ready to use!")
        print("   Run: streamlit run app/streamlit_app_basic.py")
    except ImportError:
        print("❌ Streamlit not available")
    
    try:
        import bertopic
        print("✅ BERTopic is ready to use!")
        print("   Run: streamlit run app/streamlit_app.py")
    except ImportError:
        print("❌ BERTopic not available - use basic version")
        print("   Run: streamlit run app/streamlit_app_basic.py")
    
    print(f"\n📝 Next Steps:")
    print("   1. Set up your database and DATABASE_URL environment variable")
    print("   2. Run the pipeline to populate data")
    print("   3. Start the dashboard with one of the commands above")

if __name__ == "__main__":
    main()
