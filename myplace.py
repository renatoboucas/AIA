import requests
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# MyPlace configuration
myplace_api_key = os.getenv('MYPLACE_API_KEY')

# Function to get yesterday's date in the required format
def get_yesterday_date():
    yesterday = datetime.now() - timedelta(1)
    return yesterday.strftime('%Y-%m-%d')

# Function to parse the signUp timestamp
def parse_timestamp(timestamp):
    timestamp = timestamp.split(' GMT')[0]  # Remove the extra part
    return datetime.strptime(timestamp, '%a %b %d %Y %H:%M:%S')

# API URL and headers
base_url = 'https://api.myplaceconnect.net/v1/guests/'
headers = {
    'accept': 'application/json',
    'x-api-key': myplace_api_key
}


# Function to retrieve all pages of data
def get_all_guests():
    all_guests = []
    seen_ids = set()  # Set to track unique guest IDs
    page = 1
    per_page = 10
    total_pages = 1

    while page <= total_pages:
        params = {'page': page, 'per_page': per_page}
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Failed to retrieve data: {response.status_code}")
            break

        data = response.json()
        guests = data.get('data', [])
        
        for guest in guests:
            if guest.get('id') not in seen_ids:
                all_guests.append(guest)
                seen_ids.add(guest.get('id'))

        metadata = data.get('metadata', {})
        total_results = metadata.get('total_results', 0)
        per_page = metadata.get('per_page', 10)
        total_pages = (total_results + per_page - 1) // per_page  # Calculate total pages

        page += 1

    return all_guests

# Retrieve all guests
all_guests = get_all_guests()

# Debugging: Print the signUp timestamps of all guests
print("signUp timestamps of all guests:")
for guest in all_guests:
    signUp_timestamp = guest.get('signUp', {}).get('timestamp', 'No timestamp')
    print(signUp_timestamp)

# Get yesterday's date
yesterday = datetime.now() - timedelta(1)
yesterday_date_str = yesterday.strftime('%Y-%m-%d')

# Filter the guest list to include only those from yesterday
filtered_guests = []
for guest in all_guests:
    if 'signUp' in guest and 'timestamp' in guest['signUp']:
        signUp_timestamp = guest['signUp']['timestamp']
        try:
            signUp_date = parse_timestamp(signUp_timestamp)
            if signUp_date.strftime('%Y-%m-%d') == yesterday_date_str:
                guest['signUp']['formatted_timestamp'] = signUp_date.strftime('%-m/%-d/%Y %-I:%M:%S %p')
                filtered_guests.append(guest)
        except ValueError as e:
            print(f"Error parsing timestamp {signUp_timestamp}: {e}")

# Debugging: Print the type and sample of the filtered guest list
print(f"Filtered guest list type: {type(filtered_guests)}")
if isinstance(filtered_guests, list):
    print(f"Filtered guest list length: {len(filtered_guests)}")
    print(f"Sample filtered guest data: {filtered_guests[0] if len(filtered_guests) > 0 else 'No data available'}")
else:
    print("Unexpected filtered guest list structure")
    exit()

# Function to format last_seen date
def format_last_seen(last_seen):
    try:
        last_seen_date = datetime.strptime(last_seen, '%d/%m/%Y, %H:%M')
        return last_seen_date.strftime('%m/%d/%Y %H:%M')
    except ValueError:
        return last_seen

# Prepare the CSV file
csv_file = 'guests_data.csv'
csv_columns = ['subscriberkey', 'first_name', 'last_name', 'email', 'signup', 'last_seen']

try:
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()

        for guest in filtered_guests:
            if isinstance(guest, dict):
                print(f"Processing guest: {guest}")  # Debugging: Print each guest's data
                writer.writerow({
                    'subscriberkey': guest.get('id', ''),
                    'first_name': guest.get('firstName', ''),
                    'last_name': guest.get('lastName', ''),
                    'email': guest.get('email', ''),
                    'signup': guest.get('signUp', {}).get('formatted_timestamp', ''),
                    'last_seen': format_last_seen(guest.get('last_seen', ''))
                })
            else:
                print(f"Skipping unexpected data format: {guest}")
    print(f"CSV file '{csv_file}' created successfully.")
except IOError as e:
    print(f"I/O error({e.errno}): {e.strerror}")

except Exception as e:
    print(f"An error occurred: {str(e)}")