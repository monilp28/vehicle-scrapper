from http.server import BaseHTTPRequestHandler
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.vehicle_scraper import UniversalVehicleScraper
from scraper.sheets_uploader import GoogleSheetsUploader

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        try:
            # URLs to scrape
            urls = [
                "https://www.reddeertoyota.com/inventory/new/",
                "https://www.reddeertoyota.com/inventory/new/?page=2",
                "https://www.reddeertoyota.com/inventory/new/?page=3",
                "https://www.reddeertoyota.com/inventory/used/",
                "https://www.reddeertoyota.com/inventory/used/?page=2",
                "https://www.reddeertoyota.com/inventory/used/?page=3"
            ]
            
            # Scrape vehicles
            scraper = UniversalVehicleScraper()
            vehicles = scraper.scrape_inventory_pages(urls)
            
            if not vehicles:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No vehicles scraped'}).encode())
                return
            
            # Upload to Google Sheets
            google_creds = os.getenv('GOOGLE_CREDENTIALS')
            sheet_id = os.getenv('GOOGLE_SHEET_ID')
            
            if google_creds and sheet_id:
                uploader = GoogleSheetsUploader(google_creds, sheet_id)
                uploader.upload_vehicles(vehicles)
            
            # Return success
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'success': True,
                'vehicles_scraped': len(vehicles),
                'message': f'Successfully scraped {len(vehicles)} vehicles and uploaded to Google Sheets'
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
