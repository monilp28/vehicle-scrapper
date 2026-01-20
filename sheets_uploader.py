import gspread
from google.oauth2.service_account import Credentials
import json
import os
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsUploader:
    def __init__(self, credentials_json, sheet_id):
        """Initialize Google Sheets client"""
        # Parse credentials
        if isinstance(credentials_json, str):
            credentials_dict = json.loads(credentials_json)
        else:
            credentials_dict = credentials_json
        
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
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            
            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet('Vehicle Inventory')
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title='Vehicle Inventory', rows=1000, cols=21)
            
            # Clear existing data
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
            for vehicle in vehicles:
                row = [vehicle.get(header, '') for header in headers]
                rows.append(row)
            
            # Update worksheet
            worksheet.update('A1', rows)
            
            # Format headers
            worksheet.format('A1:U1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
            })
            
            logger.info(f"Successfully uploaded {len(vehicles)} vehicles to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to Google Sheets: {e}")
            return False
