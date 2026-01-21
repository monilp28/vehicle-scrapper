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
                'Black Diamond', 'Northline', 'Max', 'North', 'Progressiv'
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
                                        'Model S', 'Model 3', 'Model X', 'Model Y', 'Crown Signia']
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
        """Scrape individual vehicle detail page with comprehensive extraction and debugging"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping VDP: {url}")
        logger.info(f"{'='*80}")
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
        
        # Save HTML to file for first vehicle (debugging)
        import os
        debug_dir = 'debug_html'
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Save only first 3 vehicles for debugging
        vehicle_num = len(os.listdir(debug_dir)) if os.path.exists(debug_dir) else 0
        if vehicle_num < 3:
            with open(f'{debug_dir}/vehicle_{vehicle_num + 1}.html', 'w', encoding='utf-8') as f:
                f.write(str(soup.prettify()))
            logger.info(f"  💾 DEBUG: Saved HTML to debug_html/vehicle_{vehicle_num + 1}.html")
        
        # 1. EXTRACT TITLE
        logger.info("  🔍 Searching for TITLE...")
        for selector in ['h1', 'h1.vehicle-title', 'h1.vdp-title', '.vehicle-info h1', 'h1.title']:
            elem = soup.select_one(selector)
            if elem:
                vehicle_data['title'] = self.clean_text(elem.get_text())
                logger.info(f"  ✅ Title found: {vehicle_data['title']}")
                break
        
        if not vehicle_data['title']:
            logger.warning("  ⚠️  No title found!")
        
        # 2. PARSE TITLE
        logger.info("  🔍 Parsing TITLE...")
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        logger.info(f"  ✅ Year: {vehicle_data['year']}, Make: {vehicle_data['brand']}, Model: {vehicle_data['model']}, Trim: {vehicle_data['trim / sub-model']}")
        
        # 3. EXTRACT ALL TEXT CONTAINING KEY INFORMATION
        logger.info("  🔍 Scanning entire page for data...")
        
        # Print all elements with class or id containing certain keywords
        logger.info("  📋 Elements with relevant classes/IDs:")
        for elem in soup.find_all(class_=True):
            classes = ' '.join(elem.get('class', []))
            if any(kw in classes.lower() for kw in ['price', 'spec', 'detail', 'feature', 'condition', 'trim']):
                text_preview = self.clean_text(elem.get_text())[:100]
                logger.info(f"    - class='{classes}': {text_preview}")
        
        # 3. CONDITION
        logger.info("  🔍 Searching for CONDITION...")
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
            logger.info(f"  ✅ Condition from URL: new")
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
            logger.info(f"  ✅ Condition from URL: used")
        
        # Check page for condition badges
        for elem in soup.find_all(['span', 'div', 'badge', 'label', 'h2']):
            text = elem.get_text().lower()
            if len(text) < 50:  # Badges are usually short
                if text.strip() == 'new' or 'new vehicle' in text:
                    vehicle_data['condition'] = 'new'
                    logger.info(f"  ✅ Condition from badge: new")
                    break
                elif text.strip() == 'used' or 'pre-owned' in text or 'used vehicle' in text:
                    vehicle_data['condition'] = 'used'
                    logger.info(f"  ✅ Condition from badge: used")
                    break
        
        # 4. STOCK NUMBER
        logger.info("  🔍 Searching for STOCK NUMBER...")
        stock_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'stock' in text.lower() and len(text) < 100:
                match = re.search(r'(?:Stock|Stk|Stock\s*#|Stock\s*Number)[:\s#]*([A-Z0-9-]+)', text, re.IGNORECASE)
                if match:
                    vehicle_data['id / stock-#'] = match.group(1).strip()
                    logger.info(f"  ✅ Stock #: {vehicle_data['id / stock-#']} (from: {text[:50]})")
                    stock_found = True
                    break
        
        if not stock_found:
            logger.warning("  ⚠️  No stock number found!")
        
        # 5. VIN
        logger.info("  🔍 Searching for VIN...")
        vin_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'vin' in text.lower() or len(text.strip()) == 17:
                match = re.search(r'([A-HJ-NPR-Z0-9]{17})', text, re.IGNORECASE)
                if match:
                    vehicle_data['vin'] = match.group(1).upper()
                    logger.info(f"  ✅ VIN: {vehicle_data['vin']}")
                    vin_found = True
                    break
        
        if not vin_found:
            logger.warning("  ⚠️  No VIN found!")
        
        # 6. PRICES
        logger.info("  🔍 Searching for PRICES...")
        all_dollar_elements = []
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3', 'h4', 'td', 'dd', 'li']):
            text = elem.get_text()
            if '
        
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
        
        # 1. EXTRACT TITLE
        for selector in ['h1', 'h1.vehicle-title', 'h1.vdp-title', '.vehicle-info h1', 'h1.title']:
            elem = soup.select_one(selector)
            if elem:
                vehicle_data['title'] = self.clean_text(elem.get_text())
                logger.info(f"  Title: {vehicle_data['title']}")
                break
        
        # 2. PARSE TITLE for year, make, model, trim
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # 3. EXTRACT CONDITION - Multiple methods
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        
        # Also check badge/label elements
        for elem in soup.find_all(['span', 'div', 'badge', 'label']):
            text = elem.get_text().lower()
            classes = ' '.join(elem.get('class', [])).lower()
            if 'new' in text or 'new' in classes:
                if 'vehicle' in text or 'inventory' in classes:
                    vehicle_data['condition'] = 'new'
                    break
            elif 'used' in text or 'pre-owned' in text:
                vehicle_data['condition'] = 'used'
                break
        
        logger.info(f"  Condition: {vehicle_data['condition']}")
        
        # 4. EXTRACT STOCK NUMBER - Enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'stock' in text.lower():
                match = re.search(r'(?:Stock|Stk|Stock\s*#|Stock\s*Number)[:\s#]*([A-Z0-9-]+)', text, re.IGNORECASE)
                if match:
                    vehicle_data['id / stock-#'] = match.group(1).strip()
                    logger.info(f"  Stock #: {vehicle_data['id / stock-#']}")
                    break
        
        # 5. EXTRACT VIN - Enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'vin' in text.lower() or len(text.strip()) == 17:
                match = re.search(r'([A-HJ-NPR-Z0-9]{17})', text, re.IGNORECASE)
                if match:
                    vehicle_data['vin'] = match.group(1).upper()
                    logger.info(f"  VIN: {vehicle_data['vin']}")
                    break
        
        # 6. EXTRACT PRICES - Comprehensive approach
        all_dollar_elements = []
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3', 'h4', 'td', 'dd', 'li']):
            text = elem.get_text()
            if '$' in text:
                all_dollar_elements.append({
                    'text': text,
                    'clean': self.clean_text(text),
                    'class': ' '.join(elem.get('class', [])),
                    'id': elem.get('id', '')
                })
        
        # Extract SELLING PRICE
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            # Skip MSRP
            if 'msrp' in text_lower or 'retail' in text_lower:
                continue
            # Look for selling price keywords
            if any(kw in text_lower for kw in ['our price', 'sale price', 'price:', 'selling price', 'internet price']):
                price = self.extract_price(item['clean'])
                if price and int(price) > 5000:
                    vehicle_data['price'] = price
                    break
        
        # If not found, take first reasonable $ amount (not MSRP)
        if not vehicle_data['price']:
            for item in all_dollar_elements:
                if 'msrp' not in item['clean'].lower():
                    price = self.extract_price(item['clean'])
                    if price and int(price) > 5000:
                        vehicle_data['price'] = price
                        break
        
        # Extract MSRP
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            if 'msrp' in text_lower or 'manufacturer' in text_lower or 'retail' in text_lower:
                msrp = self.extract_price(item['clean'])
                if msrp and int(msrp) > 5000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Extract ALL-IN PRICE
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            if any(kw in text_lower for kw in ['all-in', 'all in', 'total', 'out the door', 'drive away']):
                all_in = self.extract_price(item['clean'])
                if all_in and int(all_in) > 5000:
                    vehicle_data['vehicle all in price'] = all_in
                    break
        
        logger.info(f"  Price: {vehicle_data['price']}, MSRP: {vehicle_data['vehicle MSRP']}, All-in: {vehicle_data['vehicle all in price']}")
        
        # 7. EXTRACT MILEAGE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'km' in text.lower() or 'mileage' in text.lower() or 'odometer' in text.lower():
                mileage = self.extract_mileage(text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    logger.info(f"  Mileage: {mileage}")
                    break
        
        # 8. EXTRACT COLOR
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if any(kw in text.lower() for kw in ['exterior', 'color', 'colour']):
                color = self.clean_text(text)
                color = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color)
                if color and len(color) < 50 and len(color) > 2:
                    vehicle_data['color'] = color
                    logger.info(f"  Color: {color}")
                    break
        
        # 9. EXTRACT ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'engine' in text.lower() and len(text) < 200:
                engine = self.clean_text(text)
                engine = re.sub(r'(?i)engine[:\s]*', '', engine)
                if engine and len(engine) > 3:
                    vehicle_data['engine'] = engine
                    logger.info(f"  Engine: {engine}")
                    break
        
        # 10. EXTRACT BODY STYLE - Multiple approaches
        # Method 1: Look in specs/features
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text().lower()
            if 'body' in text or 'type' in text:
                body = self.clean_text(elem.get_text())
                body = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body)
                # Validate it's actually a body style
                valid_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                               'van', 'minivan', 'convertible', 'crossover', 'pickup', 'crew cab']
                if any(style in body.lower() for style in valid_styles):
                    vehicle_data['body style'] = body
                    logger.info(f"  Body Style: {body}")
                    break
        
        # Method 2: Infer from model name
        if not vehicle_data['body style']:
            model_lower = vehicle_data['model'].lower()
            if 'truck' in model_lower or 'tundra' in model_lower or 'tacoma' in model_lower or 'f-150' in model_lower:
                vehicle_data['body style'] = 'Pickup Truck'
            elif 'suv' in model_lower or 'rav4' in model_lower or 'highlander' in model_lower or 'escape' in model_lower:
                vehicle_data['body style'] = 'SUV'
            elif 'sedan' in model_lower or 'camry' in model_lower or 'corolla' in model_lower or 'accord' in model_lower:
                vehicle_data['body style'] = 'Sedan'
            elif 'van' in model_lower or 'sienna' in model_lower or 'pacifica' in model_lower:
                vehicle_data['body style'] = 'Minivan'
        
        # 11. EXTRACT DESCRIPTION - Multiple methods
        # Method 1: Look for description div/section
        for elem in soup.find_all(['div', 'section', 'p']):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            if any(kw in classes or kw in elem_id for kw in ['description', 'overview', 'details', 'comments']):
                desc = self.clean_text(elem.get_text())
                if len(desc) > 50 and len(desc) < 3000:
                    vehicle_data['description'] = desc
                    logger.info(f"  Description length: {len(desc)} chars")
                    break
        
        # Method 2: Look for paragraphs with substantial text
        if not vehicle_data['description']:
            for elem in soup.find_all('p'):
                text = self.clean_text(elem.get_text())
                if len(text) > 100 and len(text) < 3000:
                    # Check if it's not just a list of specs
                    if ',' not in text[:50]:  # Descriptions usually start with sentences
                        vehicle_data['description'] = text
                        logger.info(f"  Description found (fallback): {len(text)} chars")
                        break
        
        # 12. EXTRACT VEHICLE OPTIONS/FEATURES
        options = []
        # Look for feature lists
        for ul in soup.find_all(['ul', 'ol']):
            parent_text = ''
            parent = ul.find_parent(['div', 'section'])
            if parent:
                parent_text = self.clean_text(parent.get_text()[:100]).lower()
            
            # Check if this list contains features
            if any(kw in parent_text for kw in ['feature', 'option', 'equipment', 'include', 'standard']):
                for li in ul.find_all('li'):
                    option = self.clean_text(li.get_text())
                    if option and len(option) < 150 and len(option) > 3:
                        options.append(option)
        
        # Also check for dl/dt/dd pairs (definition lists)
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                feature = f"{self.clean_text(dt.get_text())}: {self.clean_text(dd.get_text())}"
                if len(feature) < 150:
                    options.append(feature)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])
            logger.info(f"  Options found: {len(options)} items")
        
        # 13. CHECK FOR CERTIFIED PRE-OWNED
        cpo_keywords = ['certified pre-owned', 'cpo', 'certified used', 'certified']
        if any(kw in page_text.lower() for kw in cpo_keywords):
            # Make sure it's actually CPO, not just mentioning certification
            for elem in soup.find_all(['div', 'span', 'badge', 'label', 'h2', 'h3']):
                text = elem.get_text().lower()
                if 'certified pre-owned' in text or 'cpo' in text:
                    vehicle_data['certified pre-owned'] = 'yes'
                    logger.info(f"  CPO: Yes")
                    break
        
        # 14. EXTRACT IMAGE
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            alt = img.get('alt', '').lower()
            if src:
                # Skip logos, icons, buttons
                if any(skip in src.lower() for skip in ['logo', 'icon', 'button', 'badge']):
                    continue
                # Prefer vehicle-specific images
                if any(kw in src.lower() or kw in alt for kw in ['vehicle', 'inventory', 'stock', 'auto']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Fallback: first large image
        if not vehicle_data['image link']:
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and 'logo' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # 15. TRY JSON-LD STRUCTURED DATA
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['description'] and data.get('description'):
                        vehicle_data['description'] = data['description']
            except:
                continue
        
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
 in text:
                all_dollar_elements.append({
                    'text': self.clean_text(text),
                    'class': ' '.join(elem.get('class', [])),
                })
        
        logger.info(f"  📊 Found {len(all_dollar_elements)} elements with $ signs")
        for i, item in enumerate(all_dollar_elements[:10], 1):  # Show first 10
            logger.info(f"    {i}. [{item['class'][:30]}] {item['text'][:80]}")
        
        # Extract SELLING PRICE
        price_found = False
        for item in all_dollar_elements:
            text_lower = item['text'].lower()
            if 'msrp' in text_lower or 'retail' in text_lower:
                continue
            if any(kw in text_lower for kw in ['our price', 'sale price', 'price:', 'selling']):
                price = self.extract_price(item['text'])
                if price and int(price) > 5000:
                    vehicle_data['price'] = price
                    logger.info(f"  ✅ Selling Price: ${price} (from: {item['text'][:60]})")
                    price_found = True
                    break
        
        if not price_found:
            for item in all_dollar_elements:
                if 'msrp' not in item['text'].lower():
                    price = self.extract_price(item['text'])
                    if price and int(price) > 5000:
                        vehicle_data['price'] = price
                        logger.info(f"  ✅ Selling Price (fallback): ${price}")
                        price_found = True
                        break
        
        if not price_found:
            logger.warning("  ⚠️  No selling price found!")
        
        # Extract MSRP
        msrp_found = False
        for item in all_dollar_elements:
            text_lower = item['text'].lower()
            if 'msrp' in text_lower or 'manufacturer' in text_lower or 'retail' in text_lower:
                msrp = self.extract_price(item['text'])
                if msrp and int(msrp) > 5000:
                    vehicle_data['vehicle MSRP'] = msrp
                    logger.info(f"  ✅ MSRP: ${msrp} (from: {item['text'][:60]})")
                    msrp_found = True
                    break
        
        if not msrp_found:
            logger.info("  ℹ️  No MSRP found")
        
        # 7. MILEAGE
        logger.info("  🔍 Searching for MILEAGE...")
        mileage_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'km' in text.lower() or 'mileage' in text.lower() or 'odometer' in text.lower():
                if len(text) < 200:  # Avoid long paragraphs
                    mileage = self.extract_mileage(text)
                    if mileage:
                        vehicle_data['mileage'] = mileage
                        logger.info(f"  ✅ Mileage: {mileage} km (from: {text[:60]})")
                        mileage_found = True
                        break
        
        if not mileage_found:
            logger.info("  ℹ️  No mileage found (may be new vehicle)")
        
        # 8. COLOR
        logger.info("  🔍 Searching for COLOR...")
        color_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if any(kw in text.lower() for kw in ['exterior', 'color', 'colour']) and len(text) < 100:
                color = self.clean_text(text)
                color = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color)
                if color and len(color) < 50 and len(color) > 2:
                    vehicle_data['color'] = color
                    logger.info(f"  ✅ Color: {color}")
                    color_found = True
                    break
        
        if not color_found:
            logger.warning("  ⚠️  No color found!")
        
        # 9. ENGINE
        logger.info("  🔍 Searching for ENGINE...")
        engine_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'engine' in text.lower() and len(text) < 200:
                engine = self.clean_text(text)
                engine = re.sub(r'(?i)engine[:\s]*', '', engine)
                if engine and len(engine) > 3 and len(engine) < 100:
                    vehicle_data['engine'] = engine
                    logger.info(f"  ✅ Engine: {engine}")
                    engine_found = True
                    break
        
        if not engine_found:
            logger.warning("  ⚠️  No engine info found!")
        
        # 10. BODY STYLE
        logger.info("  🔍 Searching for BODY STYLE...")
        body_found = False
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text().lower()
            if ('body' in text or 'type' in text or 'style' in text) and len(text) < 150:
                body = self.clean_text(elem.get_text())
                body = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body)
                valid_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                               'van', 'minivan', 'convertible', 'crossover', 'pickup', 'crew cab']
                if any(style in body.lower() for style in valid_styles):
                    vehicle_data['body style'] = body
                    logger.info(f"  ✅ Body Style: {body}")
                    body_found = True
                    break
        
        # Infer from model if not found
        if not body_found:
            model_lower = vehicle_data['model'].lower()
            if any(kw in model_lower for kw in ['tundra', 'tacoma', 'f-150', 'silverado', 'ram', 'frontier']):
                vehicle_data['body style'] = 'Pickup Truck'
                logger.info(f"  ✅ Body Style (inferred): Pickup Truck")
                body_found = True
            elif any(kw in model_lower for kw in ['rav4', 'highlander', 'escape', 'cr-v', '4runner', 'pilot']):
                vehicle_data['body style'] = 'SUV'
                logger.info(f"  ✅ Body Style (inferred): SUV")
                body_found = True
            elif any(kw in model_lower for kw in ['camry', 'corolla', 'accord', 'civic', 'altima', 'elantra']):
                vehicle_data['body style'] = 'Sedan'
                logger.info(f"  ✅ Body Style (inferred): Sedan")
                body_found = True
            elif any(kw in model_lower for kw in ['sienna', 'pacifica', 'odyssey']):
                vehicle_data['body style'] = 'Minivan'
                logger.info(f"  ✅ Body Style (inferred): Minivan")
                body_found = True
        
        if not body_found:
            logger.warning("  ⚠️  No body style found!")
        
        # 11. DESCRIPTION
        logger.info("  🔍 Searching for DESCRIPTION...")
        desc_found = False
        for elem in soup.find_all(['div', 'section', 'p']):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            if any(kw in classes or kw in elem_id for kw in ['description', 'overview', 'details', 'comments', 'about']):
                desc = self.clean_text(elem.get_text())
                if len(desc) > 50 and len(desc) < 3000:
                    vehicle_data['description'] = desc
                    logger.info(f"  ✅ Description: {len(desc)} characters")
                    desc_found = True
                    break
        
        if not desc_found:
            logger.warning("  ⚠️  No description found!")
        
        # 12. VEHICLE OPTIONS
        logger.info("  🔍 Searching for VEHICLE OPTIONS...")
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            parent = ul.find_parent(['div', 'section'])
            if parent:
                parent_text = self.clean_text(parent.get_text()[:200]).lower()
                if any(kw in parent_text for kw in ['feature', 'option', 'equipment', 'include', 'standard']):
                    for li in ul.find_all('li'):
                        option = self.clean_text(li.get_text())
                        if option and len(option) < 150 and len(option) > 3:
                            options.append(option)
                    if options:
                        break
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])
            logger.info(f"  ✅ Vehicle Options: {len(options)} items found")
        else:
            logger.warning("  ⚠️  No vehicle options found!")
        
        # 13. CERTIFIED PRE-OWNED
        logger.info("  🔍 Searching for CERTIFIED PRE-OWNED...")
        cpo_found = False
        for elem in soup.find_all(['div', 'span', 'badge', 'label', 'h2', 'h3']):
            text = elem.get_text().lower()
            if 'certified pre-owned' in text or ('certified' in text and 'used' in text):
                vehicle_data['certified pre-owned'] = 'yes'
                logger.info(f"  ✅ CPO: Yes (from: {text[:60]})")
                cpo_found = True
                break
        
        if not cpo_found:
            logger.info("  ℹ️  Not certified pre-owned")
        
        # 14. IMAGE
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                vehicle_data['image link'] = urljoin(self.base_url, src)
                break
        
        logger.info(f"\n{'='*80}")
        logger.info(f"SCRAPING COMPLETE - Summary:")
        logger.info(f"  Title: {vehicle_data['title']}")
        logger.info(f"  Stock: {vehicle_data['id / stock-#']}")
        logger.info(f"  VIN: {vehicle_data['vin']}")
        logger.info(f"  Price: {vehicle_data['price']}")
        logger.info(f"  Condition: {vehicle_data['condition']}")
        logger.info(f"  Body Style: {vehicle_data['body style']}")
        logger.info(f"  Description: {'Yes' if vehicle_data['description'] else 'No'}")
        logger.info(f"  Options: {'Yes' if vehicle_data['vehicle option'] else 'No'}")
        logger.info(f"{'='*80}\n")
        
        return vehicle_data
        
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
        
        # 1. EXTRACT TITLE
        for selector in ['h1', 'h1.vehicle-title', 'h1.vdp-title', '.vehicle-info h1', 'h1.title']:
            elem = soup.select_one(selector)
            if elem:
                vehicle_data['title'] = self.clean_text(elem.get_text())
                logger.info(f"  Title: {vehicle_data['title']}")
                break
        
        # 2. PARSE TITLE for year, make, model, trim
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # 3. EXTRACT CONDITION - Multiple methods
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        
        # Also check badge/label elements
        for elem in soup.find_all(['span', 'div', 'badge', 'label']):
            text = elem.get_text().lower()
            classes = ' '.join(elem.get('class', [])).lower()
            if 'new' in text or 'new' in classes:
                if 'vehicle' in text or 'inventory' in classes:
                    vehicle_data['condition'] = 'new'
                    break
            elif 'used' in text or 'pre-owned' in text:
                vehicle_data['condition'] = 'used'
                break
        
        logger.info(f"  Condition: {vehicle_data['condition']}")
        
        # 4. EXTRACT STOCK NUMBER - Enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'stock' in text.lower():
                match = re.search(r'(?:Stock|Stk|Stock\s*#|Stock\s*Number)[:\s#]*([A-Z0-9-]+)', text, re.IGNORECASE)
                if match:
                    vehicle_data['id / stock-#'] = match.group(1).strip()
                    logger.info(f"  Stock #: {vehicle_data['id / stock-#']}")
                    break
        
        # 5. EXTRACT VIN - Enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd', 'strong']):
            text = elem.get_text()
            if 'vin' in text.lower() or len(text.strip()) == 17:
                match = re.search(r'([A-HJ-NPR-Z0-9]{17})', text, re.IGNORECASE)
                if match:
                    vehicle_data['vin'] = match.group(1).upper()
                    logger.info(f"  VIN: {vehicle_data['vin']}")
                    break
        
        # 6. EXTRACT PRICES - Comprehensive approach
        all_dollar_elements = []
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3', 'h4', 'td', 'dd', 'li']):
            text = elem.get_text()
            if '$' in text:
                all_dollar_elements.append({
                    'text': text,
                    'clean': self.clean_text(text),
                    'class': ' '.join(elem.get('class', [])),
                    'id': elem.get('id', '')
                })
        
        # Extract SELLING PRICE
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            # Skip MSRP
            if 'msrp' in text_lower or 'retail' in text_lower:
                continue
            # Look for selling price keywords
            if any(kw in text_lower for kw in ['our price', 'sale price', 'price:', 'selling price', 'internet price']):
                price = self.extract_price(item['clean'])
                if price and int(price) > 5000:
                    vehicle_data['price'] = price
                    break
        
        # If not found, take first reasonable $ amount (not MSRP)
        if not vehicle_data['price']:
            for item in all_dollar_elements:
                if 'msrp' not in item['clean'].lower():
                    price = self.extract_price(item['clean'])
                    if price and int(price) > 5000:
                        vehicle_data['price'] = price
                        break
        
        # Extract MSRP
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            if 'msrp' in text_lower or 'manufacturer' in text_lower or 'retail' in text_lower:
                msrp = self.extract_price(item['clean'])
                if msrp and int(msrp) > 5000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Extract ALL-IN PRICE
        for item in all_dollar_elements:
            text_lower = item['clean'].lower()
            if any(kw in text_lower for kw in ['all-in', 'all in', 'total', 'out the door', 'drive away']):
                all_in = self.extract_price(item['clean'])
                if all_in and int(all_in) > 5000:
                    vehicle_data['vehicle all in price'] = all_in
                    break
        
        logger.info(f"  Price: {vehicle_data['price']}, MSRP: {vehicle_data['vehicle MSRP']}, All-in: {vehicle_data['vehicle all in price']}")
        
        # 7. EXTRACT MILEAGE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'km' in text.lower() or 'mileage' in text.lower() or 'odometer' in text.lower():
                mileage = self.extract_mileage(text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    logger.info(f"  Mileage: {mileage}")
                    break
        
        # 8. EXTRACT COLOR
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if any(kw in text.lower() for kw in ['exterior', 'color', 'colour']):
                color = self.clean_text(text)
                color = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color)
                if color and len(color) < 50 and len(color) > 2:
                    vehicle_data['color'] = color
                    logger.info(f"  Color: {color}")
                    break
        
        # 9. EXTRACT ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text()
            if 'engine' in text.lower() and len(text) < 200:
                engine = self.clean_text(text)
                engine = re.sub(r'(?i)engine[:\s]*', '', engine)
                if engine and len(engine) > 3:
                    vehicle_data['engine'] = engine
                    logger.info(f"  Engine: {engine}")
                    break
        
        # 10. EXTRACT BODY STYLE - Multiple approaches
        # Method 1: Look in specs/features
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            text = elem.get_text().lower()
            if 'body' in text or 'type' in text:
                body = self.clean_text(elem.get_text())
                body = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body)
                # Validate it's actually a body style
                valid_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                               'van', 'minivan', 'convertible', 'crossover', 'pickup', 'crew cab']
                if any(style in body.lower() for style in valid_styles):
                    vehicle_data['body style'] = body
                    logger.info(f"  Body Style: {body}")
                    break
        
        # Method 2: Infer from model name
        if not vehicle_data['body style']:
            model_lower = vehicle_data['model'].lower()
            if 'truck' in model_lower or 'tundra' in model_lower or 'tacoma' in model_lower or 'f-150' in model_lower:
                vehicle_data['body style'] = 'Pickup Truck'
            elif 'suv' in model_lower or 'rav4' in model_lower or 'highlander' in model_lower or 'escape' in model_lower:
                vehicle_data['body style'] = 'SUV'
            elif 'sedan' in model_lower or 'camry' in model_lower or 'corolla' in model_lower or 'accord' in model_lower:
                vehicle_data['body style'] = 'Sedan'
            elif 'van' in model_lower or 'sienna' in model_lower or 'pacifica' in model_lower:
                vehicle_data['body style'] = 'Minivan'
        
        # 11. EXTRACT DESCRIPTION - Multiple methods
        # Method 1: Look for description div/section
        for elem in soup.find_all(['div', 'section', 'p']):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            if any(kw in classes or kw in elem_id for kw in ['description', 'overview', 'details', 'comments']):
                desc = self.clean_text(elem.get_text())
                if len(desc) > 50 and len(desc) < 3000:
                    vehicle_data['description'] = desc
                    logger.info(f"  Description length: {len(desc)} chars")
                    break
        
        # Method 2: Look for paragraphs with substantial text
        if not vehicle_data['description']:
            for elem in soup.find_all('p'):
                text = self.clean_text(elem.get_text())
                if len(text) > 100 and len(text) < 3000:
                    # Check if it's not just a list of specs
                    if ',' not in text[:50]:  # Descriptions usually start with sentences
                        vehicle_data['description'] = text
                        logger.info(f"  Description found (fallback): {len(text)} chars")
                        break
        
        # 12. EXTRACT VEHICLE OPTIONS/FEATURES
        options = []
        # Look for feature lists
        for ul in soup.find_all(['ul', 'ol']):
            parent_text = ''
            parent = ul.find_parent(['div', 'section'])
            if parent:
                parent_text = self.clean_text(parent.get_text()[:100]).lower()
            
            # Check if this list contains features
            if any(kw in parent_text for kw in ['feature', 'option', 'equipment', 'include', 'standard']):
                for li in ul.find_all('li'):
                    option = self.clean_text(li.get_text())
                    if option and len(option) < 150 and len(option) > 3:
                        options.append(option)
        
        # Also check for dl/dt/dd pairs (definition lists)
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                feature = f"{self.clean_text(dt.get_text())}: {self.clean_text(dd.get_text())}"
                if len(feature) < 150:
                    options.append(feature)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])
            logger.info(f"  Options found: {len(options)} items")
        
        # 13. CHECK FOR CERTIFIED PRE-OWNED
        cpo_keywords = ['certified pre-owned', 'cpo', 'certified used', 'certified']
        if any(kw in page_text.lower() for kw in cpo_keywords):
            # Make sure it's actually CPO, not just mentioning certification
            for elem in soup.find_all(['div', 'span', 'badge', 'label', 'h2', 'h3']):
                text = elem.get_text().lower()
                if 'certified pre-owned' in text or 'cpo' in text:
                    vehicle_data['certified pre-owned'] = 'yes'
                    logger.info(f"  CPO: Yes")
                    break
        
        # 14. EXTRACT IMAGE
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            alt = img.get('alt', '').lower()
            if src:
                # Skip logos, icons, buttons
                if any(skip in src.lower() for skip in ['logo', 'icon', 'button', 'badge']):
                    continue
                # Prefer vehicle-specific images
                if any(kw in src.lower() or kw in alt for kw in ['vehicle', 'inventory', 'stock', 'auto']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Fallback: first large image
        if not vehicle_data['image link']:
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and 'logo' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # 15. TRY JSON-LD STRUCTURED DATA
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['description'] and data.get('description'):
                        vehicle_data['description'] = data['description']
            except:
                continue
        
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
