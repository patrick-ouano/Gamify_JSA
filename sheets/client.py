import os
import json
import gspread
from google.oauth2.service_account import Credentials

# Allow R/W operations in google sheets
# Allow accessing files in GDrive.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    # Prefer GOOGLE_CREDS env var (Heroku); fall back to local credentials.json
    google_creds = os.getenv("GOOGLE_CREDS")

    if google_creds:
        info = json.loads(google_creds)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=SCOPES
        )

    client = gspread.authorize(creds)
    return client