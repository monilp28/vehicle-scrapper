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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        cleaned = re.sub(r'^(Stock|VIN|Price|MSRP|Mileage|Year|Make|Model|Trim|Color|Engine):\s*', '', cleaned, flags=re.IGNORECASE)
        return cleaned
    
    def extract_price(self, text):
        """Extract price from text"""
        if not text:
            return ""
        price_match = re.search(r'\$?\s*([\d,]+)', text.replace(',', ''))
        if price_match:
            return price_match.group(1)
        return ""
    
    def extract_mileage(self, text):
        """Extract mileage from text"""
        if not text:
            return ""
        mileage_match = re.search(r'([\d,]+)\s*(?:km|miles?)', text, re.IGNORECASE)
        if mileage_match:
            return mileage_match.group(1).replace(',', '')
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
                'S', 'SV', 'SL', 'SR', 'Nismo',
                'LS', 'LT', 'LTZ', 'Premier', 'RS', 'SS',
                'XL', 'XLT', 'Lariat', 'King Ranch', 'Raptor',
                'SXT', 'GT', 'R/T', 'Hellcat',
                'Hybrid', 'AWD', '4WD'
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
        
        # Extract title
        title_selectors = ['h1.vehicle-title', 'h1.vdp-title', 'h1.title', 'h1']
        vehicle_data['title'] = self.find_element_with_multiple_selectors(soup, title_selectors)
        
        # Parse title
        parsed = self.parse_vehicle_title(vehicle_data['title'])
        vehicle_data['year'] = parsed['year']
        vehicle_data['brand'] = parsed['make']
        vehicle_data['model'] = parsed['model']
        vehicle_data['trim / sub-model'] = parsed['trim']
        
        # Extract other fields
        stock_selectors = ['[data-stock]', 'span.stock-number', 'span:contains("Stock")']
        stock_text = self.find_element_with_multiple_selectors(soup, stock_selectors)
        if stock_text:
            stock_match = re.search(r'(?:Stock|#)\s*[:#]?\s*([A-Z0-9-]+)', stock_text, re.IGNORECASE)
            if stock_match:
                vehicle_data['id / stock-#'] = stock_match.group(1)
        
        vin_selectors = ['[data-vin]', 'span.vin', 'span:contains("VIN")']
        vin_text = self.find_element_with_multiple_selectors(soup, vin_selectors)
        if vin_text:
            vin_match = re.search(r'(?:VIN[:\s]*)?([A-HJ-NPR-Z0-9]{17})', vin_text, re.IGNORECASE)
            if vin_match:
                vehicle_data['vin'] = vin_match.group(1).upper()
        
        price_selectors = ['[data-price]', 'span.price', '.vehicle-price']
        vehicle_data['price'] = self.find_element_with_multiple_selectors(soup, price_selectors, self.extract_price)
        
        msrp_selectors = ['[data-msrp]', 'span.msrp', 'span:contains("MSRP")']
        vehicle_data['vehicle MSRP'] = self.find_element_with_multiple_selectors(soup, msrp_selectors, self.extract_price)
        
        mileage_selectors = ['[data-mileage]', 'span.mileage', 'span:contains("km")']
        vehicle_data['mileage'] = self.find_element_with_multiple_selectors(soup, mileage_selectors, self.extract_mileage)
        
        if '/inventory/new/' in url:
            vehicle_data['condition'] = 'new'
        elif '/inventory/used/' in url:
            vehicle_data['condition'] = 'used'
        
        color_selectors = ['[data-exterior-color]', 'span.exterior-color', 'span:contains("Exterior")']
        color_text = self.find_element_with_multiple_selectors(soup, color_selectors)
        if color_text:
            vehicle_data['color'] = re.sub(r'(Exterior|Color|:)', '', color_text, flags=re.IGNORECASE).strip()
        
        engine_selectors = ['[data-engine]', 'span.engine', 'span:contains("Engine")']
        vehicle_data['engine'] = self.find_element_with_multiple_selectors(soup, engine_selectors)
        
        body_selectors = ['[data-body-style]', 'span.body-style', 'span:contains("Body")']
        vehicle_data['body style'] = self.find_element_with_multiple_selectors(soup, body_selectors)
        
        img_selectors = ['img.vehicle-image', '.gallery img', '.vdp-image img']
        for selector in img_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src')
                if img_src:
                    vehicle_data['image link'] = urljoin(self.base_url, img_src)
                    break
        
        desc_selectors = ['.vehicle-description', '.description']
        vehicle_data['description'] = self.find_element_with_multiple_selectors(soup, desc_selectors)
        
        # Extract features
        options = []
        for selector in ['.features li', '.options li', '.vehicle-features li']:
            feature_elems = soup.select(selector)
            if feature_elems:
                options = [self.clean_text(f.get_text()) for f in feature_elems]
                break
        if options:
            vehicle_data['vehicle option'] = '; '.join(options[:50])
        
        page_text = soup.get_text().lower()
        if 'certified pre-owned' in page_text or 'cpo' in page_text:
            vehicle_data['certified pre-owned'] = 'yes'
        
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
