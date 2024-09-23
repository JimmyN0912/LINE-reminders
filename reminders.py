import csv
import datetime
import requests
from dotenv import load_dotenv
import os

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
    events = []
    with open(file_path, mode='r', encoding='Big5') as file:
        reader = csv.DictReader(file)
        for row in reader:
            event_name = row['Event name'].strip()
            event_date = datetime.datetime.strptime(row['Event date and time'].strip(), '%m/%d/%Y %H:%M:%S')
            events.append({'name': event_name, 'date': event_date})
    return events

def is_event_tomorrow(event_date):
    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    return event_date.date() == tomorrow.date()

def is_event_within_week(event_date):
    today = datetime.datetime.now()
    if today.weekday() == 6:  # If today is Sunday
        start_of_week = today
    else:
        start_of_week = today - datetime.timedelta(days=today.weekday() + 1)  # Most recent Sunday
    end_of_week = start_of_week + datetime.timedelta(days=6)  # Upcoming Saturday
    return start_of_week.date() <= event_date.date() <= end_of_week.date()

def call_webhook(payload):
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        print("Successfully called webhook")
    else:
        print("Failed to call webhook")

def check_events(csv_file_path):
    events = read_csv(csv_file_path)
    reminders_tomorrow = []
    reminders_week = []

    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)
    classes_tomorrow = weekday_subjects[tomorrow.weekday()]

    for event in events:
        if is_event_tomorrow(event['date']):
            reminders_tomorrow.append(f"{event['name']} (日期: {event['date'].strftime('%Y-%m-%d')})")
        if is_event_within_week(event['date']):
            reminders_week.append(f"{event['name']} (日期: {event['date'].strftime('%Y-%m-%d')})")

    # Number the reminders and join with newline characters
    reminders_tomorrow = "\n".join([f"   {i+1}. {reminder}" for i, reminder in enumerate(reminders_tomorrow)])
    reminders_week = "\n".join([f"   {i+1}. {reminder}" for i, reminder in enumerate(reminders_week)])

    payload = {
        'classes_tomorrow': classes_tomorrow,
        'reminders_tomorrow': reminders_tomorrow,
        'reminders_week': reminders_week
    }
    call_webhook(payload)

def main():
    csv_file_path = "C:\\Share\\Reminders.csv"  # Replace with your CSV file path
    check_events(csv_file_path)

if __name__ == "__main__":
    main()