import os
import logging
from dotenv import load_dotenv
from scraper.vehicle_scraper import VehicleScraper
from scraper.sheets_uploader import GoogleSheetsUploader

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function"""
    logger.info("\n" + "="*120)
    logger.info("VEHICLE INVENTORY SCRAPER")
    logger.info("="*120)
    
    urls = [
        "https://www.reddeertoyota.com/inventory/new/",
        "https://www.reddeertoyota.com/inventory/new/?page=2",
        "https://www.reddeertoyota.com/inventory/new/?page=3",
        "https://www.reddeertoyota.com/inventory/used/",
        "https://www.reddeertoyota.com/inventory/used/?page=2",
        "https://www.reddeertoyota.com/inventory/used/?page=3"
    ]
    
    scraper = VehicleScraper()
    
    logger.info(f"\nScraping {len(urls)} pages...")
    vehicles = scraper.scrape_inventory_pages(urls)
    logger.info(f"\n{'='*120}")
    logger.info(f"SCRAPING COMPLETE - Total vehicles: {len(vehicles)}")
    logger.info(f"{'='*120}")
    
    if not vehicles:
        logger.warning("\n⚠️  No vehicles scraped. Exiting.")
        return
    
    google_creds = os.getenv('GOOGLE_CREDENTIALS')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not google_creds or not sheet_id:
        logger.error("\n❌ Missing Google credentials or Sheet ID")
        return
    
    logger.info("\n" + "="*120)
    logger.info("UPLOADING TO GOOGLE SHEETS")
    logger.info("="*120)
    
    uploader = GoogleSheetsUploader(google_creds, sheet_id)
    success = uploader.upload_vehicles(vehicles)
    
    if success:
        logger.info("\n✅ Successfully completed scraping and upload!")
        logger.info(f"   Total vehicles uploaded: {len(vehicles)}")
        logger.info(f"   Google Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}")
    else:
        logger.error("\n❌ Failed to upload to Google Sheets")

if __name__ == "__main__":
    main()
