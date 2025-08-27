# Save as: quick_recovery_fix.py
# Run this to diagnose and fix immediate recovery issues

import os
import sys
import requests
import time
import pandas as pd
from urllib.parse import urlparse

def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import youtube_transcript_api
        print("✅ youtube-transcript-api installed")
    except ImportError:
        print("❌ youtube-transcript-api missing")
        print("Run: pip install youtube-transcript-api")
        return False
    
    try:
        import requests
        print("✅ requests installed")
    except ImportError:
        print("❌ requests missing")
        print("Run: pip install requests")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✅ beautifulsoup4 installed")
    except ImportError:
        print("❌ beautifulsoup4 missing")
        print("Run: pip install beautifulsoup4")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas installed")
    except ImportError:
        print("❌ pandas missing")
        print("Run: pip install pandas")
        return False
    
    return True

def test_internet_connectivity():
    """Test basic internet connectivity"""
    print("\\n🌐 Testing internet connectivity...")
    
    test_urls = [
        "https://www.google.com",
        "https://www.youtube.com",
        "https://www.khanacademy.org"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {url} - OK")
            else:
                print(f"⚠️  {url} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - Error: {str(e)}")

def test_youtube_api_status():
    """Test if YouTube API is accessible"""
    print("\\n🎥 Testing YouTube API status...")
    
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Test with a well-known video ID
        test_video_id = "jNQXAC9IVRw"  # Popular educational video
        
        transcript = YouTubeTranscriptApi.get_transcript(test_video_id)
        if transcript:
            print("✅ YouTube Transcript API working")
            return True
        else:
            print("⚠️  YouTube Transcript API returned empty result")
            return False
            
    except Exception as e:
        if "Too Many Requests" in str(e) or "429" in str(e):
            print("🚦 YouTube API rate limited - wait 1 hour before trying videos")
            return False
        else:
            print(f"❌ YouTube API error: {str(e)}")
            return False

def test_khan_academy_access():
    """Test if Khan Academy is accessible"""
    print("\\n📚 Testing Khan Academy access...")
    
    test_urls = [
        "https://www.khanacademy.org",
        "https://www.khanacademy.org/science",
        "https://www.khanacademy.org/math"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for url in test_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                print(f"✅ {url} - OK")
            elif response.status_code == 429:
                print(f"🚦 {url} - Rate limited")
                return False
            else:
                print(f"⚠️  {url} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - Error: {str(e)}")
    
    return True

def analyze_csv_recovery_potential(csv_file):
    """Analyze which questions have the best recovery potential"""
    print(f"\\n📊 Analyzing recovery potential for {csv_file}...")
    
    try:
        df = pd.read_csv(csv_file)
        
        # Identify missing source material
        missing_mask = (
            df['source_material'].isna() | 
            (df['source_material'] == 'null') | 
            (df['source_material'].str.strip() == '')
        )
        missing_questions = df[missing_mask]
        
        print(f"Total questions: {len(df)}")
        print(f"Missing source material: {len(missing_questions)}")
        
        # Analyze by source type
        recovery_potential = {}
        
        for source_type in missing_questions['source_type'].unique():
            type_questions = missing_questions[missing_questions['source_type'] == source_type]
            
            if source_type == 'Khan Academy Video':
                recoverable = type_questions['video_id'].notna().sum()
            elif source_type == 'Khan Academy Article':
                recoverable = type_questions['article_id'].notna().sum()
            elif source_type == 'TED-Ed':
                recoverable = type_questions['video_youtube_link'].notna().sum()
            else:
                recoverable = 0
            
            recovery_potential[source_type] = {
                'total': len(type_questions),
                'recoverable': recoverable,
                'percentage': (recoverable / len(type_questions)) * 100 if len(type_questions) > 0 else 0
            }
        
        print("\\nRecovery potential by source type:")
        for source_type, stats in recovery_potential.items():
            print(f"  {source_type}: {stats['recoverable']}/{stats['total']} ({stats['percentage']:.1f}%)")
        
        return recovery_potential
        
    except Exception as e:
        print(f"❌ Error analyzing CSV: {str(e)}")
        return {}

def recommend_recovery_strategy(youtube_working, khan_working, recovery_potential):
    """Recommend the best recovery strategy based on current conditions"""
    print("\\n💡 RECOMMENDED RECOVERY STRATEGY:")
    print("=" * 50)
    
    if not youtube_working and not khan_working:
        print("🚨 CRITICAL: Both YouTube and Khan Academy are having issues")
        print("Recommendation: Wait 1-2 hours and try again")
        print("Check your internet connection and try from a different network")
        return
    
    if khan_working and not youtube_working:
        print("📚 Khan Academy is working, YouTube is rate limited")
        print("\\nStep 1: Recover articles first")
        print("python manage.py recover_source_material learningq_research_sample.csv --skip-youtube --slow-mode")
        print("\\nStep 2: Wait 1 hour, then try videos")
        print("python manage.py recover_source_material learningq_research_sample.csv --slow-mode --force-retry")
    
    elif youtube_working and not khan_working:
        print("🎥 YouTube is working, Khan Academy is having issues")
        print("\\nStep 1: Recover videos first")
        print("python manage.py recover_source_material learningq_research_sample.csv --slow-mode")
        print("\\nStep 2: Try articles later with slow mode")
        print("python manage.py recover_source_material learningq_research_sample.csv --slow-mode --force-retry")
    
    else:
        print("✅ Both services are working")
        print("\\nRecommended approach:")
        
        # Calculate total recoverable
        total_recoverable = sum(stats['recoverable'] for stats in recovery_potential.values())
        
        if total_recoverable <= 10:
            print("Small dataset - process all at once with slow mode")
            print("python manage.py recover_source_material learningq_research_sample.csv --slow-mode")
        else:
            print("Larger dataset - use phased approach")
            print("\\nPhase 1 (Articles): python manage.py recover_source_material learningq_research_sample.csv --skip-youtube --slow-mode")
            print("Phase 2 (Videos): python manage.py recover_source_material learningq_research_sample.csv --slow-mode --force-retry")
    
    print("\\n🔧 Additional options if problems persist:")
    print("• Use --limit 5 to process small batches")
    print("• Add delays between batches: sleep 1800 (30 minutes)")
    print("• Try during off-peak hours (late night/early morning)")
    print("• Use --dry-run to test without making changes")

def create_recovery_script(csv_file, youtube_working, khan_working):
    """Create a custom recovery script based on current conditions"""
    script_content = f"""#!/bin/bash
# Custom recovery script generated by diagnostics
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

echo "🚀 Starting Custom Source Material Recovery"
echo "CSV File: {csv_file}"
echo "YouTube Status: {'✅ Working' if youtube_working else '❌ Rate Limited'}"
echo "Khan Academy Status: {'✅ Working' if khan_working else '❌ Issues'}"
echo ""

"""

    if khan_working and not youtube_working:
        script_content += """# Phase 1: Articles only (YouTube rate limited)
echo "📚 Phase 1: Recovering Khan Academy Articles..."
python manage.py recover_source_material """ + csv_file + """ --skip-youtube --slow-mode

echo "⏳ Waiting 1 hour for YouTube rate limits to reset..."
sleep 3600

# Phase 2: Videos with slow mode
echo "🎥 Phase 2: Recovering YouTube Videos..."
python manage.py recover_source_material """ + csv_file + """ --slow-mode --force-retry
"""
    
    elif youtube_working and not khan_working:
        script_content += """# Phase 1: Videos first (Khan Academy having issues)
echo "🎥 Phase 1: Recovering YouTube Videos..."
python manage.py recover_source_material """ + csv_file + """ --slow-mode

echo "⏳ Waiting 30 minutes before trying articles..."
sleep 1800

# Phase 2: Articles with slow mode
echo "📚 Phase 2: Recovering Khan Academy Articles..."
python manage.py recover_source_material """ + csv_file + """ --slow-mode --force-retry
"""
    
    elif youtube_working and khan_working:
        script_content += """# Both services working - conservative approach
echo "📚 Phase 1: Recovering Khan Academy Articles..."
python manage.py recover_source_material """ + csv_file + """ --skip-youtube --slow-mode

echo "⏳ Brief pause between phases..."
sleep 300

echo "🎥 Phase 2: Recovering YouTube Videos..."
python manage.py recover_source_material """ + csv_file + """ --slow-mode --force-retry
"""
    
    else:
        script_content += """# Both services having issues - wait and retry
echo "🚨 Both services having issues - waiting 2 hours..."
sleep 7200

echo "🔄 Attempting recovery with maximum delays..."
python manage.py recover_source_material """ + csv_file + """ --slow-mode --limit 5
"""

    script_content += """
# Verification
echo "🔍 Verifying results..."
python manage.py verify_source_material """ + csv_file.replace('.csv', '_recovered.csv') + """ --show-details

echo "✅ Recovery script completed!"
"""

    with open('custom_recovery_script.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('custom_recovery_script.sh', 0o755)
    print(f"\\n📝 Created custom recovery script: custom_recovery_script.sh")
    print("Run with: ./custom_recovery_script.sh")

def main():
    print("🚀 Source Material Recovery Diagnostics & Quick Fix")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python quick_recovery_fix.py <csv_file>")
        print("Example: python quick_recovery_fix.py learningq_research_sample.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Run diagnostics
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\\n❌ Please install missing dependencies before proceeding")
        return
    
    test_internet_connectivity()
    youtube_working = test_youtube_api_status()
    khan_working = test_khan_academy_access()
    
    recovery_potential = analyze_csv_recovery_potential(csv_file)
    
    # Provide recommendations
    recommend_recovery_strategy(youtube_working, khan_working, recovery_potential)
    
    # Create custom script
    create_recovery_script(csv_file, youtube_working, khan_working)
    
    print("\\n🎯 SUMMARY:")
    print(f"Dependencies: {'✅ OK' if deps_ok else '❌ Issues'}")
    print(f"YouTube API: {'✅ Working' if youtube_working else '🚦 Rate Limited'}")
    print(f"Khan Academy: {'✅ Working' if khan_working else '⚠️  Issues'}")
    
    total_recoverable = sum(stats['recoverable'] for stats in recovery_potential.values())
    print(f"Recoverable questions: {total_recoverable}")
    
    print("\\n🚀 Next steps:")
    print("1. Follow the recommended strategy above")
    print("2. Run the generated custom_recovery_script.sh")
    print("3. Monitor progress and adjust as needed")

if __name__ == "__main__":
    main()