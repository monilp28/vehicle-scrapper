import gspread
from google.oauth2.service_account import Credentials
import json
import logging
import time

logger = logging.getLogger(__name__)

class GoogleSheetsUploader:
    def __init__(self, credentials_json, sheet_id):
        """Initialize Google Sheets client"""
        # Parse credentials
        if isinstance(credentials_json, str):
            credentials_dict = json.loads(credentials_json)
        else:
            credentials_dict = credentials_json
        
        self.service_email = credentials_dict.get('client_email', 'UNKNOWN')
        logger.info(f"Service Account Email: {self.service_email}")
        
        # Define scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Create credentials
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        
        # Authorize gspread client
        self.client = gspread.authorize(creds)
        self.sheet_id = sheet_id
        
    def upload_vehicles(self, vehicles):
        """Upload vehicle data to Google Sheets"""
        try:
            logger.info(f"Attempting to open spreadsheet with ID: {self.sheet_id}")
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            logger.info(f"Successfully opened spreadsheet: {spreadsheet.title}")
            
            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet('Vehicle Inventory')
                logger.info("Found existing 'Vehicle Inventory' worksheet")
            except gspread.WorksheetNotFound:
                logger.info("Creating new 'Vehicle Inventory' worksheet")
                worksheet = spreadsheet.add_worksheet(title='Vehicle Inventory', rows=1000, cols=21)
            
            # Clear existing data
            logger.info("Clearing existing data...")
            worksheet.clear()
            
            # Prepare headers
            headers = [
                'title', 'id / stock-#', 'price', 'condition', 'feed label',
                'body style', 'brand', 'certified pre-owned', 'color', 'description',
                'engine', 'image link', 'link', 'mileage', 'model',
                'trim / sub-model', 'vehicle MSRP', 'vehicle all in price',
                'vehicle option', 'vin', 'year'
            ]
            
            # Prepare data rows
            rows = [headers]
            logger.info(f"Preparing {len(vehicles)} vehicle rows...")
            for vehicle in vehicles:
                row = [str(vehicle.get(header, '')) for header in headers]
                rows.append(row)
            
            logger.info(f"Total rows to upload: {len(rows)} (including header)")
            
            # Update worksheet in batches if large dataset
            if len(rows) > 1000:
                logger.info("Large dataset detected, uploading in batches...")
                batch_size = 500
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    start_row = i + 1
                    end_row = start_row + len(batch) - 1
                    cell_range = f'A{start_row}:U{end_row}'
                    logger.info(f"Uploading batch {i//batch_size + 1}: rows {start_row}-{end_row}")
                    worksheet.update(cell_range, batch, value_input_option='RAW')
            else:
                # Upload all at once
                logger.info("Uploading all data...")
                result = worksheet.update('A1', rows, value_input_option='RAW')
                logger.info(f"Update result: {result}")
                
                # Add a small delay to ensure data is written
                time.sleep(2)
            
            logger.info("Data uploaded, formatting headers...")
            
            # Format headers
            try:
                worksheet.format('A1:U1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                    'horizontalAlignment': 'CENTER'
                })
                logger.info("Headers formatted successfully")
            except Exception as format_error:
                logger.warning(f"Could not format headers: {format_error}")
            
            # Force a refresh and verify data was written
            time.sleep(1)
            written_rows = worksheet.get_all_values()
            logger.info(f"Verification: {len(written_rows)} rows in sheet (expected {len(rows)})")
            
            if len(written_rows) < 2:
                logger.error(f"❌ DATA NOT WRITTEN! Only {len(written_rows)} rows found")
                logger.error(f"⚠️  PERMISSION ISSUE: Make sure you shared the sheet with: {self.service_email}")
                logger.error(f"   Give it 'Editor' access in Google Sheets Share settings")
                return False
            
            logger.info(f"✓ Successfully uploaded {len(vehicles)} vehicles to Google Sheets")
            logger.info(f"✓ Spreadsheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}")
            logger.info(f"✓ First data row: {written_rows[1][:3] if len(written_rows) > 1 else 'NONE'}")
            
            return True
            
        except gspread.exceptions.APIError as e:
            logger.error(f"Google Sheets API Error: {e}")
            logger.error(f"Error details: {e.response.text if hasattr(e, 'response') else 'No details'}")
            return False
        except Exception as e:
            logger.error(f"Error uploading to Google Sheets: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
