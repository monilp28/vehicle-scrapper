import os
import logging
from dotenv import load_dotenv
from scraper.vehicle_scraper import UniversalVehicleScraper
from scraper.sheets_uploader import GoogleSheetsUploader

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function"""
    logger.info("Starting vehicle scraper...")
    
    # URLs to scrape
    urls = [
        "https://www.reddeertoyota.com/inventory/new/",
        "https://www.reddeertoyota.com/inventory/new/?page=2",
        "https://www.reddeertoyota.com/inventory/new/?page=3",
        "https://www.reddeertoyota.com/inventory/used/",
        "https://www.reddeertoyota.com/inventory/used/?page=2",
        "https://www.reddeertoyota.com/inventory/used/?page=3"
    ]
    
    # Initialize scraper
    scraper = UniversalVehicleScraper()
    
    # Scrape vehicles
    logger.info(f"Scraping {len(urls)} pages...")
    vehicles = scraper.scrape_inventory_pages(urls)
    logger.info(f"Scraped {len(vehicles)} vehicles")
    
    if not vehicles:
        logger.warning("No vehicles scraped. Exiting.")
        return
    
    # Get credentials from environment
    google_creds = os.getenv('GOOGLE_CREDENTIALS')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not google_creds or not sheet_id:
        logger.error("Missing Google credentials or Sheet ID")
        return
    
    # Upload to Google Sheets
    logger.info("Uploading to Google Sheets...")
    uploader = GoogleSheetsUploader(google_creds, sheet_id)
    success = uploader.upload_vehicles(vehicles)
    
    if success:
        logger.info("✓ Successfully completed scraping and upload")
    else:
        logger.error("✗ Failed to upload to Google Sheets")

if __name__ == "__main__":
    main()
