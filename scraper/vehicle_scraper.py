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
        """Extract primary vehicle image URL"""
        # Try JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'image' in data:
                    img = data['image']
                    if isinstance(img, list):
                        img = img[0] if img else ''
                    if img:
                        return urljoin(self.base_url, img)
            except:
                pass
        
        # Try Open Graph
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            return urljoin(self.base_url, og_img['content'])
        
        # Find vehicle images
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            alt = img.get('alt', '').lower()
            if src and 'vehicle' in alt:
                return urljoin(self.base_url, src)
        
        # Fallback to first meaningful image
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            if src and not any(x in src.lower() for x in ['logo', 'icon']):
                return urljoin(self.base_url, src)
        
        return ''
    
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
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', data['title'] or page_text)
        if year_match:
            data['year'] = year_match.group(1)
        
        # Determine condition from URL
        if '/new/' in url:
            data['condition'] = 'new'
        elif '/used/' in url:
            data['condition'] = 'used'
        
        # Extract brand from title
        brands = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'GMC', 'Dodge', 'Ram',
                 'Nissan', 'Hyundai', 'Kia', 'Mazda', 'Subaru', 'Jeep', 'Acura',
                 'Cadillac', 'Buick', 'Lexus']
        title_lower = (data['title'] or '').lower()
        for brand in brands:
            if brand.lower() in title_lower:
                data['brand'] = brand
                break
        
        # Parse model and trim from title
        if data['title']:
            remaining = data['title']
            # Remove year and brand
            if data['year']:
                remaining = remaining.replace(data['year'], '').strip()
            if data['brand']:
                remaining = re.sub(r'\b' + re.escape(data['brand']) + r'\b', '', 
                                 remaining, flags=re.I).strip()
            
            parts = remaining.split()
            if parts:
                data['model'] = parts[0]
                if len(parts) > 1:
                    data['trim / sub-model'] = ' '.join(parts[1:])
        
        # Extract VIN
        vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', page_text)
        if vin_match:
            vin = vin_match.group(1).upper()
            if len(vin) == 17:
                data['vin'] = vin
        
        # Extract stock number
        stock_patterns = [
            r'Stock\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'Stk\s*#?\s*:?\s*([A-Z0-9-]+)',
        ]
        for pattern in stock_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                stock = match.group(1).strip()
                if len(stock) >= 3:
                    data['id / stock-#'] = stock
                    break
        
        # Extract mileage
        mileage_patterns = [
            r'([\d,]+)\s*km',
            r'Mileage\s*:?\s*([\d,]+)',
        ]
        for pattern in mileage_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                try:
                    mileage = int(match.group(1).replace(',', ''))
                    if 0 <= mileage <= 500000:
                        data['mileage'] = str(mileage)
                        break
                except:
                    pass
        
        # Extract engine
        engine_patterns = [
            r'(\d\.\d+L?\s*(?:V\d+|I\d+|Hybrid|Turbo))',
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
        color_match = re.search(r'(?:Exterior\s*)?Colou?r\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 
                               page_text)
        if color_match:
            color = color_match.group(1).strip()
            if 3 <= len(color) <= 30:
                data['color'] = color
        
        # Extract body style
        body_styles = ['Sedan', 'SUV', 'Truck', 'Coupe', 'Hatchback', 'Wagon',
                      'Van', 'Convertible', 'Crossover', 'Pickup']
        for style in body_styles:
            if re.search(r'\b' + style + r'\b', page_text, re.I):
                data['body style'] = style
                break
        
        # Extract prices
        data['price'] = self.extract_price(soup)
        data['vehicle MSRP'] = self.extract_msrp(soup)
        
        # Validate price relationship
        if data['price'] and data['vehicle MSRP']:
            try:
                if int(data['vehicle MSRP']) < int(data['price']):
                    data['price'], data['vehicle MSRP'] = data['vehicle MSRP'], data['price']
            except:
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
        logger.info(f"  Price: ${data['price']} | MSRP: ${data['vehicle MSRP']}")
        logger.info(f"  Condition: {data['condition']} | Mileage: {data['mileage']}")
        
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
