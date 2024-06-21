Introduction

This documentation provides an overview of a middleware Python script designed to automate the retrieval and processing of guest data from the MyPlace Connect API and push this data into Salesforce Marketing Cloud (SFMC). The script retrieves guest entries from the previous day, formats the data to match the schema required by SFMC, and pushes the data into the specified SFMC Data Extension.

Overview

The middleware script performs the following tasks:
            
Data Retrieval: Connects to the MyPlace Connect API to retrieve guest data.
Data Filtering: Filters the retrieved data to include only entries from the previous day.
Data Formatting: Formats the data to match the schema required by the SFMC Data Extension.
Data Upload: Pushes the filtered and formatted data into the specified SFMC Data Extension.

Script Components

Environment Setup
The script uses environment variables to securely manage sensitive information such as API keys and credentials. Ensure you have a .env file in the root directory of your project with the following variables:

SFMC_CLIENT_ID=your_sfmc_client_id
SFMC_CLIENT_SECRET=your_sfmc_client_secret
SFMC_SUBDOMAIN=your_sfmc_subdomain
SFMC_DATA_EXTENSION_KEY=your_data_extension_key
MYPLACE_API_KEY=your_api_key_here

Dependencies
Install the required libraries using pip:

pip install requests python-dotenv

Main Script
The main script comprises several functions, each responsible for a specific task:

Import Libraries and Load Environment Variables

import requests
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

Configuration Variables

sfmc_client_id = os.getenv('SFMC_CLIENT_ID')
sfmc_client_secret = os.getenv('SFMC_CLIENT_SECRET')
sfmc_subdomain = os.getenv('SFMC_SUBDOMAIN')
sfmc_data_extension_key = os.getenv('SFMC_DATA_EXTENSION_KEY')
myplace_api_key = os.getenv('MYPLACE_API_KEY')

Helper Functions

Get Yesterday's Date:
def get_yesterday_date():
    yesterday = datetime.now() - timedelta(1)
    return yesterday.strftime('%Y-%m-%d')
    
Parse Timestamp:

def parse_timestamp(timestamp):
    timestamp = timestamp.split(' GMT')[0]  # Remove the extra part
    return datetime.strptime(timestamp, '%a %b %d %Y %H:%M:%S')
    
Format Last Seen Date:

def format_last_seen(last_seen):
    try:
        last_seen_date = datetime.strptime(last_seen, '%d/%m/%Y, %H:%M')
        return last_seen_date.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return last_seen

base_url = 'https://api.myplaceconnect.net/v1/guests/'
headers = {
    'accept': 'application/json',
    'x-api-key': myplace_api_key
}

def get_all_guests():
    all_guests = []
    seen_ids = set()  # Set to track unique guest IDs
    page = 1
    per_page = 10
    total_pages = 1

Data Retrieval

Get All Guests:

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

Authentication and Data Upload

Get SFMC Access Token:

def get_sfmc_access_token():
    auth_url = f'https://{sfmc_subdomain}.auth.marketingcloudapis.com/v2/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': sfmc_client_id,
        'client_secret': sfmc_client_secret
    }
    response = requests.post(auth_url, json=payload)
    response.raise_for_status()
    return response.json().get('access_token')
    
Main Function

Main Job Function:


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
                    guest['signUp']['formatted_timestamp'] = signUp_date.strftime('%Y-%m-%d %H:%M:%S')
                    guest['formatted_last_seen'] = format_last_seen(guest.get('last_seen', ''))
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
        return

    # Prepare the data for SFMC
    sfmc_data = []
    for guest in filtered_guests:
        sfmc_data.append({
            'keys': {
                'SubscriberKey': guest.get('id', '')
            },
            'values': {
                'FirstName': guest.get('firstName', ''),
                'LastName': guest.get('lastName', ''),
                'Email': guest.get('email', ''),
                'Signup': guest.get('signUp', {}).get('formatted_timestamp', ''),
                'LastSeen': guest.get('formatted_last_seen', '')
            }
        })

    # Push the data to SFMC
    if sfmc_data:
        access_token = get_sfmc_access_token()
        push_to_sfmc(sfmc_data, access_token)
    else:
        print("No data to push to SFMC")



