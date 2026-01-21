import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalVehicleScraper:
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_page(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_vehicle_links(self, soup):
        links = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/inventory/' in href and not any(x in href for x in ['?page=', 'new/', 'used/']):
                if len(href.split('/')) > 4:
                    full_url = urljoin(self.base_url, href)
                    if '?page=' not in full_url:
                        links.add(full_url)
        return list(links)
    
    def clean_text(self, text):
        if not text:
            return ""
        return ' '.join(text.strip().split())
    
    def extract_price(self, text):
        if not text:
            return ""
        text = text.replace('$', '').replace(',', '').strip()
        numbers = re.findall(r'\d+', text)
        if numbers:
            prices = [int(n) for n in numbers if len(n) >= 4]
            if prices:
                return str(max(prices))
        return ""
    
    def extract_mileage(self, text):
        if not text:
            return ""
        text = text.replace(',', '')
        match = re.search(r'(\d+)\s*(?:km|miles?)', text, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def extract_year(self, text):
        if not text:
            return ""
        match = re.search(r'\b(19\d{2}|20[0-3]\d)\b', text)
        return match.group(1) if match else ""
    
    def parse_vehicle_title(self, title):
        result = {'year': '', 'make': '', 'model': '', 'trim': ''}
        if not title:
            return result
        
        result['year'] = self.extract_year(title)
        title_clean = re.sub(r'\b(19\d{2}|20[0-3]\d)\b', '', title).strip()
        words = title_clean.split()
        
        if not words:
            return result
        
        makes = {'Toyota', 'Lexus', 'Honda', 'Acura', 'Nissan', 'Ford', 'Chevrolet', 
                'GMC', 'Dodge', 'Ram', 'Jeep', 'Chrysler', 'Mazda', 'Subaru', 'Hyundai',
                'Kia', 'Volkswagen', 'Audi', 'BMW', 'Mercedes', 'Land Rover', 'Range Rover'}
        
        make_idx = -1
        for i, word in enumerate(words):
            if word in makes:
                result['make'] = word
                make_idx = i
                break
        
        if make_idx != -1 and make_idx + 1 < len(words):
            remaining = words[make_idx + 1:]
            trims = {'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD',
                    'LX', 'EX', 'Touring', 'Sport', 'Hybrid', 'AWD', 'FWD', '4WD',
                    'North', 'Progressiv', 'Comfortline', 'Dynamic', 'HSE'}
            
            trim_idx = len(remaining)
            for i, word in enumerate(remaining):
                if word in trims:
                    trim_idx = i
                    break
            
            result['model'] = ' '.join(remaining[:trim_idx]) if trim_idx > 0 else remaining[0]
            result['trim'] = ' '.join(remaining[trim_idx:]) if trim_idx < len(remaining) else ''
        
        return result
    
    def scrape_vehicle_detail(self, url):
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping: {url}")
        soup = self.get_page(url)
        
        if not soup:
            return None
        
        data = {
            'title': '', 'id / stock-#': '', 'price': '', 'condition': '',
            'feed label': '', 'body style': '', 'brand': '', 'certified pre-owned': '',
            'color': '', 'description': '', 'engine': '', 'image link': '',
            'link': url, 'mileage': '', 'model': '', 'trim / sub-model': '',
            'vehicle MSRP': '', 'vehicle all in price': '', 'vehicle option': '',
            'vin': '', 'year': ''
        }
        
        # Title
        h1 = soup.find('h1')
        if h1:
            data['title'] = self.clean_text(h1.get_text())
            logger.info(f"Title: {data['title']}")
        
        # Parse title
        parsed = self.parse_vehicle_title(data['title'])
        data['year'] = parsed['year']
        data['brand'] = parsed['make']
        data['model'] = parsed['model']
        data['trim / sub-model'] = parsed['trim']
        
        # Condition from URL
        if '/new/' in url:
            data['condition'] = 'new'
        elif '/used/' in url:
            data['condition'] = 'used'
        
        # Stock number
        for elem in soup.find_all(['span', 'div', 'p']):
            text = elem.get_text()
            if 'stock' in text.lower() and len(text) < 100:
                match = re.search(r'(?:Stock|#)\s*:?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
                if match:
                    data['id / stock-#'] = match.group(1)
                    break
        
        # VIN
        for elem in soup.find_all(['span', 'div', 'p']):
            text = elem.get_text()
            if 'vin' in text.lower():
                match = re.search(r'([A-HJ-NPR-Z0-9]{17})', text, re.IGNORECASE)
                if match:
                    data['vin'] = match.group(1).upper()
                    break
        
        # Prices
        price_elements = []
        for elem in soup.find_all(['span', 'div', 'p', 'strong']):
            text = elem.get_text()
            if '$' in text:
                price_elements.append(self.clean_text(text))
        
        logger.info(f"Found {len(price_elements)} price elements")
        for pe in price_elements[:5]:
            logger.info(f"  Price elem: {pe[:80]}")
        
        # Selling price
        for pe in price_elements:
            if 'msrp' not in pe.lower() and 'retail' not in pe.lower():
                price = self.extract_price(pe)
                if price and int(price) > 5000:
                    data['price'] = price
                    logger.info(f"Price: ${price}")
                    break
        
        # MSRP
        for pe in price_elements:
            if 'msrp' in pe.lower() or 'retail' in pe.lower():
                msrp = self.extract_price(pe)
                if msrp and int(msrp) > 5000:
                    data['vehicle MSRP'] = msrp
                    logger.info(f"MSRP: ${msrp}")
                    break
        
        # Mileage
        for elem in soup.find_all(['span', 'div', 'p']):
            text = elem.get_text()
            if 'km' in text.lower() and len(text) < 100:
                mileage = self.extract_mileage(text)
                if mileage:
                    data['mileage'] = mileage
                    break
        
        # Color
        for elem in soup.find_all(['span', 'div', 'p', 'dd']):
            text = elem.get_text()
            if 'exterior' in text.lower() or 'color' in text.lower():
                if len(text) < 100:
                    color = self.clean_text(text)
                    color = re.sub(r'(?i)(exterior|color)[:\s]*', '', color)
                    if color and len(color) < 50:
                        data['color'] = color
                        break
        
        # Engine
        for elem in soup.find_all(['span', 'div', 'p', 'dd']):
            text = elem.get_text()
            if 'engine' in text.lower() and len(text) < 200:
                engine = self.clean_text(text)
                engine = re.sub(r'(?i)engine[:\s]*', '', engine)
                if len(engine) > 3:
                    data['engine'] = engine
                    break
        
        # Body style - infer from model
        model_lower = data['model'].lower()
        if any(x in model_lower for x in ['tundra', 'tacoma', 'f-150']):
            data['body style'] = 'Pickup Truck'
        elif any(x in model_lower for x in ['rav4', 'highlander', 'escape', 'cr-v', '4runner']):
            data['body style'] = 'SUV'
        elif any(x in model_lower for x in ['camry', 'corolla', 'accord', 'civic']):
            data['body style'] = 'Sedan'
        elif any(x in model_lower for x in ['sienna', 'pacifica']):
            data['body style'] = 'Minivan'
        
        # Description
        for elem in soup.find_all(['div', 'p']):
            classes = ' '.join(elem.get('class', []))
            if 'description' in classes.lower() or 'overview' in classes.lower():
                desc = self.clean_text(elem.get_text())
                if len(desc) > 100:
                    data['description'] = desc[:2000]
                    break
        
        # Options
        options = []
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                opt = self.clean_text(li.get_text())
                if opt and len(opt) < 100:
                    options.append(opt)
        
        if options:
            data['vehicle option'] = '; '.join(options[:50])
        
        # CPO
        page_text = soup.get_text().lower()
        if 'certified pre-owned' in page_text:
            data['certified pre-owned'] = 'yes'
        
        # Image
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and 'logo' not in src.lower():
                data['image link'] = urljoin(self.base_url, src)
                break
        
        logger.info(f"Stock: {data['id / stock-#']}, Price: {data['price']}, Condition: {data['condition']}")
        logger.info(f"{'='*80}")
        
        return data
    
    def scrape_inventory_pages(self, urls):
        all_vehicles = []
        all_links = set()
        
        logger.info("Collecting vehicle links...")
        for url in urls:
            logger.info(f"Scanning: {url}")
            soup = self.get_page(url)
            if soup:
                links = self.extract_vehicle_links(soup)
                all_links.update(links)
                logger.info(f"Found {len(links)} vehicles")
            time.sleep(1)
        
        logger.info(f"\nTotal unique vehicles: {len(all_links)}")
        
        logger.info("\nScraping vehicle pages...")
        for i, vdp_url in enumerate(sorted(all_links), 1):
            logger.info(f"\nProgress: {i}/{len(all_links)}")
            vehicle = self.scrape_vehicle_detail(vdp_url)
            if vehicle:
                all_vehicles.append(vehicle)
            time.sleep(1)
        
        return all_vehicles
