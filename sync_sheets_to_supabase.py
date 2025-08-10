import base64
import json
import os
from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = os.getenv("SHEET_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_credentials():
    b64_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64")
    if b64_json:
        json_str = base64.b64decode(b64_json).decode('utf-8')
        service_account_info = json.loads(json_str)
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    else:
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file:
            creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        else:
            raise Exception("No Google service account credentials found.")
    return creds

def read_sheet():
    creds = get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Meta")
    return worksheet.get_all_records()

def upsert_to_supabase(records):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    for r in records:
        payload = {
            "site_name": r.get("Site Name") or r.get("site_name"),
            "client_name": r.get("Client Name"),
            "client_email": r.get("Client Email"),
            "client_whatsapp": r.get("Client WhatsApp"),
            "labour_name": r.get("Labour Name"),
            "labour_email": r.get("Labour Email"),
            "labour_whatsapp": r.get("Labour WhatsApp"),
            "updated_at": None
        }
        supabase.table("sites").upsert(payload, on_conflict="site_name").execute()

if __name__ == "__main__":
    rows = read_sheet()
    upsert_to_supabase(rows)
    print(f"Synced {len(rows)} rows to Supabase.")
