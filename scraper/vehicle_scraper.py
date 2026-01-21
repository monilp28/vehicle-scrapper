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
        # Remove dollar signs, commas, and extra whitespace
        text = text.replace('
    
    def extract_mileage(self, text):
        """Extract mileage from text"""
        if not text:
            return ""
        # Look for numbers followed by km or miles
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
        
        # Extract year first
        result['year'] = self.extract_year(title)
        
        # Remove year from title for easier parsing
        title_without_year = re.sub(r'\b(19\d{2}|20[0-3]\d)\b', '', title).strip()
        words = title_without_year.split()
        
        if not words:
            return result
        
        # Comprehensive list of automotive brands
        all_makes = {
            'Toyota', 'Lexus', 'Honda', 'Acura', 'Nissan', 'Infiniti', 'Mazda', 
            'Subaru', 'Mitsubishi', 'Suzuki', 'Isuzu',
            'Ford', 'Chevrolet', 'Chevy', 'GMC', 'Buick', 'Cadillac', 'Dodge', 
            'Ram', 'Jeep', 'Chrysler', 'Lincoln', 'Tesla',
            'BMW', 'Mercedes-Benz', 'Mercedes', 'Audi', 'Volkswagen', 'VW', 
            'Porsche', 'Volvo', 'Land Rover', 'Land', 'Range Rover', 'Range', 'Jaguar', 'MINI',
            'Hyundai', 'Kia', 'Genesis',
            'Scion', 'Fiat', 'Alfa Romeo', 'Maserati'
        }
        
        # Find make (case-insensitive)
        make_index = -1
        for i, word in enumerate(words):
            for make in all_makes:
                if word.lower() == make.lower():
                    # Special handling for multi-word makes
                    if make == 'Land' and i + 1 < len(words) and words[i + 1].lower() == 'rover':
                        result['make'] = 'Land Rover'
                        make_index = i + 1  # Skip "Rover" in next iteration
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
            
            # Comprehensive trim indicators - EXPANDED
            trim_indicators = {
                # Toyota/Lexus
                'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD', 
                'Nightshade', 'Pro', 'Trail', 'Off-Road', 'Adventure', 'Premium',
                'GR', 'Sport', 'Upgrade', 'Technology', 'Luxury',
                # Honda/Acura
                'LX', 'EX', 'EX-L', 'Touring', 'Sport', 'Type R', 'Type-R', 'Type-S',
                'Si', 'A-Spec', 'Tech', 'Elite', 'Advance',
                # Nissan/Infiniti
                'S', 'SV', 'SL', 'SR', 'Nismo', 'Pro-4X', 'Luxe', 'Essential',
                'Midnight', 'Edition', 'Platinum', 'Reserve',
                # Mazda
                'GX', 'GS', 'GT', 'Signature', 'Carbon Edition', 'Preferred',
                # Subaru
                'Base', 'Premium', 'Limited', 'Touring', 'Wilderness', 'XT',
                'WRX', 'STI', 'Outback', 'Forester', 'Onyx',
                # GM (Chevy, GMC, Buick, Cadillac)
                'LS', 'LT', 'LTZ', 'Premier', 'High Country', 'RST', 'RS', 'SS',
                'ZL1', 'Z71', 'AT4', 'Denali', 'SLT', 'SLE', 'Avenir', 'Essence',
                'Essence', 'Sport Touring', 'LT1', 'LT2', 'LT3',
                # Ford
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Platinum', 'Limited', 'Raptor',
                'ST', 'Tremor', 'FX4', 'STX', 'Timberline', 'Active', 'Wildtrak',
                'Big Bend', 'Badlands', 'Outer Banks', 'Heritage',
                # Ram/Dodge/Chrysler
                'Tradesman', 'Big Horn', 'Laramie', 'Rebel', 'Longhorn', 'Limited',
                'SXT', 'GT', 'R/T', 'Scat Pack', 'Hellcat', 'Redeye', 'Jailbreak',
                'Touring', 'Touring-L', '300S', '300C', 'Pacifica',
                # Jeep
                'Sport', 'Latitude', 'Altitude', 'Trailhawk', 'Overland', 'Summit',
                'Rubicon', 'Sahara', 'High Altitude', '4xe', 'Willys', 'Islander',
                # Hyundai/Kia/Genesis
                'Essential', 'Preferred', 'Luxury', 'Ultimate', 'N', 'N-Line',
                'EX', 'SX', 'GT-Line', 'X-Line', 'SX Prestige', 'Calligraphy',
                'Advanced', 'Prestige', 'Elite', 'Sport Advanced', 'Sport Prestige',
                # Volkswagen/Audi
                'S', 'SE', 'SEL', 'Comfortline', 'Highline', 'R-Line', 'GLI', 'GTI',
                'R', 'Golf R', 'Premium', 'Premium Plus', 'Prestige', 'S-Line', 'RS',
                'Progressiv', 'Technik',
                # BMW
                'sDrive', 'xDrive', 'M Sport', 'M', 'Luxury', 'Executive', 'Competition',
                # Mercedes
                'AMG', '4MATIC', 'Exclusive', 'Luxury', 'Sport', 'Night',
                # Acura
                'A-Spec', 'Type S', 'Advance', 'Technology',
                # Common descriptors
                'Hybrid', 'Plug-in', 'PHEV', 'EV', 'Electric', 'AWD', '4WD', 'FWD',
                '2WD', '4x4', '4x2', 'Manual', 'Automatic', 'CVT', 'Crew', 'Cab',
                'Double', 'Extended', 'SuperCrew', 'SuperCab', 'Quad', 'Access',
                # Land Rover
                'Dynamic', 'HSE', 'Autobiography', 'First Edition', 'Velar', 'Evoque',
                # Other
                'Black Diamond', 'Northline', 'Max'
            }
            
            # Find where trim starts
            trim_start_index = len(remaining_words)
            for i, word in enumerate(remaining_words):
                # Clean word for comparison
                word_clean = word.replace('-', ' ').strip()
                
                # Check if this word is a trim indicator
                if any(word.upper() == trim.upper() or word_clean.upper() == trim.upper() for trim in trim_indicators):
                    trim_start_index = i
                    break
                
                # Also check for compound trim names (e.g., "Off-Road", "Big Horn")
                if i + 1 < len(remaining_words):
                    two_word = f"{word} {remaining_words[i+1]}"
                    if any(two_word.upper() == trim.upper() for trim in trim_indicators):
                        trim_start_index = i
                        break
            
            # Model is everything before trim
            if trim_start_index > 0:
                result['model'] = ' '.join(remaining_words[:trim_start_index])
            else:
                # No clear trim found, assume first 1-3 words are model
                # Handle multi-word models (Grand Highlander, Range Rover, etc.)
                if len(remaining_words) >= 2:
                    # Check if first two words form a known multi-word model
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
            
            # Trim is everything after model
            if trim_start_index < len(remaining_words):
                result['trim'] = ' '.join(remaining_words[trim_start_index:])
        
        return result
    
    def find_element_with_multiple_selectors(self, soup, selectors, extract_func=None):
        """Try multiple selectors and return first match"""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    match = re.search(r'([^:]+):contains\("([^"]+)"\)', selector)
                    if match:
                        tag = match.group(1)
                        text = match.group(2)
                        elements = soup.find_all(tag)
                        for elem in elements:
                            if text.lower() in elem.get_text().lower():
                                if extract_func:
                                    return extract_func(elem.get_text())
                                return self.clean_text(elem.get_text())
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text()
                        if extract_func:
                            return extract_func(text)
                        return self.clean_text(text)
            except Exception:
                continue
        return ""
    
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
        
        # Get all text content for searching
        page_text = soup.get_text()
        
        # Extract title - expanded selectors
        title_selectors = [
            'h1', 'h1.vehicle-title', 'h1.vdp-title', 'h1.title', 
            '.vehicle-info h1', '.vdp-header h1', '[data-vehicle-title]',
            '.inventory-title', '.vehicle-name', '.product-title'
        ]
        vehicle_data['title'] = self.find_element_with_multiple_selectors(soup, title_selectors)
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # If model/trim not found in title, try to extract from page structure
        if not vehicle_data['model']:
            # Look for model in dedicated fields
            for elem in soup.find_all(['span', 'div', 'dd', 'td']):
                elem_text = elem.get_text().strip()
                prev_elem = elem.find_previous(['dt', 'th', 'label', 'span'])
                if prev_elem and 'model' in prev_elem.get_text().lower():
                    vehicle_data['model'] = self.clean_text(elem_text)
                    break
        
        if not vehicle_data['trim / sub-model']:
            # Look for trim in dedicated fields
            for elem in soup.find_all(['span', 'div', 'dd', 'td']):
                elem_text = elem.get_text().strip()
                prev_elem = elem.find_previous(['dt', 'th', 'label', 'span'])
                if prev_elem and 'trim' in prev_elem.get_text().lower():
                    vehicle_data['trim / sub-model'] = self.clean_text(elem_text)
                    break
        
        # Extract STOCK NUMBER with more patterns
        stock_patterns = [
            r'(?:Stock|Stk|Stock #|Stock Number)[:\s#]*([A-Z0-9-]+)',
            r'#\s*([A-Z0-9]{5,})',
            r'Stock:\s*([A-Z0-9-]+)'
        ]
        
        # Try dedicated stock elements
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'stock' in elem_text.lower():
                for pattern in stock_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['id / stock-#'] = match.group(1).strip()
                        break
                if vehicle_data['id / stock-#']:
                    break
        
        # Extract VIN with more patterns
        vin_patterns = [
            r'VIN[:\s]*([A-HJ-NPR-Z0-9]{17})',
            r'(?:^|\s)([A-HJ-NPR-Z0-9]{17})(?:\s|$)'
        ]
        
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'vin' in elem_text.lower() or len(elem_text.strip()) == 17:
                for pattern in vin_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['vin'] = match.group(1).upper()
                        break
                if vehicle_data['vin']:
                    break
        
        # Extract PRICE - Enhanced with multiple comprehensive methods
        price_found = False
        msrp_found = False
        all_in_price_found = False
        
        # Collect ALL price-related elements first
        price_elements = []
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3', 'h4', 'td', 'dd']):
            elem_text = elem.get_text()
            elem_class = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            
            # If contains $ sign or price-related keywords
            if '
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
, '').replace(',', '').strip()
        # Find the largest number (likely the price)
        numbers = re.findall(r'\d+', text)
        if numbers:
            # Return the largest number found (prices are usually the biggest numbers)
            prices = [int(n) for n in numbers if len(n) >= 4]  # At least 4 digits
            if prices:
                return str(max(prices))
        return ""
    
    def extract_mileage(self, text):
        """Extract mileage from text"""
        if not text:
            return ""
        # Look for numbers followed by km or miles
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
            'Porsche', 'Volvo', 'Land Rover', 'Range Rover', 'Jaguar', 'MINI',
            'Hyundai', 'Kia', 'Genesis',
            'Scion'
        }
        
        make_index = -1
        for i, word in enumerate(words):
            for make in all_makes:
                if word.lower() == make.lower():
                    result['make'] = make if make != 'Chevy' else 'Chevrolet'
                    make_index = i
                    break
            if make_index != -1:
                break
        
        if make_index != -1 and make_index + 1 < len(words):
            remaining_words = words[make_index + 1:]
            
            trim_indicators = {
                'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD',
                'LX', 'EX', 'EX-L', 'Touring', 'Sport', 'Type R',
                'S', 'SV', 'SL', 'SR', 'Nismo', 'Pro-4X',
                'LS', 'LT', 'LTZ', 'Premier', 'RS', 'SS', 'Denali',
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Raptor',
                'SXT', 'GT', 'R/T', 'Hellcat',
                'Hybrid', 'AWD', '4WD', 'FWD', '4x4', '4x2'
            }
            
            trim_start_index = len(remaining_words)
            for i, word in enumerate(remaining_words):
                if any(word.upper() == trim.upper() for trim in trim_indicators):
                    trim_start_index = i
                    break
            
            if trim_start_index > 0:
                result['model'] = ' '.join(remaining_words[:trim_start_index])
            else:
                result['model'] = ' '.join(remaining_words[:min(2, len(remaining_words))])
                trim_start_index = min(2, len(remaining_words))
            
            if trim_start_index < len(remaining_words):
                result['trim'] = ' '.join(remaining_words[trim_start_index:])
        
        return result
    
    def find_element_with_multiple_selectors(self, soup, selectors, extract_func=None):
        """Try multiple selectors and return first match"""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    match = re.search(r'([^:]+):contains\("([^"]+)"\)', selector)
                    if match:
                        tag = match.group(1)
                        text = match.group(2)
                        elements = soup.find_all(tag)
                        for elem in elements:
                            if text.lower() in elem.get_text().lower():
                                if extract_func:
                                    return extract_func(elem.get_text())
                                return self.clean_text(elem.get_text())
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text()
                        if extract_func:
                            return extract_func(text)
                        return self.clean_text(text)
            except Exception:
                continue
        return ""
    
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
        
        # Get all text content for searching
        page_text = soup.get_text()
        
        # Extract title - expanded selectors
        title_selectors = [
            'h1', 'h1.vehicle-title', 'h1.vdp-title', 'h1.title', 
            '.vehicle-info h1', '.vdp-header h1', '[data-vehicle-title]',
            '.inventory-title', '.vehicle-name', '.product-title'
        ]
        vehicle_data['title'] = self.find_element_with_multiple_selectors(soup, title_selectors)
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # Extract STOCK NUMBER with more patterns
        stock_patterns = [
            r'(?:Stock|Stk|Stock #|Stock Number)[:\s#]*([A-Z0-9-]+)',
            r'#\s*([A-Z0-9]{5,})',
            r'Stock:\s*([A-Z0-9-]+)'
        ]
        
        # Try dedicated stock elements
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'stock' in elem_text.lower():
                for pattern in stock_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['id / stock-#'] = match.group(1).strip()
                        break
                if vehicle_data['id / stock-#']:
                    break
        
        # Extract VIN with more patterns
        vin_patterns = [
            r'VIN[:\s]*([A-HJ-NPR-Z0-9]{17})',
            r'(?:^|\s)([A-HJ-NPR-Z0-9]{17})(?:\s|$)'
        ]
        
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'vin' in elem_text.lower() or len(elem_text.strip()) == 17:
                for pattern in vin_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['vin'] = match.group(1).upper()
                        break
                if vehicle_data['vin']:
                    break
        
        # Extract PRICE - multiple approaches
        price_found = False
        
        # Method 1: Look for price in common elements
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3']):
            elem_text = elem.get_text()
            if '$' in elem_text and not price_found:
                # Look for selling price indicators
                if any(keyword in elem_text.lower() for keyword in ['price', 'sale', 'cost', 'our price']):
                    price = self.extract_price(elem_text)
                    if price and int(price) > 1000:  # Reasonable vehicle price
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Method 2: Try specific selectors
        if not price_found:
            price_selectors = [
                '.price', '.selling-price', '.our-price', '.vehicle-price',
                '[data-price]', '#price', '.sale-price', '.internet-price',
                '.final-price', '.discounted-price'
            ]
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price = self.extract_price(elem.get_text())
                    if price and int(price) > 1000:
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Extract MSRP
        for elem in soup.find_all(['span', 'div', 'p', 'strong']):
            elem_text = elem.get_text()
            if 'msrp' in elem_text.lower() or 'retail' in elem_text.lower():
                msrp = self.extract_price(elem_text)
                if msrp and int(msrp) > 1000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
 in elem_text or any(keyword in elem_text.lower() for keyword in ['price', 'msrp', 'cost', 'sale']):
                price_elements.append({
                    'element': elem,
                    'text': elem_text,
                    'class': elem_class,
                    'id': elem_id
                })
        
        # Method 1: Look for SELLING PRICE (our price, sale price, internet price)
        for item in price_elements:
            elem_text = item['text'].lower()
            elem_class = item['class']
            elem_id = item['id']
            
            # Selling price indicators
            if not price_found and any(indicator in elem_text for indicator in [
                'our price', 'sale price', 'selling price', 'your price', 
                'internet price', 'online price', 'special price', 'price:'
            ]) or any(indicator in elem_class for indicator in [
                'selling', 'sale', 'our-price', 'internet', 'final', 'discounted'
            ]):
                price = self.extract_price(item['text'])
                if price and int(price) > 5000:  # Reasonable minimum vehicle price
                    vehicle_data['price'] = price
                    price_found = True
        
        # Method 2: If not found, look for any element with $ and "price"
        if not price_found:
            for item in price_elements:
                if 'price' in item['text'].lower() and '
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
, '').replace(',', '').strip()
        # Find the largest number (likely the price)
        numbers = re.findall(r'\d+', text)
        if numbers:
            # Return the largest number found (prices are usually the biggest numbers)
            prices = [int(n) for n in numbers if len(n) >= 4]  # At least 4 digits
            if prices:
                return str(max(prices))
        return ""
    
    def extract_mileage(self, text):
        """Extract mileage from text"""
        if not text:
            return ""
        # Look for numbers followed by km or miles
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
            'Porsche', 'Volvo', 'Land Rover', 'Range Rover', 'Jaguar', 'MINI',
            'Hyundai', 'Kia', 'Genesis',
            'Scion'
        }
        
        make_index = -1
        for i, word in enumerate(words):
            for make in all_makes:
                if word.lower() == make.lower():
                    result['make'] = make if make != 'Chevy' else 'Chevrolet'
                    make_index = i
                    break
            if make_index != -1:
                break
        
        if make_index != -1 and make_index + 1 < len(words):
            remaining_words = words[make_index + 1:]
            
            trim_indicators = {
                'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD',
                'LX', 'EX', 'EX-L', 'Touring', 'Sport', 'Type R',
                'S', 'SV', 'SL', 'SR', 'Nismo', 'Pro-4X',
                'LS', 'LT', 'LTZ', 'Premier', 'RS', 'SS', 'Denali',
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Raptor',
                'SXT', 'GT', 'R/T', 'Hellcat',
                'Hybrid', 'AWD', '4WD', 'FWD', '4x4', '4x2'
            }
            
            trim_start_index = len(remaining_words)
            for i, word in enumerate(remaining_words):
                if any(word.upper() == trim.upper() for trim in trim_indicators):
                    trim_start_index = i
                    break
            
            if trim_start_index > 0:
                result['model'] = ' '.join(remaining_words[:trim_start_index])
            else:
                result['model'] = ' '.join(remaining_words[:min(2, len(remaining_words))])
                trim_start_index = min(2, len(remaining_words))
            
            if trim_start_index < len(remaining_words):
                result['trim'] = ' '.join(remaining_words[trim_start_index:])
        
        return result
    
    def find_element_with_multiple_selectors(self, soup, selectors, extract_func=None):
        """Try multiple selectors and return first match"""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    match = re.search(r'([^:]+):contains\("([^"]+)"\)', selector)
                    if match:
                        tag = match.group(1)
                        text = match.group(2)
                        elements = soup.find_all(tag)
                        for elem in elements:
                            if text.lower() in elem.get_text().lower():
                                if extract_func:
                                    return extract_func(elem.get_text())
                                return self.clean_text(elem.get_text())
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text()
                        if extract_func:
                            return extract_func(text)
                        return self.clean_text(text)
            except Exception:
                continue
        return ""
    
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
        
        # Get all text content for searching
        page_text = soup.get_text()
        
        # Extract title - expanded selectors
        title_selectors = [
            'h1', 'h1.vehicle-title', 'h1.vdp-title', 'h1.title', 
            '.vehicle-info h1', '.vdp-header h1', '[data-vehicle-title]',
            '.inventory-title', '.vehicle-name', '.product-title'
        ]
        vehicle_data['title'] = self.find_element_with_multiple_selectors(soup, title_selectors)
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # Extract STOCK NUMBER with more patterns
        stock_patterns = [
            r'(?:Stock|Stk|Stock #|Stock Number)[:\s#]*([A-Z0-9-]+)',
            r'#\s*([A-Z0-9]{5,})',
            r'Stock:\s*([A-Z0-9-]+)'
        ]
        
        # Try dedicated stock elements
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'stock' in elem_text.lower():
                for pattern in stock_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['id / stock-#'] = match.group(1).strip()
                        break
                if vehicle_data['id / stock-#']:
                    break
        
        # Extract VIN with more patterns
        vin_patterns = [
            r'VIN[:\s]*([A-HJ-NPR-Z0-9]{17})',
            r'(?:^|\s)([A-HJ-NPR-Z0-9]{17})(?:\s|$)'
        ]
        
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'vin' in elem_text.lower() or len(elem_text.strip()) == 17:
                for pattern in vin_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['vin'] = match.group(1).upper()
                        break
                if vehicle_data['vin']:
                    break
        
        # Extract PRICE - multiple approaches
        price_found = False
        
        # Method 1: Look for price in common elements
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3']):
            elem_text = elem.get_text()
            if '$' in elem_text and not price_found:
                # Look for selling price indicators
                if any(keyword in elem_text.lower() for keyword in ['price', 'sale', 'cost', 'our price']):
                    price = self.extract_price(elem_text)
                    if price and int(price) > 1000:  # Reasonable vehicle price
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Method 2: Try specific selectors
        if not price_found:
            price_selectors = [
                '.price', '.selling-price', '.our-price', '.vehicle-price',
                '[data-price]', '#price', '.sale-price', '.internet-price',
                '.final-price', '.discounted-price'
            ]
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price = self.extract_price(elem.get_text())
                    if price and int(price) > 1000:
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Extract MSRP
        for elem in soup.find_all(['span', 'div', 'p', 'strong']):
            elem_text = elem.get_text()
            if 'msrp' in elem_text.lower() or 'retail' in elem_text.lower():
                msrp = self.extract_price(elem_text)
                if msrp and int(msrp) > 1000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
 in item['text']:
                    # Skip MSRP
                    if 'msrp' not in item['text'].lower() and 'retail' not in item['text'].lower():
                        price = self.extract_price(item['text'])
                        if price and int(price) > 5000:
                            vehicle_data['price'] = price
                            price_found = True
                            break
        
        # Method 3: Look for price in data attributes
        if not price_found:
            for elem in soup.find_all(attrs={'data-price': True}):
                price = self.extract_price(elem.get('data-price'))
                if price and int(price) > 5000:
                    vehicle_data['price'] = price
                    price_found = True
                    break
        
        # Method 4: Look for largest $ amount on page (excluding MSRP)
        if not price_found:
            all_prices = []
            for item in price_elements:
                if 'msrp' not in item['text'].lower() and 'retail' not in item['text'].lower():
                    price = self.extract_price(item['text'])
                    if price and int(price) > 5000:
                        all_prices.append(int(price))
            
            if all_prices:
                # Use the most common price if multiple, or the median
                from collections import Counter
                price_counts = Counter(all_prices)
                most_common_price = price_counts.most_common(1)[0][0]
                vehicle_data['price'] = str(most_common_price)
                price_found = True
        
        # Extract MSRP (Manufacturer's Suggested Retail Price)
        for item in price_elements:
            elem_text = item['text'].lower()
            
            if any(indicator in elem_text for indicator in [
                'msrp', 'manufacturer', 'retail', 'original price', 'list price'
            ]):
                msrp = self.extract_price(item['text'])
                if msrp and int(msrp) > 5000:
                    vehicle_data['vehicle MSRP'] = msrp
                    msrp_found = True
                    break
        
        # Extract ALL-IN PRICE (total price, drive away, out the door)
        for item in price_elements:
            elem_text = item['text'].lower()
            
            if any(indicator in elem_text for indicator in [
                'all-in', 'all in', 'total price', 'out the door', 'drive away', 
                'total cost', 'final cost', 'total amount'
            ]):
                all_in = self.extract_price(item['text'])
                if all_in and int(all_in) > 5000:
                    vehicle_data['vehicle all in price'] = all_in
                    all_in_price_found = True
                    break
        
        # Log what we found
        logger.info(f"  Prices - Sale: {vehicle_data['price']}, MSRP: {vehicle_data['vehicle MSRP']}, All-in: {vehicle_data['vehicle all in price']}")
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
, '').replace(',', '').strip()
        # Find the largest number (likely the price)
        numbers = re.findall(r'\d+', text)
        if numbers:
            # Return the largest number found (prices are usually the biggest numbers)
            prices = [int(n) for n in numbers if len(n) >= 4]  # At least 4 digits
            if prices:
                return str(max(prices))
        return ""
    
    def extract_mileage(self, text):
        """Extract mileage from text"""
        if not text:
            return ""
        # Look for numbers followed by km or miles
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
            'Porsche', 'Volvo', 'Land Rover', 'Range Rover', 'Jaguar', 'MINI',
            'Hyundai', 'Kia', 'Genesis',
            'Scion'
        }
        
        make_index = -1
        for i, word in enumerate(words):
            for make in all_makes:
                if word.lower() == make.lower():
                    result['make'] = make if make != 'Chevy' else 'Chevrolet'
                    make_index = i
                    break
            if make_index != -1:
                break
        
        if make_index != -1 and make_index + 1 < len(words):
            remaining_words = words[make_index + 1:]
            
            trim_indicators = {
                'LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD',
                'LX', 'EX', 'EX-L', 'Touring', 'Sport', 'Type R',
                'S', 'SV', 'SL', 'SR', 'Nismo', 'Pro-4X',
                'LS', 'LT', 'LTZ', 'Premier', 'RS', 'SS', 'Denali',
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Raptor',
                'SXT', 'GT', 'R/T', 'Hellcat',
                'Hybrid', 'AWD', '4WD', 'FWD', '4x4', '4x2'
            }
            
            trim_start_index = len(remaining_words)
            for i, word in enumerate(remaining_words):
                if any(word.upper() == trim.upper() for trim in trim_indicators):
                    trim_start_index = i
                    break
            
            if trim_start_index > 0:
                result['model'] = ' '.join(remaining_words[:trim_start_index])
            else:
                result['model'] = ' '.join(remaining_words[:min(2, len(remaining_words))])
                trim_start_index = min(2, len(remaining_words))
            
            if trim_start_index < len(remaining_words):
                result['trim'] = ' '.join(remaining_words[trim_start_index:])
        
        return result
    
    def find_element_with_multiple_selectors(self, soup, selectors, extract_func=None):
        """Try multiple selectors and return first match"""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    match = re.search(r'([^:]+):contains\("([^"]+)"\)', selector)
                    if match:
                        tag = match.group(1)
                        text = match.group(2)
                        elements = soup.find_all(tag)
                        for elem in elements:
                            if text.lower() in elem.get_text().lower():
                                if extract_func:
                                    return extract_func(elem.get_text())
                                return self.clean_text(elem.get_text())
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text()
                        if extract_func:
                            return extract_func(text)
                        return self.clean_text(text)
            except Exception:
                continue
        return ""
    
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
        
        # Get all text content for searching
        page_text = soup.get_text()
        
        # Extract title - expanded selectors
        title_selectors = [
            'h1', 'h1.vehicle-title', 'h1.vdp-title', 'h1.title', 
            '.vehicle-info h1', '.vdp-header h1', '[data-vehicle-title]',
            '.inventory-title', '.vehicle-name', '.product-title'
        ]
        vehicle_data['title'] = self.find_element_with_multiple_selectors(soup, title_selectors)
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # Extract STOCK NUMBER with more patterns
        stock_patterns = [
            r'(?:Stock|Stk|Stock #|Stock Number)[:\s#]*([A-Z0-9-]+)',
            r'#\s*([A-Z0-9]{5,})',
            r'Stock:\s*([A-Z0-9-]+)'
        ]
        
        # Try dedicated stock elements
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'stock' in elem_text.lower():
                for pattern in stock_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['id / stock-#'] = match.group(1).strip()
                        break
                if vehicle_data['id / stock-#']:
                    break
        
        # Extract VIN with more patterns
        vin_patterns = [
            r'VIN[:\s]*([A-HJ-NPR-Z0-9]{17})',
            r'(?:^|\s)([A-HJ-NPR-Z0-9]{17})(?:\s|$)'
        ]
        
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'vin' in elem_text.lower() or len(elem_text.strip()) == 17:
                for pattern in vin_patterns:
                    match = re.search(pattern, elem_text, re.IGNORECASE)
                    if match:
                        vehicle_data['vin'] = match.group(1).upper()
                        break
                if vehicle_data['vin']:
                    break
        
        # Extract PRICE - multiple approaches
        price_found = False
        
        # Method 1: Look for price in common elements
        for elem in soup.find_all(['span', 'div', 'p', 'strong', 'h2', 'h3']):
            elem_text = elem.get_text()
            if '$' in elem_text and not price_found:
                # Look for selling price indicators
                if any(keyword in elem_text.lower() for keyword in ['price', 'sale', 'cost', 'our price']):
                    price = self.extract_price(elem_text)
                    if price and int(price) > 1000:  # Reasonable vehicle price
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Method 2: Try specific selectors
        if not price_found:
            price_selectors = [
                '.price', '.selling-price', '.our-price', '.vehicle-price',
                '[data-price]', '#price', '.sale-price', '.internet-price',
                '.final-price', '.discounted-price'
            ]
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price = self.extract_price(elem.get_text())
                    if price and int(price) > 1000:
                        vehicle_data['price'] = price
                        price_found = True
                        break
        
        # Extract MSRP
        for elem in soup.find_all(['span', 'div', 'p', 'strong']):
            elem_text = elem.get_text()
            if 'msrp' in elem_text.lower() or 'retail' in elem_text.lower():
                msrp = self.extract_price(elem_text)
                if msrp and int(msrp) > 1000:
                    vehicle_data['vehicle MSRP'] = msrp
                    break
        
        # Extract MILEAGE - enhanced
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            elem_text = elem.get_text()
            if 'km' in elem_text.lower() or 'mileage' in elem_text.lower() or 'odometer' in elem_text.lower():
                mileage = self.extract_mileage(elem_text)
                if mileage:
                    vehicle_data['mileage'] = mileage
                    break
        
        # Determine CONDITION from URL or page content
        if '/inventory/new/' in url or '/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url or '/used/' in url:
            vehicle_data['condition'] = 'used'
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                vehicle_data['condition'] = 'new'
            elif 'used vehicle' in page_text.lower() or 'pre-owned' in page_text.lower():
                vehicle_data['condition'] = 'used'
        
        # Extract COLOR - enhanced
        color_keywords = ['exterior', 'color', 'colour', 'paint']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in color_keywords):
                # Extract color value
                color_text = self.clean_text(elem_text)
                # Remove label text
                color_text = re.sub(r'(?i)(exterior|color|colour|paint)[:\s]*', '', color_text)
                if color_text and len(color_text) < 50:  # Reasonable color name length
                    vehicle_data['color'] = color_text
                    break
        
        # Extract ENGINE
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if 'engine' in elem_text.lower() and len(elem_text) < 200:
                engine_text = self.clean_text(elem_text)
                engine_text = re.sub(r'(?i)engine[:\s]*', '', engine_text)
                if engine_text and len(engine_text) > 3:
                    vehicle_data['engine'] = engine_text
                    break
        
        # Extract BODY STYLE
        body_keywords = ['body', 'body style', 'type', 'vehicle type']
        for elem in soup.find_all(['span', 'div', 'p', 'li', 'td', 'dt', 'dd']):
            elem_text = elem.get_text()
            if any(keyword in elem_text.lower() for keyword in body_keywords):
                body_text = self.clean_text(elem_text)
                body_text = re.sub(r'(?i)(body|body style|type|vehicle type)[:\s]*', '', body_text)
                # Check if it's a valid body style
                valid_body_styles = ['sedan', 'suv', 'truck', 'coupe', 'hatchback', 'wagon', 
                                     'van', 'minivan', 'convertible', 'crossover', 'pickup']
                if any(style in body_text.lower() for style in valid_body_styles):
                    vehicle_data['body style'] = body_text
                    break
        
        # Extract IMAGE - expanded search
        img_found = False
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src and not img_found:
                # Skip small images, icons, logos
                if any(skip in src.lower() for skip in ['icon', 'logo', 'thumbnail', 'btn', 'button']):
                    continue
                # Look for vehicle images
                if any(indicator in src.lower() for indicator in ['vehicle', 'inventory', 'stock', 'auto', 'car']):
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    img_found = True
                    break
        
        # If no specific vehicle image found, take first large image
        if not img_found:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    vehicle_data['image link'] = urljoin(self.base_url, src)
                    break
        
        # Extract DESCRIPTION
        desc_keywords = ['description', 'overview', 'details', 'about', 'comments']
        for elem in soup.find_all(['div', 'p', 'section']):
            if any(keyword in elem.get('class', []) + [elem.get('id', '')] for keyword in desc_keywords):
                desc_text = self.clean_text(elem.get_text())
                if len(desc_text) > 50 and len(desc_text) < 2000:  # Reasonable description length
                    vehicle_data['description'] = desc_text
                    break
        
        # Extract FEATURES/OPTIONS - look for lists
        options = []
        for ul in soup.find_all(['ul', 'ol']):
            list_text = ul.get_text().lower()
            if any(keyword in list_text for keyword in ['feature', 'option', 'equipment', 'include']):
                for li in ul.find_all('li'):
                    option_text = self.clean_text(li.get_text())
                    if option_text and len(option_text) < 100:
                        options.append(option_text)
        
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:100])  # Limit to first 100 options
        
        # Check for CERTIFIED PRE-OWNED
        cpo_keywords = ['certified', 'cpo', 'certified pre-owned', 'certified used']
        if any(keyword in page_text.lower() for keyword in cpo_keywords):
            vehicle_data['certified pre-owned'] = 'yes'
        
        # Try to extract from JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Car', 'Vehicle', 'Product']:
                    # Fill in missing data from structured data
                    if not vehicle_data['brand'] and data.get('brand'):
                        vehicle_data['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
                    if not vehicle_data['model'] and data.get('model'):
                        vehicle_data['model'] = data['model']
                    if not vehicle_data['year'] and data.get('modelDate'):
                        vehicle_data['year'] = self.extract_year(str(data['modelDate']))
                    if not vehicle_data['vin'] and data.get('vehicleIdentificationNumber'):
                        vehicle_data['vin'] = data['vehicleIdentificationNumber']
                    if not vehicle_data['color'] and data.get('color'):
                        vehicle_data['color'] = data['color']
                    if not vehicle_data['mileage'] and data.get('mileageFromOdometer'):
                        vehicle_data['mileage'] = str(data['mileageFromOdometer'].get('value', ''))
                    if not vehicle_data['price'] and data.get('offers'):
                        offers = data['offers']
                        if isinstance(offers, dict):
                            vehicle_data['price'] = str(offers.get('price', ''))
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
