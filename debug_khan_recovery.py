# Save as: debug_khan_recovery.py
# Debug Khan Academy article recovery to see exactly what's failing

import pandas as pd
import requests
import time
from bs4 import BeautifulSoup
import re

def debug_khan_article_recovery(csv_file, article_limit=5):
    """Debug Khan Academy article recovery with detailed logging"""
    
    print("🔍 Debug Khan Academy Article Recovery")
    print("=" * 50)
    
    # Load CSV
    df = pd.read_csv(csv_file)
    
    # Find Khan Academy articles with missing source material
    missing_mask = (
        (df['source_material'].isna()) | 
        (df['source_material'] == 'null') | 
        (df['source_material'].str.strip() == '')
    )
    
    khan_articles = df[
        missing_mask & 
        (df['source_type'] == 'Khan Academy Article') & 
        df['article_id'].notna()
    ].head(article_limit)
    
    print(f"Found {len(khan_articles)} Khan Academy articles to debug")
    print()
    
    for idx, row in khan_articles.iterrows():
        debug_single_article(row)
        print("-" * 50)
        time.sleep(1)  # Be polite to Khan Academy

def debug_single_article(row):
    """Debug a single Khan Academy article recovery"""
    
    article_id = row['article_id']
    question_id = row['question_id']
    
    print(f"🔍 Debugging Article: {question_id}")
    print(f"   Article ID: {article_id}")
    print(f"   Question: {row['question_text'][:100]}...")
    print()
    
    # Try multiple URL construction strategies
    url_strategies = [
        # Strategy 1: Standard patterns
        f"https://www.khanacademy.org/science/article/{article_id}",
        f"https://www.khanacademy.org/math/article/{article_id}",
        f"https://www.khanacademy.org/humanities/article/{article_id}",
        f"https://www.khanacademy.org/computing/article/{article_id}",
        f"https://www.khanacademy.org/economics-finance-domain/article/{article_id}",
        f"https://www.khanacademy.org/test-prep/article/{article_id}",
        f"https://www.khanacademy.org/article/{article_id}",
        
        # Strategy 2: Without 'article' prefix
        f"https://www.khanacademy.org/science/{article_id}",
        f"https://www.khanacademy.org/math/{article_id}",
        f"https://www.khanacademy.org/humanities/{article_id}",
        
        # Strategy 3: Different URL patterns (if article_id contains path info)
        f"https://www.khanacademy.org/{article_id}",
        
        # Strategy 4: Try to parse if article_id is actually a partial URL
        article_id if article_id.startswith('http') else None,
    ]
    
    # Remove None values
    url_strategies = [url for url in url_strategies if url]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    success = False
    
    for i, url in enumerate(url_strategies, 1):
        print(f"   🌐 Strategy {i}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            print(f"      Status: {response.status_code}")
            print(f"      URL after redirects: {response.url}")
            print(f"      Content length: {len(response.content)} bytes")
            
            if response.status_code == 200:
                # Try to extract content
                content = extract_khan_content_debug(response.text, article_id)
                if content:
                    print(f"      ✅ SUCCESS! Extracted {len(content)} characters")
                    print(f"      Preview: {content[:200]}...")
                    success = True
                    break
                else:
                    print(f"      ⚠️  Page loaded but no content extracted")
                    
                # Show what we got instead
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                print(f"      Page title: {title.get_text() if title else 'No title'}")
                
                # Look for error indicators
                if "404" in response.text or "not found" in response.text.lower():
                    print(f"      ❌ Page indicates 404/not found")
                elif "access denied" in response.text.lower():
                    print(f"      ❌ Access denied")
                else:
                    print(f"      ❓ Unknown content structure")
                    
            elif response.status_code == 404:
                print(f"      ❌ Page not found")
            elif response.status_code == 403:
                print(f"      ❌ Access forbidden")
            elif response.status_code == 429:
                print(f"      🚦 Rate limited")
                break  # Stop trying if rate limited
            else:
                print(f"      ❌ HTTP error")
                
        except requests.exceptions.Timeout:
            print(f"      ⏰ Timeout")
        except requests.exceptions.RequestException as e:
            print(f"      💥 Request error: {str(e)}")
        except Exception as e:
            print(f"      💥 Unexpected error: {str(e)}")
        
        print()
    
    if not success:
        print(f"   ❌ All strategies failed for {article_id}")
        
        # Try to analyze the article_id format
        print(f"   🔍 Article ID Analysis:")
        print(f"      Format: {article_id}")
        print(f"      Length: {len(article_id)}")
        print(f"      Contains 'x': {'x' in article_id}")
        print(f"      Starts with 'x': {article_id.startswith('x')}")
        print(f"      Contains underscore: {'_' in article_id}")
        
        # Check if it might be a different type of identifier
        if article_id.startswith('x') and '_' in article_id:
            print(f"      💡 Looks like internal Khan Academy ID format")
        
        # Suggest alternative approaches
        print(f"   💡 Suggested alternatives:")
        print(f"      1. Search Khan Academy for question text")
        print(f"      2. Check if article_id needs different URL construction")
        print(f"      3. Look for Khan Academy API documentation")
    
    print()

def extract_khan_content_debug(html_content, article_id):
    """Debug version of content extraction"""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        print(f"      🔍 Content extraction debug:")
        
        # Try multiple content selectors and show what we find
        content_selectors = [
            ('[data-test-id="article-content"]', 'Modern test-id selector'),
            ('.article-content-container', 'Article container'),
            ('.perseus-renderer', 'Perseus renderer'),
            ('.framework-perseus', 'Framework perseus'),
            ('.article-content', 'Legacy article content'),
            ('.main-content', 'Main content'),
            ('.markdown-rendered-content', 'Markdown content'),
            ('.article-body', 'Article body'),
            ('main', 'Main element'),
            ('.content', 'Content class'),
            ('#content', 'Content ID'),
        ]
        
        best_content = ""
        best_selector = ""
        
        for selector, description in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text(separator=' ', strip=True) for elem in elements])
                content_length = len(content.strip())
                
                print(f"         {selector}: {content_length} chars")
                
                if content_length > len(best_content):
                    best_content = content
                    best_selector = description
        
        # If no good content from selectors, try paragraphs
        if len(best_content.strip()) < 200:
            paragraphs = soup.find_all(['p', 'div'], string=True)
            paragraph_content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            print(f"         Paragraph fallback: {len(paragraph_content)} chars")
            
            if len(paragraph_content) > len(best_content):
                best_content = paragraph_content
                best_selector = "Paragraph fallback"
        
        if best_content and len(best_content.strip()) > 200:
            print(f"         ✅ Best: {best_selector} ({len(best_content)} chars)")
            
            # Clean the content
            cleaned_content = clean_article_text_debug(best_content)
            if len(cleaned_content) > 8000:
                cleaned_content = cleaned_content[:8000] + "..."
            
            return cleaned_content
        else:
            print(f"         ❌ No substantial content found")
            
            # Debug: Show what's actually on the page
            page_text = soup.get_text()
            print(f"         Total page text: {len(page_text)} chars")
            if len(page_text) > 0:
                print(f"         Sample: {page_text[:300]}...")
            
            return None
        
    except Exception as e:
        print(f"         💥 Extraction error: {str(e)}")
        return None

def clean_article_text_debug(text):
    """Debug version of article text cleaning"""
    
    original_length = len(text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common HTML artifacts
    text = re.sub(r'\xa0', ' ', text)  # Non-breaking spaces
    text = re.sub(r'\u200b', '', text)  # Zero-width spaces
    text = re.sub(r'\u2019', "'", text)  # Smart quotes
    text = re.sub(r'\u201c|\u201d', '"', text)  # Smart quotes
    
    # Remove navigation and UI text
    ui_patterns = [
        r'Sign up|Log in|Sign in',
        r'Khan Academy|khanacademy\.org',
        r'Next lesson|Previous lesson',
        r'Share|Tweet|Facebook',
        r'Menu|Navigation|Search',
        r'Loading\.\.\.',
        r'Click here|Learn more',
    ]
    
    for pattern in ui_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    cleaned_length = len(text.strip())
    
    print(f"         Text cleaning: {original_length} → {cleaned_length} chars")
    
    return text.strip()

def search_khan_academy_alternative(question_text, max_results=3):
    """Alternative: Try to search Khan Academy for the question content"""
    
    print(f"🔍 Alternative: Searching Khan Academy for question content")
    
    # This would require implementing a search strategy
    # For now, just show what we would search for
    search_terms = question_text[:100].replace('?', '').strip()
    
    print(f"   Search terms: {search_terms}")
    print(f"   💡 Manual approach:")
    print(f"      1. Go to https://www.khanacademy.org/search")
    print(f"      2. Search for: {search_terms}")
    print(f"      3. Look for matching articles")
    print(f"      4. Extract content manually if found")

def main():
    """Main debug function"""
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_khan_recovery.py <csv_file> [limit]")
        print("Example: python debug_khan_recovery.py learningq_research_sample.csv 3")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    debug_khan_article_recovery(csv_file, limit)
    
    print("🎯 DEBUG SUMMARY:")
    print("=" * 50)
    print("If articles are not found with standard URL patterns:")
    print("1. The article IDs might be internal Khan Academy identifiers")
    print("2. The URL structure might have changed")
    print("3. The articles might have been moved or deleted")
    print("4. We might need a different approach (API, search, etc.)")
    print()
    print("💡 Next steps:")
    print("1. Check if any URL patterns worked")
    print("2. Look for alternative Khan Academy access methods")
    print("3. Focus on video recovery instead")
    print("4. Consider the articles as unrecoverable for now")

if __name__ == "__main__":
    main()