#!/usr/bin/env python3
"""
Comprehensive Vehicle Scraper for Red Deer Toyota
Extracts all required fields from vehicle detail pages
"""

import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class VehicleScraper:
    """Comprehensive vehicle scraper for Red Deer Toyota inventory"""
    
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def get_page(self, url, retries=3):
        """Fetch page with retry logic"""
        for attempt in range(retries):
            try:
                logger.info(f"  Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except requests.exceptions.RequestException as e:
                logger.error(f"  Error: {e}")
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    return None
        return None
    
    def extract_text_safe(self, element, default=''):
        """Safely extract and clean text from element"""
        if element:
            return ' '.join(element.get_text().strip().split())
        return default
    
    def extract_vehicle_links(self, soup):
        """Extract vehicle detail page links from listing page"""
        links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            
            # Match vehicle detail pages (not listing pages)
            if '/inventory/' in href:
                # Exclude listing pages
                if not any(x in href for x in ['/new/', '/used/', '/new', '/used', '?page=']):
                    full_url = urljoin(self.base_url, href)
                    # Clean URL (remove query params and fragments)
                    clean_url = full_url.split('?')[0].split('#')[0]
                    links.add(clean_url)
        
        return list(links)
    
    def extract_price(self, soup):
        """Extract vehicle price using multiple strategies"""
        
        # Strategy 1: JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'offers' in data and isinstance(data['offers'], dict):
                        if 'price' in data['offers']:
                            return str(int(float(data['offers']['price'])))
            except:
                pass
        
        # Strategy 2: Meta tags
        for meta in soup.find_all('meta'):
            if meta.get('property') == 'product:price:amount':
                content = meta.get('content', '')
                if content:
                    try:
                        return str(int(float(content)))
                    except:
                        pass
        
        # Strategy 3: Search for price elements (excluding MSRP)
        for elem in soup.find_all(class_=re.compile(r'price', re.I)):
            text = self.extract_text_safe(elem)
            if not any(kw in text.lower() for kw in ['msrp', 'was', 'original']):
                match = re.search(r'\$?\s*([0-9,]+)', text)
                if match:
                    try:
                        num = int(match.group(1).replace(',', ''))
                        if 5000 <= num <= 300000:
                            return str(num)
                    except:
                        pass
        
        # Strategy 4: Page text search
        page_text = soup.get_text()
        for match in re.finditer(r'(?:Price|Cost)?\s*:?\s*\$\s*([0-9,]+)', page_text):
            try:
                num = int(match.group(1).replace(',', ''))
                if 5000 <= num <= 300000:
                    # Check context for MSRP
                    start = max(0, match.start() - 50)
                    end = min(len(page_text), match.end() + 50)
                    context = page_text[start:end].lower()
                    if not any(kw in context for kw in ['msrp', 'was', 'original']):
                        return str(num)
            except:
                pass
        
        return ''
    
    def extract_msrp(self, soup):
        """Extract MSRP"""
        # Look for MSRP indicators
        for elem in soup.find_all(text=re.compile(r'MSRP|List Price', re.I)):
            if elem.parent:
                text = self.extract_text_safe(elem.parent)
                match = re.search(r'\$\s*([0-9,]+)', text)
                if match:
                    try:
                        num = int(match.group(1).replace(',', ''))
                        if 5000 <= num <= 300000:
                            return str(num)
                    except:
                        pass
        
        # Look for strikethrough prices
        for elem in soup.find_all(['del', 's', 'strike']):
            text = self.extract_text_safe(elem)
            match = re.search(r'\$\s*([0-9,]+)', text)
            if match:
                try:
                    num = int(match.group(1).replace(',', ''))
                    if 5000 <= num <= 300000:
                        return str(num)
                except:
                    pass
        
        return ''
    
    def extract_image(self, soup):
        """Extract primary vehicle image URL (avoiding logos)"""
        image_url = ''
        
        # Strategy 1: JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'image' in data:
                    img = data['image']
                    if isinstance(img, list):
                        img = img[0] if img else ''
                    if img:
                        # Verify it's not a logo
                        if not any(x in img.lower() for x in ['logo', 'icon', 'favicon']):
                            return urljoin(self.base_url, img)
                except:
                    pass
        
        # Strategy 2: Open Graph meta tags
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            if not any(x in img_url.lower() for x in ['logo', 'icon', 'favicon']):
                return urljoin(self.base_url, img_url)
        
        # Strategy 3: Look for vehicle gallery/slider images
        gallery_containers = soup.find_all(['div', 'section', 'ul'], 
                                          class_=re.compile(r'gallery|slider|carousel|photos?|images?', re.I))
        
        for container in gallery_containers:
            imgs = container.find_all('img')
            for img in imgs:
                src = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy', '')
                if src:
                    # Exclude logos, icons, small images
                    if any(x in src.lower() for x in ['logo', 'icon', 'favicon', 'banner', 'ad']):
                        continue
                    
                    # Check image size if available
                    width = img.get('width', '')
                    height = img.get('height', '')
                    if width and height:
                        try:
                            if int(width) < 200 or int(height) < 150:
                                continue
                        except:
                            pass
                    
                    return urljoin(self.base_url, src)
        
        # Strategy 4: Look for main vehicle image (common class patterns)
        main_image_selectors = [
            'img[class*="vehicle"]',
            'img[class*="main"]',
            'img[class*="primary"]',
            'img[class*="hero"]',
            'img[class*="feature"]',
            'img[id*="vehicle"]',
            'img[id*="main"]',
        ]
        
        for selector in main_image_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy', '')
                alt = img.get('alt', '').lower()
                
                if src:
                    # Exclude logos and small images
                    if any(x in src.lower() for x in ['logo', 'icon', 'favicon', 'thumb']):
                        continue
                    
                    # Prefer images with vehicle-related alt text
                    if any(kw in alt for kw in ['vehicle', 'car', 'truck', 'suv', 'van', 'auto']):
                        return urljoin(self.base_url, src)
                    
                    # Store as fallback
                    if not image_url:
                        image_url = urljoin(self.base_url, src)
        
        # Return fallback if found
        if image_url:
            return image_url
        
        # Strategy 5: First large, meaningful image on page
        all_imgs = soup.find_all('img')
        for img in all_imgs:
            src = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy', '')
            if not src:
                continue
            
            src_lower = src.lower()
            
            # Skip logos, icons, ads, tracking pixels
            exclude_keywords = ['logo', 'icon', 'favicon', 'banner', 'ad', 'pixel', 
                               'track', 'badge', 'award', '1x1', 'spacer', 'blank']
            if any(kw in src_lower for kw in exclude_keywords):
                continue
            
            # Skip very small images (likely not vehicle photos)
            width = img.get('width', '')
            height = img.get('height', '')
            if width and height:
                try:
                    if int(width) < 300 or int(height) < 200:
                        continue
                except:
                    pass
            
            # Check if image is in a header/nav/footer (skip those)
            parent_classes = []
            parent = img.parent
            for _ in range(3):  # Check up to 3 levels up
                if parent:
                    parent_classes.extend(parent.get('class', []))
                    parent = parent.parent
            
            parent_class_str = ' '.join(parent_classes).lower()
            if any(x in parent_class_str for x in ['header', 'nav', 'footer', 'menu']):
                continue
            
            # This is likely a vehicle image
            return urljoin(self.base_url, src)
        
        return image_url
    
    def scrape_vehicle(self, url):
        """Scrape a single vehicle detail page"""
        logger.info(f"\n{'─'*100}")
        logger.info(f"Scraping: {url}")
        
        soup = self.get_page(url)
        if not soup:
            return None
        
        # Initialize data structure with all required fields
        data = {
            'title': '',
            'id / stock-#': '',
            'price': '',
            'condition': '',
            'feed label': '',
            'body style': '',
            'brand': '',
            'certified pre-owned': '',
            'color': '',
            'description': '',
            'engine': '',
            'image link': '',
            'link': url,
            'mileage': '',
            'model': '',
            'trim / sub-model': '',
            'vehicle MSRP': '',
            'vehicle all in price': '',
            'vehicle option': '',
            'vin': '',
            'year': ''
        }
        
        page_text = soup.get_text()
        
        # Extract title
        h1 = soup.find('h1')
        if h1:
            data['title'] = self.extract_text_safe(h1)
            # Remove "New" or "Used" from title
            data['title'] = re.sub(r'\b(New|Used)\b', '', data['title'], flags=re.I).strip()
            # Clean up extra spaces
            data['title'] = ' '.join(data['title'].split())
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', data['title'] or page_text)
        if year_match:
            data['year'] = year_match.group(1)
        
        # Determine condition from URL - ensure it's set
        if '/new/' in url.lower():
            data['condition'] = 'new'
        elif '/used/' in url.lower():
            data['condition'] = 'used'
        
        # Fallback strategies for condition if URL doesn't contain it
        if not data['condition']:
            # Look for condition in text
            condition_match = re.search(r'Condition\s*:?\s*(New|Used)', page_text, re.I)
            if condition_match:
                data['condition'] = condition_match.group(1).lower()
            # Check data attributes
            elif soup.find(attrs={'data-condition': True}):
                cond_elem = soup.find(attrs={'data-condition': True})
                data['condition'] = cond_elem.get('data-condition', '').lower()
            # Check for "New Vehicle" or "Used Vehicle"
            elif re.search(r'\bNew\s+Vehicle\b', page_text, re.I):
                data['condition'] = 'new'
            elif re.search(r'\bUsed\s+Vehicle\b', page_text, re.I):
                data['condition'] = 'used'
        
        # Enhanced brand extraction from title AND page text
        brands = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Chevy', 'GMC', 'Dodge', 'Ram',
                 'Nissan', 'Hyundai', 'Kia', 'Mazda', 'Subaru', 'Jeep', 'Acura',
                 'Cadillac', 'Buick', 'Lexus', 'Lincoln', 'Volkswagen', 'VW', 'Audi',
                 'BMW', 'Mercedes', 'Mercedes-Benz', 'Volvo', 'Mitsubishi', 'Infiniti']
        
        # Try title first
        title_lower = (data['title'] or '').lower()
        for brand in brands:
            if brand.lower() in title_lower:
                data['brand'] = 'Chevrolet' if brand == 'Chevy' else brand
                break
        
        # If brand not found in title, search page text
        if not data['brand']:
            for brand in brands:
                if re.search(r'\bMake\s*:?\s*' + re.escape(brand), page_text, re.I):
                    data['brand'] = 'Chevrolet' if brand == 'Chevy' else brand
                    break
        
        # If still not found, look for brand in meta tags or structured data
        if not data['brand']:
            for meta in soup.find_all('meta'):
                content = meta.get('content', '').lower()
                for brand in brands:
                    if brand.lower() in content:
                        data['brand'] = 'Chevrolet' if brand == 'Chevy' else brand
                        break
                if data['brand']:
                    break
        
        # Enhanced model and trim extraction with multiple strategies
        
        # Strategy 1: Parse from title
        if data['title']:
            remaining = data['title']
            # Remove year
            if data['year']:
                remaining = remaining.replace(data['year'], '').strip()
            # Remove brand
            if data['brand']:
                remaining = re.sub(r'\b' + re.escape(data['brand']) + r'\b', '', 
                                 remaining, flags=re.I).strip()
            
            # Clean up remaining text
            remaining = ' '.join(remaining.split())
            parts = remaining.split()
            
            if parts:
                # First part is the model
                data['model'] = parts[0]
                
                # Everything else is trim/sub-model
                if len(parts) > 1:
                    data['trim / sub-model'] = ' '.join(parts[1:])
        
        # Strategy 2: Look for model and trim in structured data
        if not data['model'] or not data['trim / sub-model']:
            # Check tables
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = self.extract_text_safe(cells[0]).lower()
                        value = self.extract_text_safe(cells[1])
                        
                        if not data['model'] and 'model' in label:
                            # Model might include trim, split it
                            model_parts = value.split()
                            if model_parts:
                                data['model'] = model_parts[0]
                                if len(model_parts) > 1 and not data['trim / sub-model']:
                                    data['trim / sub-model'] = ' '.join(model_parts[1:])
                        
                        if not data['trim / sub-model'] and ('trim' in label or 'sub-model' in label or 'submodel' in label):
                            data['trim / sub-model'] = value
            
            # Check definition lists
            if not data['model'] or not data['trim / sub-model']:
                for dl in soup.find_all('dl'):
                    dts = dl.find_all('dt')
                    dds = dl.find_all('dd')
                    for dt, dd in zip(dts, dds):
                        dt_text = self.extract_text_safe(dt).lower()
                        dd_text = self.extract_text_safe(dd)
                        
                        if not data['model'] and 'model' in dt_text:
                            model_parts = dd_text.split()
                            if model_parts:
                                data['model'] = model_parts[0]
                                if len(model_parts) > 1 and not data['trim / sub-model']:
                                    data['trim / sub-model'] = ' '.join(model_parts[1:])
                        
                        if not data['trim / sub-model'] and ('trim' in dt_text or 'sub' in dt_text):
                            data['trim / sub-model'] = dd_text
        
        # Strategy 3: Look in data attributes
        if not data['model']:
            model_elem = soup.find(attrs=lambda x: x and any('model' in str(k).lower() for k in x.keys()))
            if model_elem:
                for attr, value in model_elem.attrs.items():
                    if 'model' in attr.lower() and not 'sub' in attr.lower():
                        data['model'] = str(value)
                        break
        
        if not data['trim / sub-model']:
            trim_elem = soup.find(attrs=lambda x: x and any('trim' in str(k).lower() or 'submodel' in str(k).lower() for k in x.keys()))
            if trim_elem:
                for attr, value in trim_elem.attrs.items():
                    if 'trim' in attr.lower() or 'submodel' in attr.lower() or 'sub-model' in attr.lower():
                        data['trim / sub-model'] = str(value)
                        break
        
        # Strategy 4: Text patterns
        if not data['model']:
            model_match = re.search(r'Model\s*:?\s*([A-Z][\w\-]+)', page_text, re.I)
            if model_match:
                model_val = model_match.group(1).strip()
                # Split if it contains trim
                model_parts = model_val.split()
                data['model'] = model_parts[0]
                if len(model_parts) > 1 and not data['trim / sub-model']:
                    data['trim / sub-model'] = ' '.join(model_parts[1:])
        
        if not data['trim / sub-model']:
            trim_patterns = [
                r'Trim\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n)',
                r'Sub-?Model\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n)',
            ]
            for pattern in trim_patterns:
                match = re.search(pattern, page_text, re.I)
                if match:
                    data['trim / sub-model'] = match.group(1).strip()
                    break
        
        # Enhanced VIN extraction with validation
        vin_pattern = r'\b([A-HJ-NPR-Z0-9]{17})\b'
        vin_match = re.search(vin_pattern, page_text)
        if vin_match:
            potential_vin = vin_match.group(1).upper()
            # Validate VIN (no I, O, Q allowed, must be exactly 17 chars)
            if (len(potential_vin) == 17 and 
                potential_vin.isalnum() and 
                not any(char in potential_vin for char in ['I', 'O', 'Q'])):
                data['vin'] = potential_vin
        
        # Extract stock number
        stock_patterns = [
            r'Stock\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'Stk\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'Stock\s*Number\s*:?\s*([A-Z0-9-]+)',
        ]
        for pattern in stock_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                stock = match.group(1).strip()
                if len(stock) >= 3:
                    data['id / stock-#'] = stock
                    break
        
        # Enhanced mileage extraction with better validation and multiple strategies
        mileage_found = False
        
        # Strategy 1: Look for mileage in structured format (table, dl, divs)
        # Check tables first
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = self.extract_text_safe(cells[0]).lower()
                    if 'mileage' in label or 'odometer' in label or 'km' in label:
                        value_text = self.extract_text_safe(cells[1])
                        # Extract number from value
                        num_match = re.search(r'(\d{1,3}(?:[,\s]\d{3})*|\d+)', value_text)
                        if num_match:
                            try:
                                mileage_val = int(num_match.group(1).replace(',', '').replace(' ', ''))
                                if 0 <= mileage_val <= 500000:
                                    data['mileage'] = str(mileage_val)
                                    mileage_found = True
                                    break
                            except:
                                pass
            if mileage_found:
                break
        
        # Strategy 2: Definition lists
        if not mileage_found:
            for dl in soup.find_all('dl'):
                dts = dl.find_all('dt')
                dds = dl.find_all('dd')
                for dt, dd in zip(dts, dds):
                    dt_text = self.extract_text_safe(dt).lower()
                    if 'mileage' in dt_text or 'odometer' in dt_text or 'km' in dt_text:
                        dd_text = self.extract_text_safe(dd)
                        num_match = re.search(r'(\d{1,3}(?:[,\s]\d{3})*|\d+)', dd_text)
                        if num_match:
                            try:
                                mileage_val = int(num_match.group(1).replace(',', '').replace(' ', ''))
                                if 0 <= mileage_val <= 500000:
                                    data['mileage'] = str(mileage_val)
                                    mileage_found = True
                                    break
                            except:
                                pass
                if mileage_found:
                    break
        
        # Strategy 3: Data attributes
        if not mileage_found:
            for elem in soup.find_all(attrs=lambda x: x and any('mileage' in str(k).lower() or 'odometer' in str(k).lower() for k in x.keys())):
                for attr, value in elem.attrs.items():
                    if 'mileage' in attr.lower() or 'odometer' in attr.lower():
                        try:
                            val_str = str(value).replace(',', '').replace(' ', '')
                            mileage_val = int(re.sub(r'[^\d]', '', val_str))
                            if 0 <= mileage_val <= 500000:
                                data['mileage'] = str(mileage_val)
                                mileage_found = True
                                break
                        except:
                            pass
                if mileage_found:
                    break
        
        # Strategy 4: Text patterns (with context validation)
        if not mileage_found:
            mileage_patterns = [
                r'Mileage\s*:?\s*(\d{1,3}(?:[,\s]\d{3})*)\s*(?:km|kilometers?|miles?|mi)?',
                r'Odometer\s*:?\s*(\d{1,3}(?:[,\s]\d{3})*)\s*(?:km|kilometers?)?',
                r'(\d{1,3}(?:[,\s]\d{3})*)\s*(?:km|kilometers?)\b',
                r'(\d{1,3}(?:[,\s]\d{3})*)\s*(?:miles?|mi)\b',
            ]
            
            for pattern in mileage_patterns:
                for match in re.finditer(pattern, page_text, re.I):
                    try:
                        mileage_str = match.group(1).replace(',', '').replace(' ', '')
                        mileage_val = int(mileage_str)
                        
                        # Validate range
                        if 0 <= mileage_val <= 500000:
                            # Get context to avoid false positives
                            context_start = max(0, match.start() - 50)
                            context_end = min(len(page_text), match.end() + 50)
                            context = page_text[context_start:context_end].lower()
                            
                            # Skip if context suggests this is not vehicle mileage
                            if any(skip in context for skip in ['warranty', 'coverage', 'per year', 'annual', 'fuel economy', 'mpg', 'range']):
                                continue
                            
                            data['mileage'] = str(mileage_val)
                            mileage_found = True
                            break
                    except:
                        pass
                if mileage_found:
                    break
        
        # Strategy 5: Look in spec divs/sections
        if not mileage_found:
            spec_sections = soup.find_all(['div', 'section', 'span'], 
                                         class_=re.compile(r'spec|detail|mileage|odometer', re.I))
            for section in spec_sections:
                text = self.extract_text_safe(section)
                # Look for number + km/miles pattern
                num_match = re.search(r'\b(\d{1,3}(?:[,\s]\d{3})*)\s*(?:km|kilometers?|miles?|mi)\b', text, re.I)
                if num_match:
                    try:
                        mileage_val = int(num_match.group(1).replace(',', '').replace(' ', ''))
                        if 0 <= mileage_val <= 500000:
                            data['mileage'] = str(mileage_val)
                            mileage_found = True
                            break
                    except:
                        pass
        
        # If new vehicle and no mileage found, set to 0
        if not mileage_found and data['condition'] == 'new':
            data['mileage'] = '0'
        
        # Extract engine
        engine_patterns = [
            r'(\d\.\d+L?\s*(?:V\d+|I\d+|Hybrid|Turbo|EcoBoost))',
            r'Engine\s*:?\s*([^\n]{5,40})',
        ]
        for pattern in engine_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                engine = match.group(1).strip()
                if 3 <= len(engine) <= 50:
                    data['engine'] = engine
                    break
        
        # Enhanced color extraction with 8 comprehensive strategies
        
        # Strategy 1: Pattern matching in page text (more flexible)
        color_patterns = [
            r'Exterior\s*Colou?r\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n|Interior|Engine|Transmission|Drivetrain)',
            r'Ext\.?\s*Colou?r\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n|Interior)',
            r'Colou?r\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n|Interior|Engine)',
            r'Paint\s*Colou?r?\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n)',
            r'Body\s*Colou?r\s*:?\s*([A-Z][\w\s\-]+?)(?:\s*[\|,]|$|\n)',
        ]
        
        for pattern in color_patterns:
            match = re.search(pattern, page_text)
            if match:
                color = match.group(1).strip()
                # Remove trailing words that are not part of color
                color = re.sub(r'\s+(Interior|Transmission|Engine|Drivetrain|4WD|AWD|FWD).*$', '', color, flags=re.I)
                color = re.sub(r'\s+', ' ', color)  # Clean whitespace
                if 3 <= len(color) <= 40:
                    data['color'] = color
                    break
        
        # Strategy 2: Look in table rows (td/th)
        if not data['color']:
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = self.extract_text_safe(cells[0]).lower()
                        if 'color' in label or 'colour' in label or 'exterior' in label:
                            color = self.extract_text_safe(cells[1])
                            if 3 <= len(color) <= 40:
                                data['color'] = color
                                break
                if data['color']:
                    break
        
        # Strategy 3: HTML elements with color classes/IDs (improved filtering)
        if not data['color']:
            selectors = [
                soup.find_all(['div', 'span', 'p', 'li', 'td', 'dd'], class_=re.compile(r'(?:ext|exterior|vehicle).*color', re.I)),
                soup.find_all(['div', 'span', 'p', 'li', 'td', 'dd'], class_=re.compile(r'color.*(?:ext|exterior)', re.I)),
                soup.find_all(['div', 'span', 'p', 'li', 'td', 'dd'], id=re.compile(r'color|colour', re.I))
            ]
            
            for elem_list in selectors:
                for elem in elem_list:
                    text = self.extract_text_safe(elem)
                    
                    # Skip if too long or contains excluded keywords
                    if len(text) > 60:
                        continue
                    
                    # Remove label words
                    text = re.sub(r'^(Exterior\s*)?Colou?r\s*:?\s*', '', text, flags=re.I)
                    text = text.strip()
                    
                    # Extract color
                    if text:
                        # Exclude common non-color words
                        excluded = ['new', 'used', 'toyota', 'honda', 'ford', 'chevrolet', 'gmc',
                                   'stock', 'price', 'view', 'details', 'exterior', 'interior', 
                                   'color', 'colour', 'vehicle', 'mileage', 'engine', 'transmission',
                                   'click', 'more', 'info', 'see', 'all']
                        
                        if text.lower() not in excluded and 3 <= len(text) <= 40:
                            # Validate it looks like a color (starts with capital)
                            if text[0].isupper():
                                data['color'] = text
                                break
                if data['color']:
                    break
        
        # Strategy 4: Definition lists (dt/dd)
        if not data['color']:
            for dl in soup.find_all('dl'):
                dts = dl.find_all('dt')
                dds = dl.find_all('dd')
                for dt, dd in zip(dts, dds):
                    dt_text = self.extract_text_safe(dt).lower()
                    if 'color' in dt_text or 'colour' in dt_text or 'exterior' in dt_text:
                        color = self.extract_text_safe(dd)
                        if 3 <= len(color) <= 40:
                            data['color'] = color
                            break
                if data['color']:
                    break
        
        # Strategy 5: Data attributes
        if not data['color']:
            for elem in soup.find_all(attrs=lambda x: x and any('color' in str(k).lower() for k in x.keys())):
                for attr, value in elem.attrs.items():
                    if 'color' in attr.lower() or 'colour' in attr.lower():
                        val = str(value).strip()
                        if 3 <= len(val) <= 40 and val[0].isupper():
                            data['color'] = val
                            break
                if data['color']:
                    break
        
        # Strategy 6: JSON-LD structured data
        if not data['color']:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict):
                        for key in ['color', 'colour', 'exteriorColor', 'vehicleColor', 'bodyColor']:
                            if key in json_data and json_data[key]:
                                data['color'] = str(json_data[key])
                                break
                except:
                    pass
                if data['color']:
                    break
        
        # Strategy 7: Meta tags
        if not data['color']:
            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if 'color' in prop.lower():
                    val = meta.get('content', '').strip()
                    if 3 <= len(val) <= 40:
                        data['color'] = val
                        break
        
        # Strategy 8: Expanded common color name matching in spec sections
        if not data['color']:
            common_colors = [
                # Basic colors
                'White', 'Black', 'Silver', 'Gray', 'Grey', 'Red', 'Blue', 'Green',
                'Yellow', 'Orange', 'Brown', 'Beige', 'Tan', 'Gold', 'Bronze', 
                'Burgundy', 'Maroon', 'Navy', 'Purple', 'Charcoal', 'Graphite',
                # Extended colors
                'Pearl White', 'Jet Black', 'Midnight Black', 'Super White', 
                'Magnetic Gray', 'Magnetic Grey', 'Celestial Silver', 'Ruby Red', 
                'Blueprint', 'Supersonic Red', 'Wind Chill Pearl', 'Lunar Rock', 
                'Ice Cap', 'Blizzard Pearl', 'Cavalry Blue', 'Army Green',
                'Cement', 'Barcelona Red', 'Voodoo Blue', 'Quicksand', 
                'Predawn Gray', 'Midnight Black Metallic', 'Supersonic Silver',
                'Magnetic Gray Metallic', 'Blueprint Pearl', 'Ice Edge',
                # Toyota specific
                'Super White', 'Blizzard Pearl', 'Wind Chill Pearl', 'Celestial Silver Metallic',
                'Magnetic Gray Metallic', 'Predawn Gray Mica', 'Midnight Black Metallic',
                'Ruby Flare Pearl', 'Supersonic Red', 'Blue Crush Metallic',
                'Cavalry Blue', 'Lunar Rock', 'Ice Cap', 'Cement',
                # Common multi-word colors
                'Oxford White', 'Agate Black', 'Iconic Silver', 'Rapid Red',
                'Carbonized Gray', 'Antimatter Blue', 'Atlas Blue', 'Race Red',
                'Velocity Blue', 'Shadow Black', 'Stone Gray', 'Deep Crystal Blue',
                'Crystal Black', 'Modern Steel', 'Obsidian Blue', 'Sonic Gray'
            ]
            
            # Sort by length (longest first) to match multi-word colors first
            common_colors.sort(key=len, reverse=True)
            
            # Search in spec sections and entire page
            search_areas = soup.find_all(['div', 'section', 'table', 'dl', 'ul'], 
                                        class_=re.compile(r'spec|detail|info|feature|attribute', re.I))
            search_areas.append(soup)  # Also search entire page
            
            for section in search_areas:
                section_text = section.get_text()
                for color_name in common_colors:
                    # Use word boundary to avoid partial matches
                    if re.search(r'\b' + re.escape(color_name) + r'\b', section_text, re.I):
                        data['color'] = color_name
                        break
                if data['color']:
                    break
        
        # Extract body style
        body_styles = ['Sedan', 'SUV', 'Truck', 'Coupe', 'Hatchback', 'Wagon',
                      'Van', 'Convertible', 'Crossover', 'Pickup']
        for style in body_styles:
            if re.search(r'\b' + style + r'\b', page_text, re.I):
                data['body style'] = style
                break
        
        # Extract prices (raw numbers, will add $ later)
        price_raw = self.extract_price(soup)
        msrp_raw = self.extract_msrp(soup)
        
        # Add $ prefix to prices
        if price_raw:
            data['price'] = f"${price_raw}"
        if msrp_raw:
            data['vehicle MSRP'] = f"${msrp_raw}"
        
        # Validate price relationship
        if price_raw and msrp_raw:
            try:
                if int(msrp_raw) < int(price_raw):
                    # Swap them
                    data['price'] = f"${msrp_raw}"
                    data['vehicle MSRP'] = f"${price_raw}"
            except ValueError:
                pass
        
        # All-in price typically same as price
        data['vehicle all in price'] = data['price']
        
        # Extract image
        data['image link'] = self.extract_image(soup)
        
        # Extract vehicle options/features
        options = []
        
        # Strategy 1: Look for feature/option lists (ul, ol)
        for ul in soup.find_all(['ul', 'ol']):
            parent_class = ' '.join(ul.get('class', [])).lower()
            parent_id = (ul.get('id') or '').lower()
            
            # Check if list contains features/options
            if any(kw in parent_class or kw in parent_id 
                   for kw in ['feature', 'option', 'equipment', 'spec', 'highlight', 'amenity']):
                items = ul.find_all('li')
                for item in items:
                    opt_text = self.extract_text_safe(item)
                    if opt_text and 3 < len(opt_text) < 100:
                        options.append(opt_text)
        
        # Strategy 2: Look for feature divs/sections
        for elem in soup.find_all(['div', 'section', 'span', 'p'], 
                                   class_=re.compile(r'feature|option|equipment|package', re.I)):
            text = self.extract_text_safe(elem)
            if text and 5 < len(text) < 100:
                if text not in options:  # Avoid duplicates
                    options.append(text)
        
        # Strategy 3: Search for "Features:" or "Options:" in text
        feature_patterns = [
            r'(?:Standard\s+)?Features?\s*:?\s*([^\n]{20,500})',
            r'(?:Standard\s+)?Equipment\s*:?\s*([^\n]{20,500})',
            r'Options?\s*Included?\s*:?\s*([^\n]{20,500})',
            r'Packages?\s*:?\s*([^\n]{20,500})',
        ]
        
        for pattern in feature_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                features_text = match.group(1)
                # Split by common delimiters
                items = re.split(r'[,;•·]', features_text)
                for item in items:
                    clean = item.strip()
                    if clean and 3 < len(clean) < 100:
                        options.append(clean)
        
        # Strategy 4: Look for definition lists (dt/dd)
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                dt_text = self.extract_text_safe(dt)
                dd_text = self.extract_text_safe(dd)
                if dt_text and dd_text and 3 < len(dt_text) < 50:
                    # Combine as "Feature: Value"
                    option = f"{dt_text}: {dd_text[:50]}"
                    options.append(option)
        
        # Clean and deduplicate options
        unique_options = []
        seen = set()
        for opt in options:
            opt_clean = opt.strip()
            opt_lower = opt_clean.lower()
            
            if not opt_lower or opt_lower in seen:
                continue
            
            # Filter out unwanted text
            skip_keywords = ['click', 'more info', 'view', 'details', 'features', 'options',
                            'read more', 'see all', 'show more', 'contact', 'call', 'email']
            if any(skip in opt_lower for skip in skip_keywords):
                continue
            
            # Filter out very generic options
            if opt_lower in ['yes', 'no', 'n/a', 'tbd', 'standard', 'available']:
                continue
            
            if 3 < len(opt_clean) < 100:
                unique_options.append(opt_clean)
                seen.add(opt_lower)
        
        # Store up to 30 options (separated by commas)
        if unique_options:
            data['vehicle option'] = ', '.join(unique_options[:30])
        
        # Extract description
        desc_elem = (soup.find('meta', {'name': 'description'}) or 
                    soup.find('meta', {'property': 'og:description'}))
        if desc_elem:
            desc = desc_elem.get('content', '')
            if len(desc) > 20:
                data['description'] = desc[:500]
        
        # Check for CPO
        if re.search(r'\bcertified\b.*\bpre-owned\b', page_text, re.I):
            data['certified pre-owned'] = 'yes'
        
        # Log summary
        logger.info(f"  ✓ {data['year']} {data['brand']} {data['model']} {data['trim / sub-model']}")
        logger.info(f"  Stock: {data['id / stock-#']} | VIN: {data['vin']}")
        logger.info(f"  Price: {data['price']} | MSRP: {data['vehicle MSRP']}")
        logger.info(f"  Condition: {data['condition']} | Mileage: {data['mileage']} | Color: {data['color']}")
        
        return data
    
    def scrape_inventory_pages(self, urls):
        """Scrape all inventory pages"""
        logger.info(f"\n{'='*100}")
        logger.info("STEP 1: COLLECTING VEHICLE LINKS")
        logger.info(f"{'='*100}\n")
        
        all_links = set()
        
        for url in urls:
            logger.info(f"Scanning: {url}")
            soup = self.get_page(url)
            if soup:
                links = self.extract_vehicle_links(soup)
                all_links.update(links)
                logger.info(f"  → Found {len(links)} vehicles\n")
            time.sleep(1)
        
        logger.info(f"{'='*100}")
        logger.info(f"Total unique vehicles: {len(all_links)}")
        logger.info(f"{'='*100}")
        
        # Step 2: Scrape each vehicle
        logger.info(f"\nSTEP 2: SCRAPING VEHICLE DETAILS")
        logger.info(f"{'='*100}\n")
        
        all_vehicles = []
        for i, url in enumerate(sorted(all_links), 1):
            logger.info(f"Progress: {i}/{len(all_links)}")
            vehicle = self.scrape_vehicle(url)
            if vehicle:
                all_vehicles.append(vehicle)
            time.sleep(1.5)
        
        logger.info(f"\n{'='*100}")
        logger.info(f"COMPLETE: Scraped {len(all_vehicles)} vehicles")
        logger.info(f"{'='*100}\n")
        
        return all_vehicles
