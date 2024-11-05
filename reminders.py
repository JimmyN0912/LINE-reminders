import csv
import datetime
import requests
from dotenv import load_dotenv
import os
import json
import logging
import time
import psutil

# Configure logging
logging.basicConfig(
    filename='reminders.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

webhook_url = os.getenv('MAKE_WEBHOOK_URL')

# Dictionary mapping weekdays to subject names
weekday_subjects = {
    0: '   機器人/生物 \n   機器人/生物 \n   國文 \n   數學 \n   英文作文 \n   英文作文 \n   自然充實 \n   數學',       # Monday
    1: '   數學 \n   物理 \n   化學 \n   化學 \n   體育 \n   數學 \n   國文 \n   國文',    # Tuesday
    2: '   國文 \n   全民國防教育 \n   英文 \n   化學 \n   班會 \n   團體活動 \n   地科 \n   化學',    # Wednesday
    3: '   家政 \n   家政 \n   本土語 \n   物理 \n   國文 \n   健康與護理 \n   數學 \n   英文',        # Thursday
    4: '   進階程設/生物 \n   進階程設/生物 \n   英文 \n   體育 \n   國文 \n   物理 \n   數學 \n   物理', # Friday
    5: '   不用上課！',      # Saturday
    6: '   不用上課！'    # Sunday
}

def read_csv(file_path):
    start_time = time.time()
    logging.info(f"Reading events from CSV file: {file_path}")
    events = []
    with open(file_path, mode='r', encoding='UTF-8') as file:
        reader = csv.DictReader(file)
        i = 1
        for row in reader:
            logging.debug(f"Reading row {i}")
            event_name = row['Event name'].strip()
            event_date = datetime.datetime.strptime(row['Event date and time'].strip(), '%m/%d/%Y %H:%M:%S')
            event_weekday = row['Weekday'].strip()
            events.append({'name': event_name, 'date': event_date, 'weekday': event_weekday})
            i += 1
    end_time = time.time()
    logging.info(f"Read {i} events from CSV file in {end_time - start_time:.4f} seconds.")
    return events

def is_event_tomorrow(event_date):
    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    return event_date.date() == tomorrow.date()

def is_event_in_3_days(event_date):
    today = datetime.datetime.now()
    three_days_later = today + datetime.timedelta(days=3)
    return today.date() < event_date.date() <= three_days_later.date()

def is_event_on_next_monday(event_date):
    today = datetime.datetime.now()
    monday = today + datetime.timedelta(days=(7 - today.weekday()))
    return event_date.date() == monday.date()

def call_webhook(payload):
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        logging.info("Successfully called webhook")
    else:
        logging.error(f"Failed to call webhook: {response.status_code}")

def check_events(csv_file_path):
    start_time = time.time()
    logging.info(f"Startup time: {start_time}")
    process = psutil.Process(os.getpid())
    logging.debug(f"Process ID: {process}")
    mem_before = process.memory_info().rss / 1024 / 1024  # in MB
    logging.debug(f"Memory usage before: {mem_before:.2f} MB")

    events = read_csv(csv_file_path)
    reminders_tomorrow = []
    reminders_3days = []
    reminders_monday=[]

    logging.info("Setting up dates...")

    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    classes_tomorrow = weekday_subjects[tomorrow.weekday()]

    logging.info("Checking events...")
    for event in events:
        if is_event_on_next_monday(event['date']):
            reminders_monday.append(f"{event['name']}")
        if is_event_tomorrow(event['date']):
            reminders_tomorrow.append(f"{event['name']}")
        elif is_event_in_3_days(event['date']):
            reminders_3days.append(f"{event['name']} ({event['weekday']})")

    # Number the reminders and join with newline characters
    reminders_tomorrow = "\n".join([f"   {i+1}. {reminder}" for i, reminder in enumerate(reminders_tomorrow)])
    reminders_3days = "\n".join([f"   {i+1}. {reminder}" for i, reminder in enumerate(reminders_3days)])
    reminders_monday = "\n".join([f"   {i+1}. {reminder}" for i, reminder in enumerate(reminders_monday)])

    if reminders_tomorrow == "":
        reminders_tomorrow = "明天沒有任何提醒事項！"
    if reminders_3days == "":
        reminders_3days = "三天內沒有任何提醒事項！"

    payload = {
        'classes_tomorrow': classes_tomorrow,
        'reminders_tomorrow': reminders_tomorrow,
        'reminders_week': reminders_3days,
        'reminders_monday': reminders_monday if today.weekday() == 4 else "None"
    }
    call_webhook(payload)

    mem_after = process.memory_info().rss / 1024 / 1024  # in MB
    end_time = time.time()

    # Save metrics to a JSON file with timestamp
    metrics = {
        'timestamp': today.isoformat(),
        'reminders_tomorrow_count': len(reminders_tomorrow.split('\n')),
        'reminders_3days_count': len(reminders_3days.split('\n')) if reminders_3days != "三天內沒有任何提醒事項！" else 0,
        'total_reminders_count': len(events),
        'execution_time': end_time - start_time,
        'memory_delta': mem_after - mem_before
    }
    metrics_file_path = 'metrics.json'
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

    logging.info(f"Metrics saved to {metrics_file_path}")
    logging.info(f"check_events execution time: {end_time - start_time:.2f} seconds")
    logging.info(f"Memory usage before: {mem_before:.2f} MB, after: {mem_after:.2f} MB, difference: {mem_after - mem_before:.2f} MB")

def main():
    logging.info("Starting reminders script...")
    csv_file_path = "reminders.csv"
    check_events(csv_file_path)

if __name__ == "__main__":
    main()