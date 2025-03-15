from flask import Flask, render_template, request, send_file, jsonify, session, after_this_request
import requests
from bs4 import BeautifulSoup
import os
import re
import json
from urllib.parse import urljoin, urlparse, urlunparse, unquote, quote, parse_qs
import zipfile
from io import BytesIO
import mimetypes
import base64
import cssutils
import logging
import uuid
import random
import time
import urllib3
import tempfile
from datetime import datetime
import traceback
import html
import shutil
import threading

# Try to import Selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    print("Selenium is available. Advanced rendering is enabled.")
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Advanced rendering will be disabled.")

# Suppress cssutils warnings
cssutils.log.setLevel(logging.CRITICAL)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_website_extractor')

def is_binary_content(content, asset_type):
    """Determine if content should be treated as binary or text based on asset type and content inspection"""
    # First check by asset type
    if asset_type in ['images', 'fonts', 'videos', 'audio']:
        return True
        
    # For potentially text-based assets, try to detect if it's binary
    if asset_type in ['css', 'js', 'html', 'svg', 'json', 'globals_css']:
        # Check if the content is bytes
        if not isinstance(content, bytes):
            return False
            
        # Try to detect if binary by checking for null bytes and high concentration of non-ASCII chars
        try:
            # Check for null bytes which indicate binary content
            if b'\x00' in content:
                return True
                
            # Sample the first 1024 bytes to determine if it's binary
            sample = content[:1024]
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
            return bool(sample.translate(None, text_chars))
        except:
            # If there's any error in detection, treat as binary to be safe
            return True
            
    # For anything else, just check if it's bytes
    return isinstance(content, bytes)

def download_asset(url, base_url, headers=None, session_obj=None):
    """
    Download an asset from a URL
    
    Args:
        url: URL to download from
        base_url: Base URL of the website (for referrer)
        headers: Optional custom headers
        session_obj: Optional requests.Session object for maintaining cookies
    
    Returns:
        Content of the asset or None if download failed
    """
    # List of user agents to rotate through to avoid detection
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ]
    
    # Use a random user agent
    random_user_agent = random.choice(user_agents)
    
    if not headers:
        headers = {
            'User-Agent': random_user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': base_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
    else:
        # Update the user agent in the provided headers
        headers['User-Agent'] = random_user_agent
    
    # Parse the URL to check if it's valid
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            print(f"Invalid URL: {url}")
            return None
    except Exception as e:
        print(f"Error parsing URL {url}: {str(e)}")
        return None
    
    # Add a delay to avoid rate limiting
    time.sleep(0.1)  # 100ms delay between requests
    
    # Maximum number of retries
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Use session if provided, otherwise make a direct request
            if session_obj:
                response = session_obj.get(
                    url, 
                    timeout=15, 
                    headers=headers, 
                    stream=True, 
                    allow_redirects=True,
                    verify=False  # Ignore SSL certificate errors
                )
            else:
                response = requests.get(
                    url, 
                    timeout=15, 
                    headers=headers, 
                    stream=True, 
                    allow_redirects=True,
                    verify=False  # Ignore SSL certificate errors
                )
            
            # Handle redirects
            if response.history:
                print(f"Request for {url} was redirected {len(response.history)} times to {response.url}")
                url = response.url  # Update URL to the final destination
            
            if response.status_code == 200:
                # Check the Content-Type header
                content_type = response.headers.get('Content-Type', '')
                print(f"Downloaded {url} ({len(response.content)} bytes, type: {content_type})")
                
                # Check for binary content types
                is_binary = any(binary_type in content_type.lower() for binary_type in [
                    'image/', 'video/', 'audio/', 'font/', 'application/octet-stream', 
                    'application/zip', 'application/x-rar', 'application/pdf', 'application/vnd.'
                ])
                
                # If binary or content-type suggests binary, return raw content
                if is_binary:
                    return response.content
                
                # For text content types
                is_text = any(text_type in content_type.lower() for text_type in [
                    'text/', 'application/json', 'application/javascript', 'application/xml', 'application/xhtml'
                ])
                
                if is_text:
                    # Try to determine encoding
                    encoding = None
                    
                    # From Content-Type header
                    if 'charset=' in content_type:
                        encoding = content_type.split('charset=')[1].split(';')[0].strip()
                    
                    # From response encoding or apparent encoding
                    if not encoding:
                        encoding = response.encoding or response.apparent_encoding or 'utf-8'
                    
                    # Decode with specified encoding
                    try:
                        return response.content.decode(encoding, errors='replace').encode('utf-8')
                    except (UnicodeDecodeError, LookupError):
                        # If decoding fails, try utf-8
                        try:
                            return response.content.decode('utf-8', errors='replace').encode('utf-8')
                        except:
                            # If all else fails, return raw content
                            return response.content
                
                # For unknown content types, return raw content
                return response.content
            elif response.status_code == 404:
                print(f"Resource not found (404): {url}")
                return None
            elif response.status_code == 403:
                print(f"Access forbidden (403): {url}")
                # Try with a different user agent on the next retry
                headers['User-Agent'] = random.choice(user_agents)
                retry_count += 1
                time.sleep(1)  # Wait longer before retrying
                continue
            elif response.status_code >= 500:
                print(f"Server error ({response.status_code}): {url}")
                retry_count += 1
                time.sleep(1)  # Wait longer before retrying
                continue
            else:
                print(f"HTTP error ({response.status_code}): {url}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"Timeout error downloading {url}")
            retry_count += 1
            time.sleep(1)
            continue
        except requests.exceptions.ConnectionError:
            print(f"Connection error downloading {url}")
            retry_count += 1
            time.sleep(1)
            continue
        except requests.exceptions.TooManyRedirects:
            print(f"Too many redirects for {url}")
            return None
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            return None
    
    if retry_count == max_retries:
        print(f"Max retries reached for {url}")
    
    return None

def get_asset_type(url):
    """Determine the type of asset from the URL"""
    # Handle empty or None URLs
    if not url:
        return 'other'
    
    url_lower = url.lower()
    
    # Framework-specific patterns
    if '_next/static' in url_lower:
        if '.css' in url_lower or 'styles' in url_lower:
            return 'css'
        return 'js'  # Default to JS for Next.js assets
        
    if 'chunk.' in url_lower or 'webpack' in url_lower:
        return 'js'  # Webpack chunks
        
    if 'angular' in url_lower and '.js' in url_lower:
        return 'js'  # Angular bundles
        
    # Handle CSS files
    if url_lower.endswith(('.css', '.scss', '.less', '.sass')):
        return 'css'
    if 'global.css' in url_lower or 'globals.css' in url_lower or 'tailwind' in url_lower:
        return 'css'
    if 'fonts.googleapis.com' in url_lower:
        return 'css'
    if 'styles' in url_lower and '.css' in url_lower:
        return 'css'
        
    # Handle JS files
    if url_lower.endswith(('.js', '.jsx', '.mjs', '.ts', '.tsx', '.cjs')):
        return 'js'
    if 'bundle.js' in url_lower or 'main.js' in url_lower or 'app.js' in url_lower:
        return 'js'
    if 'polyfill' in url_lower or 'runtime' in url_lower or 'vendor' in url_lower:
        return 'js'
    if 'image-config' in url_lower or 'image.config' in url_lower:
        return 'js'
        
    # Handle image files
    if url_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif', '.bmp', '.ico')):
        return 'img'
    if '/images/' in url_lower or '/img/' in url_lower or '/assets/images/' in url_lower:
        return 'img'
        
    # Handle font files
    if url_lower.endswith(('.woff', '.woff2', '.ttf', '.otf', '.eot')):
        return 'fonts'
    if '/fonts/' in url_lower or 'font-awesome' in url_lower:
        return 'fonts'
        
    # Handle media files
    if url_lower.endswith(('.mp4', '.webm', '.ogg', '.avi', '.mov', '.flv')):
        return 'videos'
    if url_lower.endswith(('.mp3', '.wav', '.ogg', '.aac')):
        return 'audio'
        
    # Handle favicon
    if url_lower.endswith(('.ico', '.icon')):
        return 'favicons'
    if 'favicon' in url_lower:
        return 'favicons'
        
    # Handle special API endpoints
    if 'graphql' in url_lower or 'api.' in url_lower:
        return 'js'
        
    # Try to guess based on URL structure
    if '/css/' in url_lower:
        return 'css'
    if '/js/' in url_lower or '/scripts/' in url_lower:
        return 'js'
    if '/static/' in url_lower and not any(ext in url_lower for ext in ['.css', '.js', '.png', '.jpg']):
        # For static assets with unclear type, check the URL itself
        if 'style' in url_lower:
            return 'css'
        return 'js'  # Default for static assets
        
    # For CDN resources, try to determine type from the host
    cdn_hosts = ['cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com']
    for host in cdn_hosts:
        if host in url_lower:
            if any(lib in url_lower for lib in ['react', 'angular', 'vue', 'jquery']):
                return 'js'
            if any(lib in url_lower for lib in ['bootstrap', 'tailwind', 'material', 'font']):
                return 'css'
    
    # Default to JS for unknown extensions
    return 'js'

def extract_metadata(soup, base_url):
    """Extract metadata from the HTML"""
    metadata = {
        'title': '',
        'description': '',
        'keywords': '',
        'og_tags': {},
        'twitter_cards': {},
        'canonical': '',
        'language': '',
        'favicon': '',
        'structured_data': []
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        metadata['title'] = title_tag.string.strip()
    
    # Extract meta tags
    meta_tags = soup.find_all('meta')
    for tag in meta_tags:
        # Description
        if tag.get('name') == 'description' and tag.get('content'):
            metadata['description'] = tag.get('content').strip()
        
        # Keywords
        elif tag.get('name') == 'keywords' and tag.get('content'):
            metadata['keywords'] = tag.get('content').strip()
        
        # OpenGraph tags
        elif tag.get('property') and tag.get('property').startswith('og:') and tag.get('content'):
            prop = tag.get('property')[3:]  # Remove 'og:' prefix
            metadata['og_tags'][prop] = tag.get('content').strip()
        
        # Twitter card tags
        elif tag.get('name') and tag.get('name').startswith('twitter:') and tag.get('content'):
            prop = tag.get('name')[8:]  # Remove 'twitter:' prefix
            metadata['twitter_cards'][prop] = tag.get('content').strip()
    
    # Extract canonical URL
    canonical_tag = soup.find('link', {'rel': 'canonical'})
    if canonical_tag and canonical_tag.get('href'):
        canonical_url = canonical_tag.get('href')
        if not canonical_url.startswith(('http://', 'https://')):
            canonical_url = urljoin(base_url, canonical_url)
        metadata['canonical'] = canonical_url
    
    # Extract language
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        metadata['language'] = html_tag.get('lang')
    
    # Extract favicon
    favicon_tag = soup.find('link', {'rel': 'icon'}) or soup.find('link', {'rel': 'shortcut icon'})
    if favicon_tag and favicon_tag.get('href'):
        favicon_url = favicon_tag.get('href')
        if not favicon_url.startswith(('http://', 'https://')):
            favicon_url = urljoin(base_url, favicon_url)
        metadata['favicon'] = favicon_url
    
    # Extract structured data (JSON-LD)
    script_tags = soup.find_all('script', {'type': 'application/ld+json'})
    for tag in script_tags:
        if tag.string:
            try:
                json_data = json.loads(tag.string)
                metadata['structured_data'].append(json_data)
            except json.JSONDecodeError:
                pass
    
    return metadata

def get_component_type(element):
    """Determine the type of UI component based on element attributes and classes"""
    if not element:
        return None
        
    # Get tag name, classes, and ID
    tag_name = element.name
    class_list = element.get('class', [])
    if class_list and not isinstance(class_list, list):
        class_list = [class_list]
    class_str = ' '.join(class_list).lower() if class_list else ''
    element_id = element.get('id', '').lower()
    
    # Get element role
    role = element.get('role', '').lower()
    
    # Navigation components
    if tag_name == 'nav' or role == 'navigation' or 'nav' in class_str or 'navigation' in class_str or 'menu' in class_str or element_id in ['nav', 'navigation', 'menu']:
        return 'navigation'
    
    # Header components
    if tag_name == 'header' or role == 'banner' or 'header' in class_str or 'banner' in class_str or element_id in ['header', 'banner']:
        return 'header'
    
    # Footer components
    if tag_name == 'footer' or role == 'contentinfo' or 'footer' in class_str or element_id == 'footer':
        return 'footer'
    
    # Hero/banner components
    if 'hero' in class_str or 'banner' in class_str or 'jumbotron' in class_str or 'showcase' in class_str or element_id in ['hero', 'banner', 'jumbotron', 'showcase']:
        return 'hero'
    
    # Card components
    if 'card' in class_str or 'tile' in class_str or 'item' in class_str or element_id in ['card', 'tile']:
        return 'card'
    
    # Form components
    if tag_name == 'form' or role == 'form' or 'form' in class_str or element_id == 'form':
        return 'form'
    
    # CTA (Call to Action) components
    if 'cta' in class_str or 'call-to-action' in class_str or 'action' in class_str or element_id in ['cta', 'call-to-action']:
        return 'cta'
    
    # Sidebar components
    if 'sidebar' in class_str or 'side-bar' in class_str or element_id in ['sidebar', 'side-bar']:
        return 'sidebar'
    
    # Modal/Dialog components
    if role == 'dialog' or 'modal' in class_str or 'dialog' in class_str or 'popup' in class_str or element_id in ['modal', 'dialog', 'popup']:
        return 'modal'
    
    # Section components
    if tag_name == 'section' or role == 'region' or 'section' in class_str:
        return 'section'
    
    # Mobile components
    if 'mobile' in class_str or 'smartphone' in class_str or 'mobile-only' in class_str:
        return 'mobile'
    
    # Store/Product components
    if 'product' in class_str or 'store' in class_str or 'shop' in class_str or 'pricing' in class_str:
        return 'store'
    
    # Cart components
    if 'cart' in class_str or 'basket' in class_str or 'shopping-cart' in class_str or element_id in ['cart', 'basket', 'shopping-cart']:
        return 'cart'
    
    # If no specific type is identified, check if the element is a major container
    if tag_name in ['div', 'section', 'article'] and ('container' in class_str or 'wrapper' in class_str or 'content' in class_str):
        return 'container'
    
    # Default to unknown if no specific type is identified
    return 'other'

def extract_component_structure(soup):
    """Extract UI components from the HTML structure"""
    if not soup:
        return {}
        
    components = {
        'navigation': [],
        'header': [],
        'footer': [],
        'hero': [],
        'card': [],
        'form': [],
        'cta': [],
        'sidebar': [],
        'modal': [],
        'section': [],
        'store': [],
        'mobile': [],
        'cart': []
    }
    
    # Helper function to convert element to HTML string
    def element_to_html(element):
        return str(element)
    
    # Extract navigation components
    nav_elements = soup.find_all(['nav']) + soup.find_all(role='navigation') + soup.find_all(class_=lambda c: c and ('nav' in c.lower() or 'menu' in c.lower()))
    for element in nav_elements[:5]:  # Limit to 5 to avoid excessive extraction
        components['navigation'].append({
            'html': element_to_html(element)
        })
    
    # Extract header components
    header_elements = soup.find_all(['header']) + soup.find_all(role='banner') + soup.find_all(class_=lambda c: c and 'header' in c.lower())
    for element in header_elements[:2]:  # Usually only 1-2 headers per page
        components['header'].append({
            'html': element_to_html(element)
        })
    
    # Extract footer components
    footer_elements = soup.find_all(['footer']) + soup.find_all(role='contentinfo') + soup.find_all(class_=lambda c: c and 'footer' in c.lower())
    for element in footer_elements[:2]:  # Usually only 1-2 footers per page
        components['footer'].append({
            'html': element_to_html(element)
        })
    
    # Extract hero/banner components
    hero_elements = soup.find_all(class_=lambda c: c and ('hero' in c.lower() or 'banner' in c.lower() or 'jumbotron' in c.lower()))
    for element in hero_elements[:3]:  # Limit to 3
        components['hero'].append({
            'html': element_to_html(element)
        })
    
    # Extract card components - often these are repeated elements
    card_elements = soup.find_all(class_=lambda c: c and ('card' in c.lower() or 'tile' in c.lower()))
    
    # If we find many cards, just keep one of each unique structure
    unique_cards = {}
    for element in card_elements[:15]:  # Examine up to 15 cards
        # Use a simplified structure hash to identify similar cards
        structure_hash = str(len(element.find_all()))  # Number of child elements
        if structure_hash not in unique_cards:
            unique_cards[structure_hash] = element
    
    # Add unique cards to components
    for idx, element in enumerate(unique_cards.values()):
        if idx >= 5:  # Limit to 5 unique cards
            break
        components['card'].append({
            'html': element_to_html(element)
        })
    
    # Extract form components
    form_elements = soup.find_all(['form']) + soup.find_all(class_=lambda c: c and 'form' in c.lower())
    for element in form_elements[:3]:  # Limit to 3
        components['form'].append({
            'html': element_to_html(element)
        })
    
    # Extract CTA components
    cta_elements = soup.find_all(class_=lambda c: c and ('cta' in c.lower() or 'call-to-action' in c.lower()))
    for element in cta_elements[:3]:  # Limit to 3
        components['cta'].append({
            'html': element_to_html(element)
        })
    
    # Extract sidebar components
    sidebar_elements = soup.find_all(class_=lambda c: c and ('sidebar' in c.lower() or 'side-bar' in c.lower()))
    for element in sidebar_elements[:2]:  # Limit to 2
        components['sidebar'].append({
            'html': element_to_html(element)
        })
    
    # Extract modal/dialog components
    modal_elements = soup.find_all(role='dialog') + soup.find_all(class_=lambda c: c and ('modal' in c.lower() or 'dialog' in c.lower() or 'popup' in c.lower()))
    for element in modal_elements[:3]:  # Limit to 3
        components['modal'].append({
            'html': element_to_html(element)
        })
    
    # Extract section components
    section_elements = soup.find_all(['section']) + soup.find_all(role='region')
    # Filter to get only substantial sections
    substantial_sections = [element for element in section_elements if len(element.find_all()) > 3]  # Must have at least 3 child elements
    for element in substantial_sections[:5]:  # Limit to 5
        components['section'].append({
            'html': element_to_html(element)
        })
    
    # Extract mobile-specific components
    mobile_elements = soup.find_all(class_=lambda c: c and ('mobile' in c.lower() or 'smartphone' in c.lower() or 'mobile-only' in c.lower()))
    for element in mobile_elements[:3]:  # Limit to 3
        components['mobile'].append({
            'html': element_to_html(element)
        })
    
    # Extract store/product components
    store_elements = soup.find_all(class_=lambda c: c and ('product' in c.lower() or 'store' in c.lower() or 'shop' in c.lower() or 'pricing' in c.lower()))
    for element in store_elements[:5]:  # Limit to 5
        components['store'].append({
            'html': element_to_html(element)
        })
    
    # Extract cart components
    cart_elements = soup.find_all(class_=lambda c: c and ('cart' in c.lower() or 'basket' in c.lower() or 'shopping-cart' in c.lower()))
    for element in cart_elements[:2]:  # Limit to 2
        components['cart'].append({
            'html': element_to_html(element)
        })
    
    # Remove empty component types
    return {k: v for k, v in components.items() if v}

def extract_inline_styles(soup):
    """Extract all inline styles from the HTML"""
    inline_styles = {}
    elements_with_style = soup.select('[style]')
    
    for i, element in enumerate(elements_with_style):
        style_content = element.get('style')
        if style_content:
            class_name = f'extracted-inline-style-{i}'
            inline_styles[class_name] = style_content
            # Add the class to the element
            element['class'] = element.get('class', []) + [class_name]
            # Remove the inline style
            del element['style']
    
    return inline_styles

def extract_inline_javascript(soup):
    """Extract inline JavaScript from HTML content"""
    inline_js = []
    # Find all script tags without src attribute (inline scripts)
    for script in soup.find_all('script'):
        if not script.get('src') and script.string:
            inline_js.append(script.string.strip())
    
    if inline_js:
        return '\n\n/* --- INLINE SCRIPTS --- */\n\n'.join(inline_js)
    return ""

def extract_assets(html_content, base_url, session_obj=None, headers=None):
    """Extract all assets from HTML content"""
    assets = {
        'css': [],
        'js': [],
        'img': [],
        'fonts': [],
        'videos': [],
        'audio': [],
        'favicons': [],
        'font_families': set(),
        'metadata': {},
        'components': {}
    }
    
    if not html_content:
        print("Warning: Empty HTML content provided to extract_assets")
        return assets
    
    try:
        # Create BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if not soup or not soup.html:
            print("Warning: Could not parse HTML content properly")
            # Try with a more lenient parser
            soup = BeautifulSoup(html_content, 'html5lib')
            if not soup or not soup.html:
                print("Error: Failed to parse HTML with both parsers")
                return assets
        
        # Extract metadata
        try:
            assets['metadata'] = extract_metadata(soup, base_url)
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
            traceback.print_exc()
        
        # Extract all CSS files
        try:
            css_links = soup.find_all('link', {'rel': 'stylesheet'}) or []
            # Also look for preload links with as="style"
            preload_css = soup.find_all('link', {'rel': 'preload', 'as': 'style'}) or []
            
            for link in css_links + preload_css:
                href = link.get('href')
                if href:
                    if not href.startswith(('http://', 'https://', 'data:')):
                        href = urljoin(base_url, href)
                    if href.startswith(('http://', 'https://')):
                        assets['css'].append(href)
        except Exception as e:
            print(f"Error extracting CSS links: {str(e)}")
        
        # Look for Next.js specific CSS files
        try:
            next_css = soup.find_all('link', {'data-n-g': True}) or []
            next_css += soup.find_all('link', {'data-n-p': True}) or []
            for link in next_css:
                href = link.get('href')
                if href:
                    if not href.startswith(('http://', 'https://', 'data:')):
                        href = urljoin(base_url, href)
                    if href.startswith(('http://', 'https://')):
                        assets['css'].append(href)
        except Exception as e:
            print(f"Error extracting Next.js CSS: {str(e)}")
                    
        # Extract all inline styles and check for CSS imports or fonts
        try:
            style_tags = soup.find_all('style') or []
            for style in style_tags:
                style_content = style.string
                if style_content:
                    # Extract @import statements
                    import_urls = re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', style_content) or []
                    import_urls += re.findall(r'@import\s+url\([\'"]?([^\'"|\)]+)[\'"]?\)', style_content) or []
                    
                    for import_url in import_urls:
                        if not import_url.startswith(('http://', 'https://', 'data:')):
                            import_url = urljoin(base_url, import_url)
                        if import_url.startswith(('http://', 'https://')):
                            assets['css'].append(import_url)
                    
                    # Extract font families
                    font_families = re.findall(r'font-family:\s*[\'"]?([^\'";]+)[\'"]?', style_content) or []
                    for family in font_families:
                        family = family.strip().split(',')[0].strip('\'"`')
                        if family and family.lower() not in ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui']:
                            assets['font_families'].add(family)
        except Exception as e:
            print(f"Error extracting inline styles: {str(e)}")
    
        # Extract all JavaScript files
        try:
            script_tags = soup.find_all('script', {'src': True}) or []
            for script in script_tags:
                src = script.get('src')
                if src:
                    if not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        assets['js'].append(src)
            
            # Look for module scripts (common in modern frameworks)
            module_scripts = soup.find_all('script', {'type': 'module'}) or []
            for script in module_scripts:
                src = script.get('src')
                if src:
                    if not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        assets['js'].append(src)
        except Exception as e:
            print(f"Error extracting JavaScript: {str(e)}")
        
        # Extract all images
        try:
            # Regular img tags
            img_tags = soup.find_all('img') or []
            for img in img_tags:
                # Check src attribute
                src = img.get('src')
                if src:
                    if not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        assets['img'].append(src)
                
                # Check srcset attribute
                srcset = img.get('srcset')
                if srcset:
                    for src_str in srcset.split(','):
                        src_parts = src_str.strip().split(' ')
                        if src_parts:
                            src = src_parts[0]
                            if not src.startswith(('http://', 'https://', 'data:')):
                                src = urljoin(base_url, src)
                            if src.startswith(('http://', 'https://')):
                                assets['img'].append(src)
                
                # Check data-src (lazy loading)
                data_src = img.get('data-src')
                if data_src:
                    if not data_src.startswith(('http://', 'https://', 'data:')):
                        data_src = urljoin(base_url, data_src)
                    if data_src.startswith(('http://', 'https://')):
                        assets['img'].append(data_src)
            
            # Background images in style attributes
            elements_with_style = soup.select('[style]') or []
            for element in elements_with_style:
                style = element.get('style', '')
                if 'background' in style or 'background-image' in style:
                    # Try to extract URLs
                    bg_urls = re.findall(r'url\([\'"]?([^\'"|\)]+)[\'"]?\)', style)
                    for bg_url in bg_urls:
                        if not bg_url.startswith(('http://', 'https://', 'data:')):
                            bg_url = urljoin(base_url, bg_url)
                        if bg_url.startswith(('http://', 'https://')):
                            assets['img'].append(bg_url)
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
        
        # Extract favicon
        try:
            favicon_links = soup.find_all('link', {'rel': lambda r: r and (r.lower() == 'icon' or 'icon' in r.lower().split())}) or []
            for link in favicon_links:
                href = link.get('href')
                if href:
                    if not href.startswith(('http://', 'https://', 'data:')):
                        href = urljoin(base_url, href)
                    if href.startswith(('http://', 'https://')):
                        assets['favicons'].append(href)
        except Exception as e:
            print(f"Error extracting favicons: {str(e)}")
        
        # Extract all video sources
        try:
            video_tags = soup.find_all('video') or []
            for video in video_tags:
                # Check src attribute
                src = video.get('src')
                if src:
                    if not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        assets['videos'].append(src)
                
                # Check source tags inside video
                source_tags = video.find_all('source') or []
                for source in source_tags:
                    src = source.get('src')
                    if src:
                        if not src.startswith(('http://', 'https://', 'data:')):
                            src = urljoin(base_url, src)
                        if src.startswith(('http://', 'https://')):
                            assets['videos'].append(src)
        except Exception as e:
            print(f"Error extracting videos: {str(e)}")
        
        # Extract all audio sources
        try:
            audio_tags = soup.find_all('audio') or []
            for audio in audio_tags:
                # Check src attribute
                src = audio.get('src')
                if src:
                    if not src.startswith(('http://', 'https://', 'data:')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        assets['audio'].append(src)
                
                # Check source tags inside audio
                source_tags = audio.find_all('source') or []
                for source in source_tags:
                    src = source.get('src')
                    if src:
                        if not src.startswith(('http://', 'https://', 'data:')):
                            src = urljoin(base_url, src)
                        if src.startswith(('http://', 'https://')):
                            assets['audio'].append(src)
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
        
        # Extract all iframes
        try:
            iframe_tags = soup.find_all('iframe') or []
            for iframe in iframe_tags:
                src = iframe.get('src')
                if src and not src.startswith('data:'):
                    if not src.startswith(('http://', 'https://')):
                        src = urljoin(base_url, src)
                    if src.startswith(('http://', 'https://')):
                        if 'youtube' in src or 'vimeo' in src:
                            assets['videos'].append(src)
                        else:
                            assets['js'].append(src)  # Treat as JS resource
        except Exception as e:
            print(f"Error extracting iframes: {str(e)}")
        
        # Extract Next.js specific resources
        try:
            # Look for Next.js data scripts
            next_data = soup.find('script', {'id': '__NEXT_DATA__'})
            if next_data and next_data.string:
                try:
                    next_json = json.loads(next_data.string)
                    # Extract buildId
                    if 'buildId' in next_json:
                        build_id = next_json['buildId']
                        # Add common Next.js resources with this buildId
                        for path in ['main', 'webpack', 'framework', 'pages/_app', 'pages/_error', 'pages/index']:
                            chunk_url = f"{base_url}/_next/static/{build_id}/pages/{path}.js"
                            assets['js'].append(chunk_url)
                        
                    # Extract page data
                    if 'page' in next_json and 'props' in next_json.get('props', {}):
                        # This often has valuable data we might want to preserve
                        assets['metadata']['next_data'] = next_json
                except Exception as next_error:
                    print(f"Error parsing Next.js data: {str(next_error)}")
            
            # Look for Webpack chunks in comments
            chunks_regex = r'/\*\s*webpackJsonp\s*\*/(.*?)/\*\s*end\s*webpackJsonp\s*\*/'
            chunks_matches = re.findall(chunks_regex, html_content, re.DOTALL)
            if chunks_matches:
                print("Found webpack chunks in comments")
                # These are JavaScript assets that might be dynamically loaded
        except Exception as e:
            print(f"Error extracting Next.js resources: {str(e)}")
        
        # Try to download CSS files and extract additional assets
        if session_obj and headers:
            try:
                css_urls = assets['css'].copy()  # Copy to avoid modifying during iteration
                for css_url in css_urls:
                    try:
                        # Skip data URLs
                        if css_url.startswith('data:'):
                            continue
                            
                        # Download CSS file
                        response = session_obj.get(
                            css_url, 
                            timeout=10, 
                            headers=headers,
                            verify=False  # Ignore SSL certificate errors
                        )
                        
                        if response.status_code == 200:
                            css_content = response.text
                            
                            # Extract URLs from url() function
                            url_matches = re.findall(r'url\([\'"]?([^\'"|\)]+)[\'"]?\)', css_content) or []
                            for url in url_matches:
                                if not url or url.startswith('data:'):
                                    continue
                                    
                                if not url.startswith(('http://', 'https://')):
                                    # Resolve relative to the CSS file
                                    url = urljoin(css_url, url)
                                    
                                # Determine asset type
                                asset_type = get_asset_type(url)
                                if asset_type in assets:
                                    assets[asset_type].append(url)
                            
                            # Extract font families
                            font_families = re.findall(r'font-family:\s*[\'"]?([^\'";]+)[\'"]?', css_content) or []
                            for family in font_families:
                                family = family.strip().split(',')[0].strip('\'"`')
                                if family and family.lower() not in ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui']:
                                    assets['font_families'].add(family)
                            
                            # Extract Google Fonts specifically
                            google_fonts_imports = re.findall(r'@import\s+url\([\'"]?(https?://fonts\.googleapis\.com/[^\'"|\)]+)[\'"]?\)', css_content) or []
                            for font_url in google_fonts_imports:
                                if font_url not in assets['css']:
                                    assets['css'].append(font_url)
                                    
                            # Check for Tailwind
                            if 'tailwind' in css_content.lower() or '.tw-' in css_content:
                                print("Detected Tailwind CSS in stylesheets")
                    except Exception as css_error:
                        print(f"Error processing CSS {css_url}: {str(css_error)}")
            except Exception as e:
                print(f"Error processing CSS files: {str(e)}")
        
        # Extract UI components
        try:
            components = extract_component_structure(soup)
            if components:
                assets['components'] = components
        except Exception as e:
            print(f"Error extracting components: {str(e)}")
            traceback.print_exc()
        
        # Remove duplicates while preserving order
        for asset_type in assets:
            if isinstance(assets[asset_type], list):
                # Use dict.fromkeys to remove duplicates while preserving order
                assets[asset_type] = list(dict.fromkeys(assets[asset_type]))
                
        return assets
        
    except Exception as e:
        print(f"Error in extract_assets: {str(e)}")
        traceback.print_exc()
        return assets

def create_zip_file(html_content, assets, url, session_obj, headers, screenshots=None):
    """Create a zip file containing the extracted website data"""
    # Create a temp file for the zip
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    # Extract domain for the folder name
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create the zip file
    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Write the main HTML
        zipf.writestr('index.html', html_content)
        
        # Create directories for each asset type
        for asset_type in assets.keys():
            if asset_type in ['font_families', 'metadata', 'components']:
                continue  # Skip non-URL assets
                
            # Make sure the assets[asset_type] exists and is a list before iterating
            if not assets[asset_type] or not isinstance(assets[asset_type], list):
                print(f"  Skipping {asset_type} - no assets found or invalid format")
                continue
                
            # Create the directory
            zipf.writestr(f'{asset_type}/.gitkeep', '')
            
            # Download each asset
            processed_urls = set()  # Track processed URLs to avoid duplicates
            
            for url in assets[asset_type]:
                # Skip if the URL is None, empty, or a data URL
                if not url or url.startswith('data:'):
                    continue
                    
                # Skip if we've already processed this URL
                if url in processed_urls:
                    continue
                    
                processed_urls.add(url)
                    
                try:
                    # Fix URL if it's relative
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        parsed_base = urlparse(parsed_url.scheme + '://' + parsed_url.netloc)
                        url = urljoin(parsed_base.geturl(), url)
                        
                    # Extract filename from URL
                    path = urlparse(url).path
                    # Handle query parameters in the URL
                    query = urlparse(url).query
                    filename = os.path.basename(unquote(path))
                    
                    # Clean filename
                    if not filename:
                        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{asset_type}"
                    elif '.' not in filename:
                        filename = f"{filename}.{asset_type}"
                        
                    # Add query parameters to filename to make it unique
                    if query:
                        clean_query = re.sub(r'[^a-zA-Z0-9]', '_', query)[:30]  # Limit length
                        name, ext = os.path.splitext(filename)
                        filename = f"{name}_{clean_query}{ext}"
                        
                    # Avoid duplicate filenames with UUID
                    file_path = f"{asset_type}/{filename}"
                    
                    try:
                        # Download the file
                        response = session_obj.get(
                            url, 
                            timeout=10, 
                            headers=headers,
                            verify=False  # Ignore SSL certificate errors
                        )
                        
                        if response.status_code == 200:
                            zipf.writestr(file_path, response.content)
                            print(f"  Added {file_path}")
                        else:
                            print(f"  Failed to download {url}, status: {response.status_code}")
                    except Exception as e:
                        print(f"  Error downloading {url}: {str(e)}")
                except Exception as e:
                    print(f"  Error processing URL {url}: {str(e)}")
        
        # Handle font families
        if 'font_families' in assets and assets['font_families']:
            zipf.writestr('css/fonts.css', '\n'.join([
                f"/* Font Family: {family} */\n"
                f"@import url('https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}&display=swap');\n"
                for family in assets['font_families']
            ]))
            
        # Handle metadata if present
        if 'metadata' in assets and assets['metadata']:
            metadata_content = json.dumps(assets['metadata'], indent=2)
            zipf.writestr('metadata.json', metadata_content)
            
        # Handle UI components if present
        if 'components' in assets and assets['components'] and isinstance(assets['components'], dict):
            # Create components directory
            zipf.writestr('components/.gitkeep', '')
            
            # Create index for components
            component_html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Extracted UI Components</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                    .component { margin-bottom: 40px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }
                    .component-header { background: #f5f5f5; padding: 10px 15px; border-bottom: 1px solid #ddd; }
                    .component-content { padding: 15px; }
                    .component-code { background: #f8f8f8; padding: 15px; border-top: 1px solid #ddd; white-space: pre-wrap; overflow-x: auto; }
                    h1, h2 { color: #333; }
                    pre { margin: 0; }
                </style>
            </head>
            <body>
                <h1>Extracted UI Components</h1>
                <p>The following components were extracted from the website.</p>
            """
            
            # Add each component
            for component_type, components in assets['components'].items():
                if components:
                    component_html += f'<h2>{component_type.replace("_", " ").title()} Components</h2>'
                    
                    for i, component in enumerate(components):
                        html_code = component.get('html', '')
                        if html_code:
                            component_html += f"""
                            <div class="component">
                                <div class="component-header">
                                    <strong>{component_type.replace("_", " ").title()} {i+1}</strong>
                                </div>
                                <div class="component-content">
                                    {html_code}
                                </div>
                                <div class="component-code">
                                    <pre>{html.escape(html_code)}</pre>
                                </div>
                            </div>
                            """
            
            component_html += """
            </body>
            </html>
            """
            
            zipf.writestr('components/index.html', component_html)
            
            # Save individual components
            for component_type, components in assets['components'].items():
                if components:
                    zipf.writestr(f'components/{component_type}/.gitkeep', '')
                    
                    for i, component in enumerate(components):
                        html_code = component.get('html', '')
                        if html_code:
                            zipf.writestr(f'components/{component_type}/component_{i+1}.html', html_code)
        
        # Create a README file
        readme_content = f"""# Website Clone: {domain}

Extracted on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Source URL: {url}

## Contents

- `index.html`: Main HTML file
- `css/`: Stylesheets
- `js/`: JavaScript files
- `img/`: Images
- `fonts/`: Font files
- `components/`: Extracted UI components
- `metadata.json`: Website metadata (title, description, etc.)

## How to Use

1. Unzip this file
2. Open `index.html` in your browser
3. For best results, serve the files with a local server:
   ```
   python -m http.server
   ```
   Then open http://localhost:8000 in your browser

## Component Viewer

If components were extracted, you can view them by opening `components/index.html`

## Notes

- Some assets might not load correctly due to cross-origin restrictions
- External resources and APIs may not work without proper configuration
- JavaScript functionality might be limited without a proper backend

## Handling Modern Frameworks

This extraction has been optimized to handle the following frameworks:
- React and Next.js: Script chunks and module loading
- Angular: Component structure and scripts
- Tailwind CSS: Utility classes and structure

Generated by Website Extractor
"""
        zipf.writestr('README.md', readme_content)
    
    return temp_zip.name

def extract_with_selenium(url, timeout=30):
    """
    Extract rendered HTML content using Selenium with Chrome/Chromium.
    This method will execute JavaScript and capture the fully rendered page structure.
    
    Args:
        url: URL to fetch
        timeout: Maximum time to wait for page to load (seconds)
        
    Returns:
        tuple: (html_content, discovered_urls, None)
    """
    if not SELENIUM_AVAILABLE:
        return None, None, {"error": "Selenium is not installed. Run: pip install selenium webdriver-manager"}
    
    try:
        print("Setting up advanced Chrome options...")
        # Set up Chrome options with anti-detection measures
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless
        chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
        chrome_options.add_argument("--no-sandbox")  # Required for running as root
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--window-size=1920,1080")  # Set window size
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
        chrome_options.add_argument("--disable-extensions")  # Disable extensions
        chrome_options.add_argument("--disable-infobars")  # Disable infobars
        
        # Avoid detection as a bot
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Add modern user agent to avoid detection
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        # Initialize the Chrome driver
        print(f"Initializing Chrome WebDriver...")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as driver_error:
            print(f"Error initializing Chrome WebDriver: {str(driver_error)}")
            print("Trying alternative initialization method...")
            try:
                # Try alternative initialization without Service object
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as alt_error:
                print(f"Alternative initialization also failed: {str(alt_error)}")
                return None, None, {"error": f"Failed to initialize Chrome WebDriver: {str(alt_error)}"}
        
        # Set page load timeout
        driver.set_page_load_timeout(timeout)
        
        # Used to store discovered URLs
        discovered_urls = []
        
        try:
            print(f"Navigating to {url}...")
            driver.get(url)
            
            # Wait for page to be fully loaded
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception as e:
                print(f"Warning: Timeout waiting for body element: {str(e)}")
            
            # Execute JavaScript to disable animation
            try:
                driver.execute_script("""
                    var style = document.createElement('style');
                    style.type = 'text/css';
                    style.innerHTML = '* { animation-duration: 0.001s !important; transition-duration: 0.001s !important; }';
                    document.getElementsByTagName('head')[0].appendChild(style);
                """)
                print("Animations disabled to improve extraction")
            except Exception as e:
                print(f"Warning: Could not disable animations: {str(e)}")
            
            # Wait for page to be fully rendered
            print("Waiting for dynamic content to load...")
            try:
                # Wait a bit for any dynamic content to load
                time.sleep(5)
                
                # Wait for network to be idle
                driver.execute_script("return window.performance.getEntriesByType('resource').length")
                time.sleep(2)  # Wait a bit more after resources are loaded
            except Exception as e:
                print(f"Warning while waiting for dynamic content: {str(e)}")
            
            # Implement advanced scrolling to trigger lazy loading
            print("Performing advanced scrolling to trigger lazy loading...")
            try:
                # Get the total height of the page
                total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight, document.documentElement.offsetHeight, document.body.clientHeight, document.documentElement.clientHeight);")
                
                # Scroll down the page in steps
                viewport_height = driver.execute_script("return window.innerHeight")
                scroll_steps = max(1, min(20, total_height // viewport_height))  # Cap at 20 steps
                
                for i in range(scroll_steps + 1):
                    scroll_position = (i * total_height) // scroll_steps
                    driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                    
                    # Small pause to allow content to load
                    time.sleep(0.3)
                    
                    # Extract resources after each scroll
                    try:
                        urls = driver.execute_script("""
                            var resources = [];
                            // Get all link hrefs
                            document.querySelectorAll('link[rel="stylesheet"], link[as="style"]').forEach(function(el) {
                                if (el.href) resources.push(el.href);
                            });
                            // Get all script srcs
                            document.querySelectorAll('script[src]').forEach(function(el) {
                                if (el.src) resources.push(el.src);
                            });
                            // Get all image srcs
                            document.querySelectorAll('img[src]').forEach(function(el) {
                                if (el.src && !el.src.startsWith('data:')) resources.push(el.src);
                            });
                            return resources;
                        """)
                        discovered_urls.extend(urls)
                    except Exception as res_error:
                        print(f"Error extracting resources during scroll: {str(res_error)}")
                
                # Scroll back to top
                driver.execute_script("window.scrollTo(0, 0);")
                
                # Wait for everything to settle after scrolling
                time.sleep(1)
            except Exception as scroll_error:
                print(f"Error during page scrolling: {str(scroll_error)}")
            
            # Try to click on common elements that might reveal more content
            try:
                # Common UI elements that might reveal more content when clicked
                for selector in [
                    'button.load-more', '.show-more', '.expand', '.accordion-toggle', 
                    '[aria-expanded="false"]', '.menu-toggle', '.navbar-toggler',
                    '.mobile-menu-button', '.hamburger', '[data-toggle="collapse"]'
                ]:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements[:3]:  # Limit to first 3 matches of each type
                            if element.is_displayed():
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(0.5)  # Wait for content to appear
                    except Exception as click_error:
                        # Skip any errors and continue with next selector
                        continue
                print("Attempted to expand hidden content")
            except Exception as interact_error:
                print(f"Error expanding content: {str(interact_error)}")
            
            # Get the final HTML content after all JavaScript executed
            html_content = driver.page_source
            print(f"HTML content captured ({len(html_content)} bytes)")
            
            # Extract URLs for modern frameworks
            try:
                # React/Next.js specific resources
                next_js_urls = driver.execute_script("""
                    var resources = [];
                    // Find Next.js specific scripts
                    document.querySelectorAll('script[src*="_next"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    // Find chunk files
                    document.querySelectorAll('script[src*="chunk"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    // Find webpack files
                    document.querySelectorAll('script[src*="webpack"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    // Find hydration scripts
                    document.querySelectorAll('script[src*="hydration"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    return resources;
                """)
                discovered_urls.extend(next_js_urls)
                
                # Angular specific resources
                angular_urls = driver.execute_script("""
                    var resources = [];
                    // Find Angular specific scripts
                    document.querySelectorAll('script[src*="runtime"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    document.querySelectorAll('script[src*="polyfills"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    document.querySelectorAll('script[src*="main"]').forEach(function(el) {
                        resources.push(el.src);
                    });
                    return resources;
                """)
                discovered_urls.extend(angular_urls)
                
                # Get CSS variables for Tailwind detection
                tailwind_check = driver.execute_script("""
                    var style = window.getComputedStyle(document.body);
                    var hasTailwind = false;
                    // Check for common Tailwind classes
                    if (document.querySelector('.flex') && 
                        document.querySelector('.grid') && 
                        document.querySelector('.text-')) {
                        hasTailwind = true;
                    }
                    return hasTailwind;
                """)
                
                if tailwind_check:
                    print("Tailwind CSS detected, including appropriate CSS files")
            except Exception as framework_error:
                print(f"Error detecting framework resources: {str(framework_error)}")
            
            # Remove duplicates from discovered URLs
            discovered_urls = list(set(discovered_urls))
            print(f"Discovered {len(discovered_urls)} resource URLs")
            
            return html_content, discovered_urls, None
            
        except TimeoutException:
            print(f"Timeout while loading {url}")
            return None, None, {"error": "Timeout while loading page"}
        except WebDriverException as e:
            print(f"Selenium error: {str(e)}")
            return None, None, {"error": f"Selenium error: {str(e)}"}
        finally:
            # Close the browser
            print("Closing WebDriver...")
            driver.quit()
    
    except Exception as e:
        print(f"Error setting up Selenium: {str(e)}")
        return None, None, {"error": f"Error setting up Selenium: {str(e)}"}

def fix_relative_urls(html_content, base_url):
    """Fix relative URLs in the HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Fix relative URLs for links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/'):
            link['href'] = urljoin(base_url, href)
    
    # Fix relative URLs for images
    for img in soup.find_all('img', src=True):
        src = img['src']
        if not src.startswith(('http://', 'https://', 'data:')):
            img['src'] = urljoin(base_url, src)
    
    # Fix relative URLs for scripts
    for script in soup.find_all('script', src=True):
        src = script['src']
        if not src.startswith(('http://', 'https://', 'data:')):
            script['src'] = urljoin(base_url, src)
    
    # Fix relative URLs for stylesheets
    for link in soup.find_all('link', href=True):
        href = link['href']
        if not href.startswith(('http://', 'https://', 'data:')):
            link['href'] = urljoin(base_url, href)
    
    return str(soup)

@app.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')

@app.route('/clear')
def clear_session():
    """Clear the session data"""
    session.clear()
    return jsonify({'message': 'Session cleared'})

@app.route('/extract', methods=['POST'])
def extract():
    url = request.form.get('url')
    use_selenium = request.form.get('use_selenium') == 'true'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Add http:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"\n{'='*80}\nStarting extraction for: {url}\n{'='*80}")
        
        # Create a session to maintain cookies
        session_obj = requests.Session()
        
        # Disable SSL verification warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # List of user agents to try if we get blocked
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        ]
        
        # List of referers to try
        referers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://www.instagram.com/',
            'https://www.facebook.com/',
            'https://www.twitter.com/',
            'https://www.linkedin.com/'
        ]
        
        # Initial headers (will be rotated if needed)
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': random.choice(referers),
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        html_content = None
        additional_urls = []
        
        # Use Selenium for rendering if requested and available
        if use_selenium and SELENIUM_AVAILABLE:
            print("Using Selenium for advanced rendering...")
            html_content, additional_urls, error_info = extract_with_selenium(url)
            
            if not html_content:
                print("Selenium extraction failed, falling back to regular request")
                use_selenium = False
                # Check if we have an error message
                if error_info and isinstance(error_info, dict) and 'error' in error_info:
                    print(f"Selenium error: {error_info['error']}")
        
        # If Selenium wasn't used or failed, use regular requests with retries
        if not use_selenium or not html_content:
            # Maximum number of retries with different configurations
            max_retries = 5
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries and not html_content:
                try:
                    print(f"HTTP Request attempt {retry_count+1}/{max_retries} for: {url}")
                    print(f"Using User-Agent: {headers['User-Agent'][:30]}...")
                    
                    # First request to get cookies and possible redirects
                    response = session_obj.get(
                        url, 
                        timeout=20,  # Increased timeout 
                        headers=headers, 
                        allow_redirects=True,
                        verify=False  # Ignore SSL certificate errors
                    )
                    
                    # Follow redirects manually if needed
                    if response.history:
                        print(f"Request was redirected {len(response.history)} times")
                        for i, resp in enumerate(response.history):
                            print(f"  Redirect {i+1}: {resp.url} -> {resp.headers.get('Location')}")
                        print(f"  Final URL: {response.url}")
                        url = response.url  # Update URL to the final destination
                    
                    # Handle different status codes
                    if response.status_code == 200:
                        print(f"Success! Received 200 OK response ({len(response.content)} bytes)")
                        
                        # Determine encoding from Content-Type header or content
                        content_type = response.headers.get('Content-Type', '')
                        print(f"Content-Type: {content_type}")
                        
                        # Get encoding from headers or meta tag
                        encoding = None
                        
                        # Try to get encoding from Content-Type header
                        if 'charset=' in content_type:
                            encoding = content_type.split('charset=')[1].split(';')[0].strip()
                            print(f"Encoding from headers: {encoding}")
                        
                        # If no encoding specified, try to detect from content
                        if not encoding:
                            # Look for <meta charset="..."> tag
                            charset_match = re.search(r'<meta.*?charset=["\']*([^\s"\'/>]+)', response.text, re.IGNORECASE)
                            if charset_match:
                                encoding = charset_match.group(1)
                                print(f"Encoding from meta charset tag: {encoding}")
                            else:
                                # Look for <meta http-equiv="Content-Type" content="text/html; charset=...">
                                http_equiv_match = re.search(r'<meta.*?http-equiv=["\']*content-type["\']*.*?content=["\']*.*?charset=([^\s"\'/>]+)', response.text, re.IGNORECASE)
                                if http_equiv_match:
                                    encoding = http_equiv_match.group(1)
                                    print(f"Encoding from meta http-equiv tag: {encoding}")
                        
                        # If still no encoding, use apparent encoding from requests
                        if not encoding and response.apparent_encoding:
                            encoding = response.apparent_encoding
                            print(f"Detected encoding: {encoding}")
                        
                        # Default to utf-8 if still no encoding
                        if not encoding:
                            encoding = 'utf-8'
                            print("Using default encoding: utf-8")
                        
                        # Decode content with detected encoding
                        try:
                            html_content = response.content.decode(encoding, errors='replace')
                            print(f"Successfully decoded HTML content with {encoding} encoding ({len(html_content)} bytes)")
                            break  # Exit the retry loop on success
                        except (UnicodeDecodeError, LookupError) as e:
                            print(f"Error decoding with {encoding}: {str(e)}, falling back to utf-8")
                            html_content = response.content.decode('utf-8', errors='replace')
                            break  # Exit the retry loop on success with fallback
                    
                    elif response.status_code == 403:  # Forbidden - likely bot protection
                        print(f"Received 403 Forbidden response - website is likely blocking scrapers")
                        
                        # If we have Selenium available as a fallback, try that instead
                        if SELENIUM_AVAILABLE and not use_selenium:
                            print("Trying Selenium as a fallback for 403 error...")
                            html_content, additional_urls, error_info = extract_with_selenium(url)
                            if html_content:
                                print("Successfully bypassed 403 with Selenium!")
                                break
                        
                        # Otherwise, rotate our headers and try again
                        headers['User-Agent'] = random.choice(user_agents)
                        headers['Referer'] = random.choice(referers)
                        
                        # Add some randomization to headers
                        if random.random() > 0.5:
                            headers['Accept-Language'] = random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8,en-US;q=0.7', 'en-CA,en;q=0.9,fr-CA;q=0.8'])
                        
                        # Try adding cookies if we have any from previous responses
                        if session_obj.cookies:
                            print(f"Using {len(session_obj.cookies)} cookies from previous responses")
                        
                        # Add delay to avoid rate limiting
                        delay = random.uniform(1.0, 3.0)
                        print(f"Waiting {delay:.2f} seconds before retrying...")
                        time.sleep(delay)
                        
                    elif response.status_code == 429:  # Too Many Requests
                        print(f"Received 429 Too Many Requests - rate limited")
                        
                        # Check if we have a Retry-After header
                        retry_after = response.headers.get('Retry-After')
                        if retry_after and retry_after.isdigit():
                            delay = int(retry_after) + random.uniform(0.1, 1.0)
                        else:
                            delay = 5 + random.uniform(1.0, 5.0)  # 5-10 second delay
                        
                        print(f"Waiting {delay:.2f} seconds before retrying...")
                        time.sleep(delay)
                        
                        # Rotate headers
                        headers['User-Agent'] = random.choice(user_agents)
                        
                    elif response.status_code == 503:  # Service Unavailable - often used for anti-bot
                        print(f"Received 503 Service Unavailable - possible anti-bot measure")
                        
                        # Try with a longer delay and new headers
                        delay = 10 + random.uniform(1.0, 5.0)  # 10-15 second delay
                        print(f"Waiting {delay:.2f} seconds before retrying...")
                        time.sleep(delay)
                        
                        # Complete header rotation
                        headers['User-Agent'] = random.choice(user_agents)
                        headers['Referer'] = random.choice(referers)
                        
                    else:
                        print(f"Received unexpected status code: {response.status_code}")
                        last_error = f"HTTP error ({response.status_code})"
                        
                        # Try with new headers on next attempt
                        headers['User-Agent'] = random.choice(user_agents)
                
                except requests.exceptions.Timeout:
                    print(f"Timeout error fetching {url}")
                    last_error = "Request timeout"
                    # Try with increased timeout on next attempt
                    
                except requests.exceptions.ConnectionError:
                    print(f"Connection error fetching {url}")
                    last_error = "Connection error"
                    # Wait before retrying
                    time.sleep(2)
                    
                except requests.exceptions.TooManyRedirects:
                    print(f"Too many redirects for {url}")
                    last_error = "Too many redirects"
                    # This is likely a permanent issue, break the loop
                    break
                    
                except Exception as e:
                    print(f"Error fetching {url}: {str(e)}")
                    last_error = str(e)
                
                retry_count += 1
            
            # If we've exhausted all retries and still don't have content
            if not html_content and retry_count >= max_retries:
                error_msg = f"Failed to fetch website after {max_retries} attempts. Last error: {last_error}"
                print(error_msg)
                return jsonify({'error': error_msg}), 400
        
        # Safety check - make sure we have HTML content
        if not html_content or len(html_content) < 100:  # Arbitrary minimum size for valid HTML
            return jsonify({'error': 'Failed to extract valid HTML content from the website'}), 400
        
        # Continue with asset extraction and zip file creation
        try:
            print("\nExtracting assets...")
            # Extract assets from the HTML content
            assets = extract_assets(html_content, url, session_obj, headers)
            
            if not assets:
                return jsonify({'error': 'Failed to extract assets from the website'}), 500
                
            print(f"Assets extracted: {', '.join(assets.keys())}")
            
            # If we have additional URLs from Selenium, add them to the assets
            if additional_urls:
                print(f"Adding {len(additional_urls)} URLs discovered by Selenium")
                for asset_url in additional_urls:
                    # Skip data URLs
                    if not asset_url or asset_url.startswith('data:'):
                        continue
                        
                    # Normalize URL
                    if asset_url.startswith('//'):
                        asset_url = f"https:{asset_url}"
                    
                    try:
                        asset_type = get_asset_type(asset_url)
                        if asset_type in assets and asset_url not in assets[asset_type]:
                            # Validate URL
                            parsed = urlparse(asset_url)
                            if parsed.scheme and parsed.netloc:
                                assets[asset_type].append(asset_url)
                    except Exception as url_error:
                        print(f"Error processing URL {asset_url}: {str(url_error)}")
            
            # Count assets by type
            asset_counts = {asset_type: len(urls) for asset_type, urls in assets.items() 
                          if isinstance(urls, list) and asset_type not in ['metadata', 'font_families']}
            print(f"\nAsset counts:")
            for asset_type, count in asset_counts.items():
                print(f"  {asset_type}: {count}")
            
            # Check if we have enough assets
            total_assets = sum(count for count in asset_counts.values())
            if total_assets < 5:
                print("\nWARNING: Very few assets extracted. Trying alternative extraction methods...")
                
                # Try to extract assets from the page using JavaScript execution (simulated)
                try:
                    # Look for JavaScript variables that might contain asset URLs
                    js_asset_patterns = [
                        r'["\'](https?://[^"\']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))["\']',
                        r'["\'](/[^"\']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))["\']',
                        r'["\'](//[^"\']+\.(css|js|png|jpg|jpeg|gif|svg|woff2?))["\']',
                        r'loadCSS\(["\']([^"\']+)["\']',
                        r'loadJS\(["\']([^"\']+)["\']',
                        r'src=["\'](/[^"\']+)["\']',
                        r'href=["\'](/[^"\']+\.css)["\']',
                        # React/Next.js specific patterns
                        r'__NEXT_DATA__\s*=\s*({.*})',
                        r'window\.__PRELOADED_STATE__\s*=\s*({.*})',
                        r'window\.__INITIAL_STATE__\s*=\s*({.*})',
                        r'_ASSET_PREFIX_\s*=\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in js_asset_patterns:
                        matches = re.findall(pattern, html_content)
                        for match in matches:
                            if isinstance(match, tuple):
                                match_url = match[0]
                            else:
                                match_url = match
                                
                            if match_url.startswith('//'):
                                match_url = 'https:' + match_url
                            elif match_url.startswith('/'):
                                match_url = urljoin(url, match_url)
                                
                            # Skip if it's clearly not a URL (likely JSON data)
                            if '{' in match_url or '}' in match_url:
                                continue
                                
                            asset_type = get_asset_type(match_url)
                            if asset_type in assets:
                                assets[asset_type].append(match_url)
                    
                    print("Extracted additional assets from JavaScript patterns")
                except Exception as e:
                    print(f"Error extracting additional assets: {str(e)}")
            
            # Try to fix relative URLs in the HTML
            try:
                print("\nFixing relative URLs...")
                fixed_html = fix_relative_urls(html_content, url)
                print("Relative URLs fixed")
            except Exception as e:
                print(f"Error fixing URLs: {str(e)}")
                fixed_html = html_content  # Use original HTML if fixing fails
            
            try:
                # Create and send zip file, passing the session and headers
                print("\nCreating zip file...")
                
                # Extract domain from URL for the filename
                domain = urlparse(url).netloc
                safe_domain = re.sub(r'[^\w\-_]', '_', domain)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{safe_domain}_{timestamp}.zip"
                
                # Create a zip file with the extracted content
                zip_file_path = create_zip_file(fixed_html, assets, url, session_obj, headers)
                
                # Check if the file was created successfully
                if not os.path.exists(zip_file_path) or os.path.getsize(zip_file_path) < 100:
                    return jsonify({'error': 'Failed to create valid zip file'}), 500
                
                print(f"Zip file created successfully at {zip_file_path} ({os.path.getsize(zip_file_path)} bytes)")
                print(f"\nExtraction completed for: {url}\n{'='*80}")
                
                # Copy the temporary file to a more persistent location
                persistent_dir = os.path.join(tempfile.gettempdir(), 'website_extractor_downloads')
                os.makedirs(persistent_dir, exist_ok=True)
                persistent_path = os.path.join(persistent_dir, filename)

                # Copy the file instead of moving to ensure the original isn't deleted prematurely
                shutil.copy2(zip_file_path, persistent_path)

                # Schedule the temp file for deletion after a reasonable period (30 minutes)
                def delete_temp_file():
                    try:
                        time.sleep(1800)  # 30 minutes
                        if os.path.exists(zip_file_path):
                            os.remove(zip_file_path)
                            print(f"Temporary file {zip_file_path} removed after 30 minutes")
                        if os.path.exists(persistent_path):
                            os.remove(persistent_path)
                            print(f"Persistent file {persistent_path} removed after 30 minutes")
                    except Exception as e:
                        print(f"Error removing temporary file: {str(e)}")

                # Start a thread to handle file deletion
                cleanup_thread = threading.Thread(target=delete_temp_file)
                cleanup_thread.daemon = True
                cleanup_thread.start()

                # Send the persistent file with improved headers and explicit attachment
                response = send_file(
                    persistent_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=filename
                )

                # Add headers to prevent caching issues
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

                # Note: We're no longer using after_this_request to remove the file immediately
                # Instead, we're using a background thread to clean up after 30 minutes

                return response
                
            except Exception as e:
                print(f"Error creating or sending zip file: {str(e)}")
                traceback.print_exc()
                return jsonify({'error': f'Failed to create or send zip file: {str(e)}'}), 500
        except Exception as e:
            print(f"Error in asset extraction: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': f'Error extracting assets: {str(e)}'}), 500
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*80)
    print("Website Extractor is running!")
    print("Access it in your browser at: http://127.0.0.1:5001")
    print("="*80 + "\n")
    app.run(debug=True, threaded=True, port=5001) 

def main():
    """Entry point for the package, to allow running as an installed package from command line"""
    print("\n" + "="*80)
    print("Website Extractor is running!")
    print("Access it in your browser at: http://127.0.0.1:5001")
    print("="*80 + "\n")
    app.run(debug=True, threaded=True, port=5001) 