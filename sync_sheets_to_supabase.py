import requests
import streamlit as st
import os
import json
import base64
from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# --- Google Sheets / Supabase Config ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = os.getenv("SHEET_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client once
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_credentials():
    if os.getenv("GOOGLE_SERVICE_ACCOUNT_B64"):
        b64_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64")
        json_str = base64.b64decode(b64_json).decode('utf-8')
        service_account_info = json.loads(json_str)
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    elif os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"):
        creds = Credentials.from_service_account_file(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"), scopes=SCOPES)
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

def fetch_sites_and_labours():
    data = supabase.table("sites").select("site_name, labour_name").execute()
    sites = sorted(set([item["site_name"] for item in data.data if item.get("site_name")]))
    labours = sorted(set([item["labour_name"] for item in data.data if item.get("labour_name")]))
    return sites, labours

# --- Streamlit UI ---

st.title("Daily Work Plan / Completion Status")

# Button to sync Google Sheet → Supabase on-demand (optional)
if st.button("Sync Meta Tab from Google Sheet to Supabase"):
    with st.spinner("Syncing..."):
        try:
            rows = read_sheet()
            upsert_to_supabase(rows)
            st.success(f"Synced {len(rows)} rows to Supabase.")
        except Exception as e:
            st.error(f"Sync failed: {e}")

# Load dynamic dropdown options from Supabase
sites, labours = fetch_sites_and_labours()

if not sites or not labours:
    st.warning("No sites or labours found. Please sync first.")
else:
    site_selected = st.selectbox("Select Site", sites)
    labour_selected = st.selectbox("Select Labour", labours)

    # Choose input type
    field_choice = st.selectbox("Select Field to Enter", ["Morning Plan", "Work Done", "Work Not Done"])

    # Text input for that field
    text_value = st.text_area(f"Enter details for {field_choice}")

    # Morning or Evening toggle
    time_of_day = st.radio("Is this for Morning Plan or Evening Completion?", ["Morning", "Evening"])

    if st.button("Submit"):
        if not text_value.strip():
            st.error("Please enter some text before submitting.")
        else:
            # Construct JSON payload to send to Telegram/n8n
            payload = {
                "date": str(st.date_input("Select Date")),
                "site_name": site_selected,
                "labour_name": labour_selected,
                "field": field_choice,
                "value": text_value.strip(),
                "time_of_day": time_of_day
            }
            st.json(payload)
            
            # --- Telegram Sending Logic ---
            TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
            TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                message = json.dumps(payload, indent=2)  # pretty JSON text
                send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                resp = requests.post(send_url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                })
                if resp.status_code == 200:
                    st.success("Sent to Telegram!")
                else:
                    st.error(f"Failed to send to Telegram: {resp.text}")
            else:
                st.warning("Telegram credentials not set. Skipping Telegram send.")
                # TODO: Send payload to your n8n webhook here if you want (via requests.post)
                st.success("Payload ready! Send this JSON to your Telegram or n8n workflow.")
