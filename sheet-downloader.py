from dotenv import load_dotenv
import os
import csv
import time
import psutil
import logging
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#Configure logging
logging.basicConfig(
    filename="downloader.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

load_dotenv()

# The ID and range of the spreadsheet.
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE_NAME = "Sheet1!A4:E"

def main():
    start_time = time.time()
    logging.info("Starting the script")
    process = psutil.Process(os.getpid())
    logging.debug(f"Process Info: {process}")
    mem_before = process.memory_info().rss / 1024 / 1024  # in MB
    logging.debug(f"Memory used before: {mem_before:.2f} MB")

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        logging.info("Loading credentials from token.json")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Token expired, refreshing credentials.")
            creds.refresh(Request())
        else:
            logging.info("No valid credentials found, starting OAuth flow.")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            logging.info("Saving credentials to token.json")
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        logging.info("Requesting data from Google Sheets...")
        request_time = time.time()
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME)
            .execute()
        )
        received_time = time.time()
        logging.info(f"Request completed in {received_time - request_time:.4f} seconds...")
        values = result.get("values", [])
        logging.info(f"Received {len(values)} rows of data.")

        if not values:
            logging.warning("No data found.")
            return
        try:
            logging.info("Writing data to reminders.csv...")
            with open("reminders.csv", mode="w", encoding="UTF-8", newline="") as file:
                writer = csv.writer(file)
                logging.debug("Writing headers to CSV file...")
                writer.writerow(["Event name", "Event date and time", "Weekday"])
                i=1
                for row in values:
                    if len(row) >= 5:
                        logging.debug(f"Writing row {i} to CSV file...")
                        writer.writerow([row[0], row[3], row[4]])
                        i+=1
        except Exception as e:
            print(e)
    except HttpError as err:
        print(err)

    logging.info("reminders.csv has been created successfully.")
    mem_after = process.memory_info().rss / 1024 / 1024  # in MB
    logging.debug(f"Memory used after: {mem_after:.2f} MB")
    end_time = time.time()
    logging.info(f"Script completed in {end_time - start_time:.4f} seconds.")

    # Save metrics
    metrics = {
        'timestamp': datetime.datetime.now().isoformat(),
        'execution_time': end_time - start_time,
        'request_time': received_time - request_time,
        'memory_before': mem_before,
        'memory_after': mem_after,
        'memory_delta': mem_after - mem_before,
        'csv_file_size': os.path.getsize('reminders.csv') / 1024  # in KB
    }
    metrics_file_path = 'downloader_metrics.json'
    if os.path.exists(metrics_file_path):
        with open(metrics_file_path, 'r') as metrics_file:
            all_metrics = json.load(metrics_file)
            if not isinstance(all_metrics, list):
                all_metrics = [all_metrics]
    else:
        all_metrics = []

    all_metrics.append(metrics)

    with open(metrics_file_path, 'w') as metrics_file:
        json.dump(all_metrics, metrics_file, indent=4)

if __name__ == "__main__":
    main()