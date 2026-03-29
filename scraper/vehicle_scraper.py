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
                    
                    # Validate: URL should have content after /inventory/
                    if clean_url.rstrip('/').endswith('/inventory'):
                        continue  # Skip invalid URLs
                    
                    # Check that there's actually a path after /inventory/
                    parts = clean_url.rstrip('/').split('/inventory/')
                    if len(parts) > 1 and parts[1]:  # Has content after /inventory/
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
            except Exception:
                pass
        
        # Strategy 2: Meta tags
        for meta in soup.find_all('meta'):
            if meta.get('property') == 'product:price:amount':
                content = meta.get('content', '')
                if content:
                    try:
                        return str(int(float(content)))
                    except Exception:
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
                    except Exception:
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
            except Exception:
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
                    except Exception:
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
                except Exception:
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
            except Exception:
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
                        except Exception:
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
                except Exception:
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
        
        # Extract VIN
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
        
        # Extract mileage
        mileage_found = False
        
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
                            except Exception:
                                pass
            if mileage_found:
                break
        
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
        
        # Extract color
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
