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
    def __init__(self):
        self.base_url = "https://www.reddeertoyota.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_page(self, url):
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def extract_links(self, soup):
        links = set()
        all_hrefs = []
        
        # Collect all links
        for a in soup.find_all('a', href=True):
            href = a['href']
            all_hrefs.append(href)
            
            # Look for vehicle inventory links - be very permissive
            if '/inventory/' in href:
                full_url = urljoin(self.base_url, href)
                
                # Exclude category pages and pagination
                if not any(full_url.endswith(x) for x in ['/new/', '/used/', '/new', '/used']):
                    if '?page=' not in full_url and '?sort=' not in full_url:
                        # This should be a vehicle page
                        links.add(full_url)
        
        # Debug: show what we found
        logger.info(f"  Total <a> tags found: {len(all_hrefs)}")
        logger.info(f"  Links with /inventory/: {len([h for h in all_hrefs if '/inventory/' in h])}")
        if len(links) == 0:
            logger.info(f"  Sample hrefs:")
            for href in all_hrefs[:10]:
                logger.info(f"    - {href}")
        
        return list(links)
    
    def clean(self, text):
        return ' '.join(str(text).strip().split()) if text else ""
    
    def get_all_text_blocks(self, soup):
        """Get all meaningful text blocks from the page"""
        blocks = []
        for elem in soup.find_all(['p', 'div', 'span', 'li', 'td', 'dd', 'dt']):
            text = self.clean(elem.get_text())
            if text and 5 < len(text) < 500:
                blocks.append({
                    'text': text,
                    'tag': elem.name,
                    'class': ' '.join(elem.get('class', [])),
                    'id': elem.get('id', '')
                })
        return blocks
    
    def extract_number(self, text, min_digits=4):
        """Extract largest number from text"""
        nums = re.findall(r'\d+', text.replace(',', ''))
        valid = [int(n) for n in nums if len(n) >= min_digits]
        return str(max(valid)) if valid else ""
    
    def scrape_vehicle(self, url):
        logger.info(f"\n{'='*120}")
        logger.info(f"URL: {url}")
        logger.info(f"{'='*120}")
        
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
        
        # Get all text from page
        page_text = soup.get_text()
        blocks = self.get_all_text_blocks(soup)
        
        # === TITLE ===
        h1 = soup.find('h1')
        if h1:
            data['title'] = self.clean(h1.get_text())
            logger.info(f"\n[TITLE] {data['title']}")
        
        # === YEAR ===
        year_match = re.search(r'\b(202[3-9]|20[3-9]\d)\b', data['title'])
        if year_match:
            data['year'] = year_match.group(1)
        
        # === MAKE/BRAND ===
        makes = ['Toyota', 'Lexus', 'Honda', 'Acura', 'Nissan', 'Mazda', 'Ford', 
                'Chevrolet', 'GMC', 'Dodge', 'Ram', 'Jeep', 'Chrysler', 'Hyundai',
                'Kia', 'Subaru', 'Volkswagen', 'Audi', 'BMW', 'Mercedes-Benz',
                'Land Rover', 'Range Rover', 'Porsche', 'Volvo']
        
        for make in makes:
            if make.lower() in data['title'].lower():
                data['brand'] = make
                break
        
        # === MODEL & TRIM ===
        # Remove year and make from title
        title_clean = data['title']
        if data['year']:
            title_clean = title_clean.replace(data['year'], '')
        if data['brand']:
            title_clean = title_clean.replace(data['brand'], '')
        
        parts = title_clean.strip().split()
        
        # Known multi-word models
        multi_models = ['Grand Highlander', 'Crown Signia', 'Land Cruiser', 
                       'Grand Cherokee', 'Range Rover', 'Santa Fe']
        
        model_found = False
        for mm in multi_models:
            if mm.lower() in title_clean.lower():
                data['model'] = mm
                title_clean = title_clean.replace(mm, '')
                model_found = True
                break
        
        if not model_found and parts:
            # First word is usually the model
            data['model'] = parts[0]
            parts = parts[1:]
        
        # Everything else is trim
        data['trim / sub-model'] = ' '.join(parts).strip()
        
        logger.info(f"[VEHICLE] {data['year']} {data['brand']} {data['model']} {data['trim / sub-model']}")
        
        # === CONDITION ===
        # Check URL
        url_lower = url.lower()
        if '/inventory/new/' in url_lower:
            data['condition'] = 'new'
            logger.info(f"[CONDITION] new (from URL)")
        elif '/inventory/used/' in url_lower:
            data['condition'] = 'used'
            logger.info(f"[CONDITION] used (from URL)")
        else:
            # Check page text
            page_lower = page_text.lower()
            # Look for "New Vehicle" or "Used Vehicle" badges
            if re.search(r'\bnew\s+vehicle\b', page_lower):
                data['condition'] = 'new'
                logger.info(f"[CONDITION] new (from page)")
            elif re.search(r'\b(used|pre-owned)\s+vehicle\b', page_lower):
                data['condition'] = 'used'
                logger.info(f"[CONDITION] used (from page)")
            else:
                # Check if mileage exists (used) or not (new)
                if re.search(r'\d+\s*km', page_lower):
                    data['condition'] = 'used'
                    logger.info(f"[CONDITION] used (has mileage)")
                else:
                    data['condition'] = 'new'
                    logger.info(f"[CONDITION] new (no mileage)")
        
        # === STOCK NUMBER ===
        for block in blocks:
            if 'stock' in block['text'].lower():
                match = re.search(r'(?:stock|stk)\s*#?\s*:?\s*([A-Z0-9-]+)', block['text'], re.I)
                if match:
                    data['id / stock-#'] = match.group(1)
                    logger.info(f"[STOCK] {data['id / stock-#']}")
                    break
        
        # === VIN ===
        vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', page_text)
        if vin_match:
            data['vin'] = vin_match.group(1).upper()
            logger.info(f"[VIN] {data['vin']}")
        
        # === PRICES - CRITICAL SECTION ===
        logger.info(f"\n[PRICE EXTRACTION]")
        
        # Collect ALL dollar amounts with context
        price_candidates = []
        for block in blocks:
            if '$' in block['text']:
                # Extract all numbers with $
                amounts = re.findall(r'\$\s*([\d,]+)', block['text'])
                for amount in amounts:
                    num = amount.replace(',', '')
                    if len(num) >= 4:  # At least $1000
                        price_candidates.append({
                            'amount': num,
                            'context': block['text'].lower(),
                            'full_text': block['text']
                        })
        
        logger.info(f"  Found {len(price_candidates)} price candidates")
        
        # Display first 10 for debugging
        for i, pc in enumerate(price_candidates[:10], 1):
            logger.info(f"    {i}. ${pc['amount']} - {pc['full_text'][:70]}")
        
        # Extract SELLING PRICE (not MSRP, not total)
        for pc in price_candidates:
            ctx = pc['context']
            # Skip MSRP
            if any(word in ctx for word in ['msrp', 'manufacturer', 'retail', 'original']):
                continue
            # Skip totals/taxes
            if any(word in ctx for word in ['total', 'tax', 'fee', 'after']):
                continue
            # This is likely the selling price
            if int(pc['amount']) > 10000:  # Reasonable car price
                data['price'] = pc['amount']
                logger.info(f"  ✓ SELLING PRICE: ${pc['amount']}")
                logger.info(f"    Context: {pc['full_text'][:100]}")
                break
        
        # Extract MSRP
        for pc in price_candidates:
            ctx = pc['context']
            if any(word in ctx for word in ['msrp', 'manufacturer', 'retail', 'original']):
                if int(pc['amount']) > 10000:
                    data['vehicle MSRP'] = pc['amount']
                    logger.info(f"  ✓ MSRP: ${pc['amount']}")
                    break
        
        # === MILEAGE ===
        km_match = re.search(r'([\d,]+)\s*km', page_text, re.I)
        if km_match:
            data['mileage'] = km_match.group(1).replace(',', '')
            logger.info(f"[MILEAGE] {data['mileage']} km")
        
        # === COLOR ===
        for block in blocks:
            if any(word in block['text'].lower() for word in ['exterior', 'color', 'colour']):
                # Extract color name
                text = block['text']
                # Remove label
                text = re.sub(r'(?i)(exterior|color|colour)\s*:?\s*', '', text)
                text = self.clean(text)
                if 2 < len(text) < 40:
                    data['color'] = text
                    logger.info(f"[COLOR] {text}")
                    break
        
        # === ENGINE ===
        for block in blocks:
            if 'engine' in block['text'].lower():
                text = re.sub(r'(?i)engine\s*:?\s*', '', block['text'])
                text = self.clean(text)
                if 5 < len(text) < 100:
                    data['engine'] = text
                    logger.info(f"[ENGINE] {text}")
                    break
        
        # === BODY STYLE ===
        logger.info(f"\n[BODY STYLE]")
        
        # Try to find explicit body style
        for block in blocks:
            if any(word in block['text'].lower() for word in ['body style', 'body type', 'type:']):
                text = re.sub(r'(?i)(body\s*style|body\s*type|type)\s*:?\s*', '', block['text'])
                text = self.clean(text)
                # Validate it's actually a body style
                if any(style in text.lower() for style in ['sedan', 'suv', 'truck', 'van', 'coupe', 'hatchback', 'wagon', 'convertible']):
                    data['body style'] = text
                    logger.info(f"  ✓ {text} (explicit)")
                    break
        
        # Infer from model if not found
        if not data['body style']:
            model = data['model'].lower()
            
            trucks = ['tundra', 'tacoma', 'frontier', 'titan', 'f-150', 'f-250', 'f-350', 
                     'silverado', 'sierra', 'ram', 'canyon', 'colorado', 'ranger', 'gladiator']
            suvs = ['rav4', 'highlander', '4runner', 'sequoia', 'escape', 'explorer', 
                   'expedition', 'bronco', 'cr-v', 'pilot', 'passport', 'rogue', 'pathfinder',
                   'armada', 'murano', 'cx-5', 'cx-9', 'tucson', 'santa fe', 'palisade',
                   'sorento', 'telluride', 'outback', 'ascent', 'forester', 'cherokee',
                   'wrangler', 'grand cherokee', 'durango', 'tahoe', 'suburban', 'yukon',
                   'terrain', 'acadia', 'enclave', 'traverse', 'blazer', 'equinox', 'trailblazer']
            sedans = ['camry', 'corolla', 'avalon', 'accord', 'civic', 'insight', 'clarity',
                     'altima', 'sentra', 'maxima', 'mazda3', 'mazda6', 'elantra', 'sonata',
                     'forte', 'optima', 'k5', 'stinger', 'legacy', 'impreza', 'wrx']
            vans = ['sienna', 'odyssey', 'pacifica', 'caravan', 'sedona', 'carnival']
            
            if any(t in model for t in trucks):
                data['body style'] = 'Pickup Truck'
            elif any(s in model for s in suvs):
                data['body style'] = 'SUV'
            elif any(s in model for s in sedans):
                data['body style'] = 'Sedan'
            elif any(v in model for v in vans):
                data['body style'] = 'Minivan'
            
            if data['body style']:
                logger.info(f"  ✓ {data['body style']} (inferred)")
        
        # === DESCRIPTION ===
        logger.info(f"\n[DESCRIPTION]")
        
        # Look for description sections
        for elem in soup.find_all(['div', 'section', 'article']):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            
            if any(kw in classes or kw in elem_id for kw in ['description', 'overview', 'detail', 'about', 'comment']):
                # Get only direct text (not nested)
                text = ' '.join(elem.stripped_strings)
                text = self.clean(text)
                if 100 < len(text) < 5000:
                    data['description'] = text
                    logger.info(f"  ✓ Found ({len(text)} characters)")
                    logger.info(f"    Preview: {text[:100]}...")
                    break
        
        # === VEHICLE OPTIONS ===
        logger.info(f"\n[OPTIONS]")
        
        options = []
        
        # Method 1: Find feature lists
        for ul in soup.find_all(['ul', 'ol']):
            # Check if this is a feature list
            parent = ul.find_parent(['div', 'section'])
            if parent:
                parent_text = ' '.join(parent.stripped_strings)[:500].lower()
                
                if any(kw in parent_text for kw in ['feature', 'option', 'equipment', 'include', 'standard', 'package']):
                    for li in ul.find_all('li', recursive=False):
                        opt = self.clean(li.get_text())
                        if 3 < len(opt) < 150:
                            options.append(opt)
                    
                    if options:
                        logger.info(f"  ✓ Found {len(options)} from list")
                        break
        
        # Method 2: Find specification tables
        if not options:
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) == 2:
                        opt = f"{self.clean(cells[0].get_text())}: {self.clean(cells[1].get_text())}"
                        if len(opt) < 150:
                            options.append(opt)
            
            if options:
                logger.info(f"  ✓ Found {len(options)} from table")
        
        if options:
            data['vehicle option'] = '; '.join(options[:100])
            # Show first 5 as preview
            logger.info(f"  Preview:")
            for opt in options[:5]:
                logger.info(f"    - {opt}")
        else:
            logger.info(f"  ⚠ No options found")
        
        # === CERTIFIED PRE-OWNED ===
        if re.search(r'certified\s+pre-?owned|CPO', page_text, re.I):
            data['certified pre-owned'] = 'yes'
            logger.info(f"[CPO] Yes")
        
        # === IMAGE ===
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src and not any(x in src.lower() for x in ['logo', 'icon', 'badge']):
                data['image link'] = urljoin(self.base_url, src)
                break
        
        # === FINAL SUMMARY ===
        logger.info(f"\n{'='*120}")
        logger.info(f"SUMMARY:")
        logger.info(f"  Title: {data['title']}")
        logger.info(f"  Vehicle: {data['year']} {data['brand']} {data['model']} {data['trim / sub-model']}")
        logger.info(f"  Stock: {data['id / stock-#']} | VIN: {data['vin']}")
        logger.info(f"  PRICE: ${data['price']} | MSRP: ${data['vehicle MSRP']}")
        logger.info(f"  CONDITION: {data['condition']}")
        logger.info(f"  BODY STYLE: {data['body style']}")
        logger.info(f"  Mileage: {data['mileage']} km | Color: {data['color']}")
        logger.info(f"  Description: {'✓ ' + str(len(data['description'])) + ' chars' if data['description'] else '✗'}")
        logger.info(f"  Options: {'✓ ' + str(len(data['vehicle option'].split(';'))) + ' items' if data['vehicle option'] else '✗'}")
        logger.info(f"  CPO: {data['certified pre-owned']}")
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
        logger.info(f"{'='*120}\n")
        
        for i, url in enumerate(sorted(all_links), 1):
            logger.info(f"VEHICLE {i}/{len(all_links)}")
            vehicle = self.scrape_vehicle(url)
            if vehicle:
                all_vehicles.append(vehicle)
            time.sleep(1)
        
        return all_vehicles
