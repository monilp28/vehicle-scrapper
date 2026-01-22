import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class VehicleScraper:
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.debug_mode = True
        self.debug_count = 0
    
    def get_page(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def save_debug_html(self, soup, filename):
        """Save HTML for debugging"""
        if self.debug_mode and self.debug_count < 3:
            try:
                os.makedirs('debug_output', exist_ok=True)
                with open(f'debug_output/{filename}', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                logger.info(f"  💾 Saved HTML to debug_output/{filename}")
                self.debug_count += 1
            except:
                pass
    
    def extract_links(self, soup):
        """Extract vehicle links and save debug info"""
        self.save_debug_html(soup, 'inventory_page.html')
        
        links = set()
        all_hrefs = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            all_hrefs.append(href)
            
            if '/inventory/' in href:
                full_url = urljoin(self.base_url, href)
                if not any(full_url.endswith(x) for x in ['/new/', '/used/', '/new', '/used']):
                    if '?page=' not in full_url:
                        links.add(full_url)
        
        # Debug output
        logger.info(f"  DEBUG: Found {len(all_hrefs)} total links")
        logger.info(f"  DEBUG: {len([h for h in all_hrefs if '/inventory/' in h])} contain /inventory/")
        logger.info(f"  DEBUG: {len(links)} vehicle pages identified")
        
        if len(links) == 0:
            logger.info(f"  DEBUG: Sample links from page:")
            for href in all_hrefs[:15]:
                logger.info(f"    {href}")
        
        return list(links)
    
    def scrape_vehicle(self, url):
        logger.info(f"\n{'='*120}")
        logger.info(f"SCRAPING: {url}")
        
        soup = self.get_page(url)
        if not soup:
            return None
        
        # Save first 3 vehicle pages for debugging
        self.save_debug_html(soup, f'vehicle_page_{self.debug_count + 1}.html')
        
        data = {
            'title': '', 'id / stock-#': '', 'price': '', 'condition': '',
            'feed label': '', 'body style': '', 'brand': '', 'certified pre-owned': '',
            'color': '', 'description': '', 'engine': '', 'image link': '',
            'link': url, 'mileage': '', 'model': '', 'trim / sub-model': '',
            'vehicle MSRP': '', 'vehicle all in price': '', 'vehicle option': '',
            'vin': '', 'year': ''
        }
        
        page_text = soup.get_text()
        
        # Extract title
        h1 = soup.find('h1')
        if h1:
            data['title'] = ' '.join(h1.get_text().strip().split())
            logger.info(f"TITLE: {data['title']}")
        
        # Parse basic info from title
        if data['title']:
            year_match = re.search(r'\b(20\d{2})\b', data['title'])
            if year_match:
                data['year'] = year_match.group(1)
            
            title_lower = data['title'].lower()
            if 'toyota' in title_lower:
                data['brand'] = 'Toyota'
            
            # Simple model extraction
            parts = data['title'].split()
            if len(parts) > 2:
                data['model'] = parts[2] if len(parts) > 2 else ''
                data['trim / sub-model'] = ' '.join(parts[3:]) if len(parts) > 3 else ''
        
        # Condition from URL
        if '/new/' in url:
            data['condition'] = 'new'
        elif '/used/' in url:
            data['condition'] = 'used'
        
        # Find ALL text containing prices
        logger.info(f"\nPRICE DEBUGGING:")
        logger.info(f"  Looking for all $ signs on page...")
        
        price_texts = []
        for elem in soup.find_all(text=re.compile(r'\$')):
            parent = elem.parent
            text = ' '.join(parent.get_text().strip().split())
            if text and len(text) < 200:
                price_texts.append(text)
        
        logger.info(f"  Found {len(price_texts)} elements with $")
        for i, pt in enumerate(price_texts[:20], 1):
            logger.info(f"    {i}. {pt}")
        
        # Try to extract price
        for pt in price_texts:
            if 'msrp' not in pt.lower() and '$' in pt:
                nums = re.findall(r'\$?\s*([\d,]+)', pt.replace(',', ''))
                for num in nums:
                    if len(num) >= 5:
                        data['price'] = num
                        logger.info(f"\n  ✓ SELECTED PRICE: ${num} from: {pt}")
                        break
                if data['price']:
                    break
        
        if not data['price']:
            logger.info(f"  ⚠️ NO PRICE FOUND!")
        
        # Simple text searches for other fields
        # Stock
        stock_match = re.search(r'(?:Stock|Stk)\s*#?\s*:?\s*([A-Z0-9-]+)', page_text, re.I)
        if stock_match:
            data['id / stock-#'] = stock_match.group(1)
        
        # VIN  
        vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', page_text)
        if vin_match:
            data['vin'] = vin_match.group(1).upper()
        
        # Mileage
        km_match = re.search(r'([\d,]+)\s*km', page_text, re.I)
        if km_match:
            data['mileage'] = km_match.group(1).replace(',', '')
        
        # Summary
        logger.info(f"\nSUMMARY:")
        logger.info(f"  Title: {data['title']}")
        logger.info(f"  Year/Make/Model: {data['year']} {data['brand']} {data['model']} {data['trim / sub-model']}")
        logger.info(f"  Stock: {data['id / stock-#']} | VIN: {data['vin']}")
        logger.info(f"  PRICE: ${data['price']}")
        logger.info(f"  Condition: {data['condition']}")
        logger.info(f"  Mileage: {data['mileage']}")
        logger.info(f"{'='*120}\n")
        
        return data
    
    def scrape_inventory_pages(self, urls):
        all_vehicles = []
        all_links = set()
        
        logger.info(f"\n{'='*120}")
        logger.info(f"COLLECTING VEHICLE LINKS")
        logger.info(f"{'='*120}\n")
        
        for url in urls:
            logger.info(f"Scanning: {url}")
            soup = self.get_page(url)
            if soup:
                links = self.extract_links(soup)
                all_links.update(links)
                logger.info(f"  → Found {len(links)} vehicles\n")
            time.sleep(1)
        
        logger.info(f"{'='*120}")
        logger.info(f"TOTAL VEHICLES: {len(all_links)}")
        logger.info(f"{'='*120}")
        
        if self.debug_mode:
            logger.info(f"\n📁 DEBUG FILES SAVED TO: debug_output/")
            logger.info(f"   - inventory_page.html (listing page)")
            logger.info(f"   - vehicle_page_1.html, vehicle_page_2.html, etc.")
            logger.info(f"\n⚠️ Please share these HTML files or the price debugging output!")
            logger.info(f"{'='*120}\n")
        
        for i, url in enumerate(sorted(all_links), 1):
            logger.info(f"VEHICLE {i}/{len(all_links)}")
            vehicle = self.scrape_vehicle(url)
            if vehicle:
                all_vehicles.append(vehicle)
            time.sleep(1)
        
        return all_vehicles
