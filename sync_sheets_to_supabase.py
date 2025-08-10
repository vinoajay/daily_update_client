# sync_sheets_to_supabase.py
import os
from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# env vars: GOOGLE_SERVICE_ACCOUNT_FILE, SHEET_ID, SUPABASE_URL, SUPABASE_KEY
SERVICE_ACCOUNT_FILE = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
SHEET_ID = os.environ["SHEET_ID"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

def read_sheet():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Meta")
    return worksheet.get_all_records()  # list of dicts

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
        # upsert on unique site_name (requires unique constraint)
        supabase.table("sites").upsert(payload, on_conflict="site_name").execute()

if __name__ == "__main__":
    rows = read_sheet()
    upsert_to_supabase(rows)
    print(f"Synced {len(rows)} rows to Supabase.")
