import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalVehicleScraper:
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_page(self, url):
        """Fetch page content with error handling"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_vehicle_links(self, soup):
        """Extract all vehicle detail page links from inventory page"""
        links = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            
            if href and (
                ('/inventory/' in href and not any(x in href for x in ['?page=', 'new/', 'used/', 'new', 'used']) and len(href.split('/')) > 4) or
                ('/vehicles/' in href) or
                ('/vdp/' in href) or
                re.search(r'/\d{4}-[\w-]+', href)
            ):
                full_url = urljoin(self.base_url, href)
                if not re.search(r'\?(page|sort|filter)=', full_url):
                    links.add(full_url)
        
        return list(links)
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        cleaned = ' '.join(text.strip().split())
        return cleaned
    
    def extract_price(self, text):
        """Extract price from text - handles various formats"""
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
        """Extract mileage from text"""
        if not text:
            return ""
        text = text.replace(',', '')
        mileage_match = re.search(r'(\d+)\s*(?:km|miles?|KM|Km)', text, re.IGNORECASE)
        if mileage_match:
            return mileage_match.group(1)
        return ""
    
    def extract_year(self, text):
        """Extract year from text"""
        if not text:
            return ""
        year_match = re.search(r'\b(19\d{2}|20[0-3]\d)\b', text)
        return year_match.group(1) if year_match else ""
    
    def parse_vehicle_title(self, title):
        """Parse vehicle title to extract year, make, model, and trim"""
        result = {'year': '', 'make': '', 'model': '', 'trim': ''}
        
        if not title:
            return result
        
        result['year'] = self.extract_year(title)
        title_without_year = re.sub(r'\b(19\d{2}|20[0-3]\d)\b', '', title).strip()
        words = title_without_year.split()
        
        if not words:
            return result
        
        all_makes = {
            'Toyota', 'Lexus', 'Honda', 'Acura', 'Nissan', 'Infiniti', 'Mazda', 
            'Subaru', 'Mitsubishi', 'Suzuki', 'Isuzu',
            'Ford', 'Chevrolet', 'Chevy', 'GMC', 'Buick', 'Cadillac', 'Dodge', 
            'Ram', 'Jeep', 'Chrysler', 'Lincoln', 'Tesla',
            'BMW', 'Mercedes-Benz', 'Mercedes', 'Audi', 'Volkswagen', 'VW', 
            'Porsche', 'Volvo', 'Land Rover', 'Land', 'Range Rover', 'Range', 'Jaguar', 'MINI',
            'Hyundai', 'Kia', 'Genesis', 'Scion', 'Fiat', 'Alfa Romeo', 'Maserati'
        }
        
        make_index = -1
        for i, word in enumerate(words):
            for make in all_makes:
                if word.lower() == make.lower():
                    if make == 'Land' and i + 1 < len(words) and words[i + 1].lower() == 'rover':
                        result['make'] = 'Land Rover'
                        make_index = i + 1
                    elif make == 'Range' and i + 1 < len(words) and words[i + 1].lower() == 'rover':
                        result['make'] = 'Range Rover'
                        make_index = i + 1
                    elif make == 'Alfa' and i + 1 < len(words) and words[i + 1].lower() == 'romeo':
                        result['make'] = 'Alfa Romeo'
                        make_index = i + 1
                    else:
                        result['make'] = make if make != 'Chevy' else 'Chevrolet'
                        make_index = i
                    break
            if make_index != -1:
                break
        
        if make_index != -1 and make_index + 1 < len(words):
            remaining_words = words[make_index + 1:]
            
            trim_indicators = {
                'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD', 
                'Nightshade', 'Pro', 'Trail', 'Off-Road', 'Adventure', 'Premium',
                'GR', 'Sport', 'Upgrade', 'Technology', 'Luxury',
                'LX', 'EX', 'EX-L', 'Touring', 'Type R', 'Si', 'A-Spec', 'Tech', 'Elite', 'Advance',
                'S', 'SV', 'SL', 'SR', 'Nismo', 'Pro-4X', 'Luxe', 'Essential', 'Midnight', 'Edition', 'Reserve',
                'GX', 'GS', 'GT', 'Signature', 'Carbon', 'Preferred',
                'Base', 'Wilderness', 'XT', 'WRX', 'STI', 'Outback', 'Forester', 'Onyx',
                'LS', 'LT', 'LTZ', 'Premier', 'High Country', 'RST', 'RS', 'SS',
                'ZL1', 'Z71', 'AT4', 'Denali', 'SLT', 'SLE', 'Avenir', 'Essence',
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Raptor', 'ST', 'Tremor', 'FX4', 
                'STX', 'Timberline', 'Active', 'Wildtrak', 'Big Bend', 'Badlands', 'Outer Banks', 'Heritage',
                'Tradesman', 'Big Horn', 'Laramie', 'Rebel', 'Longhorn',
                'SXT', 'R/T', 'Scat Pack', 'Hellcat', 'Redeye', 'Jailbreak', '300S', '300C', 'Pacifica',
                'Latitude', 'Altitude', 'Trailhawk', 'Overland', 'Summit',
                'Rubicon', 'Sahara', 'High Altitude', '4xe', 'Willys', 'Islander',
                'Ultimate', 'N', 'N-Line', 'GT-Line', 'X-Line', 'SX Prestige', 'Calligraphy',
                'SEL', 'Comfortline', 'Highline', 'R-Line', 'GLI', 'GTI', 'R', 'Golf R',
                'Premium Plus', 'Prestige', 'S-Line', 'Progressiv', 'Technik',
                'sDrive', 'xDrive', 'M Sport', 'M', 'Executive', 'Competition',
                'AMG', '4MATIC', 'Exclusive', 'Night', 'Type S',
                'Hybrid', 'Plug-in', 'PHEV', 'EV', 'Electric', 'AWD', '4WD', 'FWD',
                '2WD', '4x4', '4x2', 'Manual', 'Automatic', 'CVT', 'Crew', 'Cab',
                'Double', 'Extended', 'SuperCrew', 'SuperCab', 'Quad', 'Access',
                'Dynamic', 'HSE', 'Autobiography', 'First', 'Velar', 'Evoque',
                'Black Diamond', 'Northline', 'Max'
            }
            
            trim_start_index = len(remaining_words)
            for i, word in enumerate(remaining_words):
                word_clean = word.replace('-', ' ').strip()
                if any(word.upper() == trim.upper() or word_clean.upper() == trim.upper() for trim in trim_indicators):
                    trim_start_index = i
                    break
                if i + 1 < len(remaining_words):
                    two_word = f"{word} {remaining_words[i+1]}"
                    if any(two_word.upper() == trim.upper() for trim in trim_indicators):
                        trim_start_index = i
                        break
            
            if trim_start_index > 0:
                result['model'] = ' '.join(remaining_words[:trim_start_index])
            else:
                if len(remaining_words) >= 2:
                    two_word_model = f"{remaining_words[0]} {remaining_words[1]}"
                    multi_word_models = ['Grand Highlander', 'Range Rover', 'Land Cruiser', 
                                        'Grand Cherokee', 'Santa Fe', 'Civic Type',
                                        'Model S', 'Model 3', 'Model X', 'Model Y']
                    if any(two_word_model.lower() == model.lower() for model in multi_word_models):
                        result['model'] = two_word_model
                        trim_start_index = 2
                    else:
                        result['model'] = remaining_words[0]
                        trim_start_index = 1
                else:
                    result['model'] = ' '.join(remaining_words[:min(2, len(remaining_words))])
                    trim_start_index = min(2, len(remaining_words))
            
            if trim_start_index < len(remaining_words):
                result['trim'] = ' '.join(remaining_words[trim_start_index:])
        
        return result
    
    def scrape_vehicle_detail(self, url):
        """Scrape individual vehicle detail page"""
        logger.info(f"Scraping VDP: {url}")
        soup = self.get_page(url)
        
        if not soup:
            return None
        
        vehicle_data = {
            'title': '', 'id / stock-#': '', 'price': '', 'condition': '',
            'feed label': '', 'body style': '', 'brand': '', 'certified pre-owned': '',
            'color': '', 'description': '', 'engine': '', 'image link': '',
            'link': url, 'mileage': '', 'model': '', 'trim / sub-model': '',
            'vehicle MSRP': '', 'vehicle all in price': '', 'vehicle option': '',
            'vin': '', 'year': ''
        }
        
        page_text = soup.get_text()
        
        # Extract title
        for selector in ['h1', 'h1.vehicle-title', 'h1.vdp-title', '.vehicle-info h1']:
            elem = soup.select_one(selector)
            if elem:
                vehicle_data['title'] = self.clean_text(elem.get_text())
                break
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # Extract stock, VIN, prices, etc. (same as before)
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            text = elem.get_text()
            if 'stock' in text.lower():
                match = re.search(r'(?:Stock|#)\s*[:#]?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
                if match:
                    vehicle_data['id / stock-#'] = match.group(1).strip()
                    break
        
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            text = elem.get_text()
            if 'vin' in text.lower():
                match = re.search(r'([A-HJ-NPR-Z0-9]{17})', text, re.IGNORECASE)
                if match:
                    vehicle_data['vin'] = match.group(1).upper()
                    break
        
        # Price extraction
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3']):
            text = elem.get_text()
            if '$' in text and 'price' in text.lower() and 'msrp' not in text.lower():
                price = self.extract_price(text)
                if price and int(price) > 5000:
                    vehicle_data['price'] = price
                    break
        
        # MSRP
        for elem in soup.find_all(['span', 'div', 'p', 'strong']):
            text = elem.get_text()
            if 'msrp' in text.lower():
                msrp = self.extract_price(text)
                if msrp and int(msrp) > 5000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Mileage
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            text = elem.get_text()
            if 'km' in text.lower() or 'mileage' in text.lower():
                mileage = self.extract_mileage(text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Condition
        if '/inventory/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url:
            vehicle_data['condition'] = 'used'
        
        # Color
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dd']):
            text = elem.get_text()
            if 'exterior' in text.lower() or 'color' in text.lower():
                color = self.clean_text(text)
                color = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color)
                if color and len(color) < 50:
                    vehicle_data['color'] = color
                    break
        
        # Engine
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dd']):
            text = elem.get_text()
            if 'engine' in text.lower() and len(text) < 200:
                engine = self.clean_text(text)
                engine = re.sub(r'(?i)engine[:\s]*', '', engine)
                if engine and len(engine) > 3:
                    vehicle_data['engine'] = engine
                    break
        
        # Image
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src and 'vehicle' in src.lower() or 'inventory' in src.lower():
                vehicle_data['image link'] = urljoin(self.base_url, src)
                break
        
        return vehicle_data
    
    def scrape_inventory_pages(self, urls):
        """Scrape all inventory pages and extract vehicle data"""
        all_vehicles = []
        all_vdp_links = set()
        
        logger.info("Collecting vehicle detail page links...")
        for url in urls:
            logger.info(f"Scanning: {url}")
            soup = self.get_page(url)
            if soup:
                links = self.extract_vehicle_links(soup)
                all_vdp_links.update(links)
                logger.info(f"Found {len(links)} vehicles on this page")
            time.sleep(1)
        
        logger.info(f"Total unique vehicles found: {len(all_vdp_links)}")
        
        logger.info("Scraping individual vehicle pages...")
        for i, vdp_url in enumerate(sorted(all_vdp_links), 1):
            logger.info(f"Progress: {i}/{len(all_vdp_links)}")
            vehicle_data = self.scrape_vehicle_detail(vdp_url)
            if vehicle_data:
                all_vehicles.append(vehicle_data)
            time.sleep(1)
        
        return all_vehicles
