import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class UniversalVehicleScraper:
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
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
            if href and '/inventory/' in href:
                if not any(x in href for x in ['?page=', '/new/', '/used/']):
                    if len(href.split('/')) > 4:
                        full_url = urljoin(self.base_url, href)
                        if '?' not in full_url:
                            links.add(full_url)
        return list(links)
    
    def clean_text(self, text):
        if not text:
            return ""
        return ' '.join(text.strip().split())
    
    def scrape_vehicle_detail(self, url):
        logger.info(f"\n{'='*100}")
        logger.info(f"SCRAPING: {url}")
        logger.info(f"{'='*100}")
        
        soup = self.get_page(url)
        if not soup:
            return None
        
        # Initialize data
        data = {
            'title': '', 'id / stock-#': '', 'price': '', 'condition': '',
            'feed label': '', 'body style': '', 'brand': '', 'certified pre-owned': '',
            'color': '', 'description': '', 'engine': '', 'image link': '',
            'link': url, 'mileage': '', 'model': '', 'trim / sub-model': '',
            'vehicle MSRP': '', 'vehicle all in price': '', 'vehicle option': '',
            'vin': '', 'year': ''
        }
        
        page_html = str(soup)
        page_text = soup.get_text()
        
        # ===== 1. TITLE =====
        logger.info("\n[TITLE]")
        title_elem = soup.find('h1')
        if title_elem:
            data['title'] = self.clean_text(title_elem.get_text())
            logger.info(f"  ✓ {data['title']}")
        
        # ===== 2. PARSE YEAR, MAKE, MODEL, TRIM FROM TITLE =====
        logger.info("\n[PARSING TITLE]")
        title = data['title']
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', title)
        if year_match:
            data['year'] = year_match.group(1)
            logger.info(f"  ✓ Year: {data['year']}")
        
        # Extract make
        makes = ['Toyota', 'Lexus', 'Honda', 'Acura', 'Nissan', 'Infiniti', 'Mazda', 'Subaru',
                'Ford', 'Chevrolet', 'GMC', 'Dodge', 'Ram', 'Jeep', 'Chrysler', 'Hyundai',
                'Kia', 'Volkswagen', 'Audi', 'BMW', 'Mercedes', 'Mercedes-Benz', 'Land Rover',
                'Range Rover', 'Porsche', 'Volvo', 'Jaguar', 'Alfa Romeo', 'Maserati']
        
        for make in makes:
            if make.lower() in title.lower():
                data['brand'] = make
                logger.info(f"  ✓ Make: {data['brand']}")
                break
        
        # Extract model and trim
        title_parts = title.split()
        year_idx = -1
        make_idx = -1
        
        for i, part in enumerate(title_parts):
            if part == data['year']:
                year_idx = i
            if data['brand'] and part.lower() in data['brand'].lower():
                make_idx = i
        
        if make_idx >= 0 and make_idx + 1 < len(title_parts):
            remaining = title_parts[make_idx + 1:]
            
            # Common trim indicators
            trim_words = ['LE', 'SE', 'XLE', 'XSE', 'Limited', 'Platinum', 'SR5', 'TRD',
                         'LX', 'EX', 'Touring', 'Sport', 'Hybrid', 'AWD', '4WD', 'FWD',
                         'North', 'Progressiv', 'Comfortline', 'Dynamic', 'HSE', 'Premium',
                         'Upgrade', 'Technology', 'Off-Road', 'Pro', 'Trail', 'Adventure',
                         'Nightshade', 'Black Diamond', 'A-Spec', 'Type R', 'Si', 'Nismo']
            
            # Find where trim starts
            trim_start = len(remaining)
            for i, word in enumerate(remaining):
                if word in trim_words:
                    trim_start = i
                    break
            
            # Everything before trim is model
            if trim_start > 0:
                # Check for multi-word models
                if trim_start >= 2:
                    two_word = f"{remaining[0]} {remaining[1]}"
                    if two_word in ['Grand Highlander', 'Crown Signia', 'Grand Cherokee', 
                                   'Range Rover', 'Land Cruiser', 'Santa Fe']:
                        data['model'] = two_word
                        data['trim / sub-model'] = ' '.join(remaining[2:]) if len(remaining) > 2 else ''
                    else:
                        data['model'] = remaining[0]
                        data['trim / sub-model'] = ' '.join(remaining[1:])
                else:
                    data['model'] = remaining[0]
                    data['trim / sub-model'] = ' '.join(remaining[1:])
            else:
                # No trim found
                data['model'] = ' '.join(remaining[:2]) if len(remaining) >= 2 else remaining[0] if remaining else ''
        
        logger.info(f"  ✓ Model: {data['model']}")
        logger.info(f"  ✓ Trim: {data['trim / sub-model']}")
        
        # ===== 3. CONDITION =====
        logger.info("\n[CONDITION]")
        if '/new/' in url or '/inventory/new/' in url:
            data['condition'] = 'new'
            logger.info(f"  ✓ new (from URL)")
        elif '/used/' in url or '/inventory/used/' in url:
            data['condition'] = 'used'
            logger.info(f"  ✓ used (from URL)")
        else:
            # Check page content
            if 'new vehicle' in page_text.lower() or 'brand new' in page_text.lower():
                data['condition'] = 'new'
                logger.info(f"  ✓ new (from content)")
            elif 'used vehicle' in page_text.lower() or 'pre-owned vehicle' in page_text.lower():
                data['condition'] = 'used'
                logger.info(f"  ✓ used (from content)")
        
        # ===== 4. STOCK NUMBER =====
        logger.info("\n[STOCK NUMBER]")
        # Try multiple patterns
        stock_patterns = [
            (r'Stock\s*#?\s*:?\s*([A-Z0-9-]+)', 'Stock #'),
            (r'Stock\s+Number\s*:?\s*([A-Z0-9-]+)', 'Stock Number'),
            (r'Stk\s*#?\s*:?\s*([A-Z0-9-]+)', 'Stk #'),
        ]
        
        for pattern, label in stock_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                data['id / stock-#'] = match.group(1).strip()
                logger.info(f"  ✓ {data['id / stock-#']} (via {label})")
                break
        
        # ===== 5. VIN =====
        logger.info("\n[VIN]")
        vin_match = re.search(r'\bVIN\s*:?\s*([A-HJ-NPR-Z0-9]{17})\b', page_text, re.IGNORECASE)
        if vin_match:
            data['vin'] = vin_match.group(1).upper()
            logger.info(f"  ✓ {data['vin']}")
        else:
            # Try finding 17-char VIN without label
            vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', page_text)
            if vin_match:
                data['vin'] = vin_match.group(1).upper()
                logger.info(f"  ✓ {data['vin']} (found without label)")
        
        # ===== 6. PRICES =====
        logger.info("\n[PRICES]")
        
        # Find all elements with dollar signs
        price_elements = []
        for elem in soup.find_all(text=re.compile(r'\$[\d,]+')):
            parent = elem.parent
            text = self.clean_text(parent.get_text())
            if text and len(text) < 200:
                price_elements.append(text)
        
        logger.info(f"  Found {len(price_elements)} price elements")
        
        # Extract selling price (not MSRP)
        for price_text in price_elements:
            if 'msrp' not in price_text.lower() and 'retail' not in price_text.lower():
                numbers = re.findall(r'\$?([\d,]+)', price_text.replace(',', ''))
                for num in numbers:
                    if len(num) >= 5:
                        data['price'] = num
                        logger.info(f"  ✓ Selling Price: ${num}")
                        break
                if data['price']:
                    break
        
        # Extract MSRP
        for price_text in price_elements:
            if 'msrp' in price_text.lower() or 'retail' in price_text.lower():
                numbers = re.findall(r'\$?([\d,]+)', price_text.replace(',', ''))
                for num in numbers:
                    if len(num) >= 5:
                        data['vehicle MSRP'] = num
                        logger.info(f"  ✓ MSRP: ${num}")
                        break
                if data['vehicle MSRP']:
                    break
        
        # Extract All-In Price
        for price_text in price_elements:
            if any(kw in price_text.lower() for kw in ['all-in', 'all in', 'total', 'out the door']):
                numbers = re.findall(r'\$?([\d,]+)', price_text.replace(',', ''))
                for num in numbers:
                    if len(num) >= 5:
                        data['vehicle all in price'] = num
                        logger.info(f"  ✓ All-In: ${num}")
                        break
                if data['vehicle all in price']:
                    break
        
        # ===== 7. MILEAGE =====
        logger.info("\n[MILEAGE]")
        mileage_match = re.search(r'([\d,]+)\s*(?:km|KM|Km)', page_text)
        if mileage_match:
            data['mileage'] = mileage_match.group(1).replace(',', '')
            logger.info(f"  ✓ {data['mileage']} km")
        
        # ===== 8. COLOR =====
        logger.info("\n[COLOR]")
        color_patterns = [
            r'Exterior\s*:?\s*([A-Za-z\s]+?)(?:\n|,|$)',
            r'Color\s*:?\s*([A-Za-z\s]+?)(?:\n|,|$)',
            r'Colour\s*:?\s*([A-Za-z\s]+?)(?:\n|,|$)',
        ]
        
        for pattern in color_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                color = match.group(1).strip()
                if len(color) < 50 and len(color) > 2:
                    data['color'] = color
                    logger.info(f"  ✓ {color}")
                    break
        
        # ===== 9. ENGINE =====
        logger.info("\n[ENGINE]")
        engine_match = re.search(r'Engine\s*:?\s*([^\n]{10,100})', page_text, re.IGNORECASE)
        if engine_match:
            data['engine'] = self.clean_text(engine_match.group(1))
            logger.info(f"  ✓ {data['engine']}")
        
        # ===== 10. BODY STYLE =====
        logger.info("\n[BODY STYLE]")
        
        # Try to find explicit body style
        body_match = re.search(r'Body\s*(?:Style|Type)?\s*:?\s*([A-Za-z\s]+?)(?:\n|,|$)', page_text, re.IGNORECASE)
        if body_match:
            data['body style'] = self.clean_text(body_match.group(1))
            logger.info(f"  ✓ {data['body style']} (explicit)")
        else:
            # Infer from model
            model_lower = data['model'].lower()
            if any(x in model_lower for x in ['tundra', 'tacoma', 'f-150', 'silverado', 'ram', 'frontier', 'ranger']):
                data['body style'] = 'Pickup Truck'
            elif any(x in model_lower for x in ['rav4', 'highlander', 'escape', 'cr-v', '4runner', 'pilot', 'explorer', 'tucson', 'santa fe', 'cx-5', 'outback', 'forester']):
                data['body style'] = 'SUV'
            elif any(x in model_lower for x in ['camry', 'corolla', 'accord', 'civic', 'altima', 'sentra', 'elantra', 'sonata', 'mazda3', 'mazda6']):
                data['body style'] = 'Sedan'
            elif any(x in model_lower for x in ['sienna', 'pacifica', 'odyssey', 'caravan']):
                data['body style'] = 'Minivan'
            elif any(x in model_lower for x in ['bronco', 'wrangler', '4runner']):
                data['body style'] = 'SUV'
            
            if data['body style']:
                logger.info(f"  ✓ {data['body style']} (inferred from model)")
        
        # ===== 11. DESCRIPTION =====
        logger.info("\n[DESCRIPTION]")
        
        # Look for description in common containers
        desc_found = False
        for elem in soup.find_all(['div', 'section', 'p']):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            
            if any(kw in classes or kw in elem_id for kw in ['description', 'overview', 'details', 'comments', 'about']):
                text = self.clean_text(elem.get_text())
                if len(text) > 100 and len(text) < 5000:
                    data['description'] = text
                    logger.info(f"  ✓ Found ({len(text)} chars)")
                    desc_found = True
                    break
        
        if not desc_found:
            logger.info(f"  ⚠ Not found")
        
        # ===== 12. VEHICLE OPTIONS/FEATURES =====
        logger.info("\n[VEHICLE OPTIONS]")
        
        options = []
        # Method 1: Look for unordered/ordered lists
        for ul in soup.find_all(['ul', 'ol']):
            parent = ul.find_parent(['div', 'section'])
            if parent:
                parent_text = parent.get_text()[:300].lower()
                if any(kw in parent_text for kw in ['feature', 'option', 'equipment', 'include', 'standard', 'package']):
                    for li in ul.find_all('li'):
                        opt = self.clean_text(li.get_text())
                        if opt and 3 < len(opt) < 150:
                            options.append(opt)
        
        # Method 2: Look for definition lists
        if not options:
            for dl in soup.find_all('dl'):
                for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                    opt = f"{self.clean_text(dt.get_text())}: {self.clean_text(dd.get_text())}"
                    if len(opt) < 150:
                        options.append(opt)
        
        if options:
            data['vehicle option'] = '; '.join(options[:100])
            logger.info(f"  ✓ Found {len(options)} options")
        else:
            logger.info(f"  ⚠ Not found")
        
        # ===== 13. CERTIFIED PRE-OWNED =====
        logger.info("\n[CERTIFIED PRE-OWNED]")
        
        if re.search(r'certified\s+pre-owned', page_text, re.IGNORECASE):
            data['certified pre-owned'] = 'yes'
            logger.info(f"  ✓ Yes")
        elif re.search(r'\bCPO\b', page_text):
            data['certified pre-owned'] = 'yes'
            logger.info(f"  ✓ Yes (CPO)")
        else:
            logger.info(f"  ✓ No")
        
        # ===== 14. IMAGE =====
        logger.info("\n[IMAGE]")
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy')
            if src:
                if not any(skip in src.lower() for skip in ['logo', 'icon', 'badge', 'button']):
                    data['image link'] = urljoin(self.base_url, src)
                    logger.info(f"  ✓ Found")
                    break
        
        # ===== SUMMARY =====
        logger.info(f"\n{'='*100}")
        logger.info("SUMMARY:")
        logger.info(f"  Title: {data['title']}")
        logger.info(f"  Year/Make/Model: {data['year']} {data['brand']} {data['model']} {data['trim / sub-model']}")
        logger.info(f"  Stock: {data['id / stock-#']} | VIN: {data['vin']}")
        logger.info(f"  Price: ${data['price']} | MSRP: ${data['vehicle MSRP']}")
        logger.info(f"  Condition: {data['condition']} | Body: {data['body style']}")
        logger.info(f"  Mileage: {data['mileage']} | Color: {data['color']}")
        logger.info(f"  Description: {'✓' if data['description'] else '✗'}")
        logger.info(f"  Options: {'✓' if data['vehicle option'] else '✗'}")
        logger.info(f"  CPO: {data['certified pre-owned']}")
        logger.info(f"{'='*100}\n")
        
        return data
    
    def scrape_inventory_pages(self, urls):
        all_vehicles = []
        all_links = set()
        
        logger.info("\n" + "="*100)
        logger.info("COLLECTING VEHICLE LINKS")
        logger.info("="*100)
        
        for url in urls:
            logger.info(f"\nScanning: {url}")
            soup = self.get_page(url)
            if soup:
                links = self.extract_vehicle_links(soup)
                all_links.update(links)
                logger.info(f"  Found {len(links)} vehicles")
            time.sleep(1)
        
        logger.info(f"\n{'='*100}")
        logger.info(f"TOTAL UNIQUE VEHICLES: {len(all_links)}")
        logger.info(f"{'='*100}\n")
        
        for i, vdp_url in enumerate(sorted(all_links), 1):
            logger.info(f"\nPROGRESS: {i}/{len(all_links)}")
            vehicle = self.scrape_vehicle_detail(vdp_url)
            if vehicle:
                all_vehicles.append(vehicle)
            time.sleep(1)
        
        return all_vehicles
