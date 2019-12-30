#!/usr/bin/env python
import re

import requests
import json
import os
from geopy.geocoders import Nominatim, options
from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from dotenv import load_dotenv
from datetime import datetime
from rebel_management_utilities import get_all_members

options.default_timeout = None
geolocator = Nominatim(user_agent="NL postcode mapping.")
geocode = RateLimiter(geolocator.geocode, error_wait_seconds=300)


def load_api_key():
    load_dotenv()
    key = os.getenv("ACTION_NETWORK_API_KEY")

    if not key:
        raise OSError('ACTION_NETWORK_API_KEY not found in .env')

    return key


def get_primary_postcode(member):
    postcodes = member['postal_addresses']
    return [p for p in postcodes if p['primary']][0]


def has_local_group(member):
    try:
        local_group = member['custom_fields']['local_group']
        return not (local_group == 'Not selected' or local_group == 'No group nearby')
    except KeyError:
        return False


def record_logs(new_logs, file_name):
    logs_directory = 'logs'
    file_name = f'{file_name}.json'
    file_path = os.path.join(logs_directory, file_name)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path) as f:
            logs = json.load(f)['logs']
    except FileNotFoundError:
        logs = []

    logs.extend(new_logs)

    data = {'logs': logs}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def filter_members(members):
    filtered_members = []
    for m in members:
        primary_postcode = get_primary_postcode(m)
        # skip those with no postcode
        if 'postal_code' not in primary_postcode:
            continue
        # skip those with empty postcode
        if not primary_postcode['postal_code']:
            continue
        # skip those outside NL
        if primary_postcode['country'] != 'NL':
            continue
        # skip those that already have a local group
        if has_local_group(m):
            continue
        filtered_members.append(m)
    return filtered_members


def postcode_to_coordinates(postcode):
    # format postcode
    postcode = postcode.replace(" ", "")
    postcode = postcode.upper()
    postcode_regex = re.search(r'\d{4}[a-zA-Z]{2}|\d{4}', postcode)
    try:
        postcode = postcode_regex.group()
    except AttributeError:
        # invalid postcode
        print(f'Invalid postcode: {postcode}')
        raise ValueError(postcode)

    location = geocode(f"{postcode}, Nederland")
    try:
        coordinates = (location.latitude, location.longitude)
        return coordinates
    except AttributeError:
        # invalid postcode if no coordinates are found
        print(f'Coordinates not found: {postcode}')
        raise ValueError(postcode)


def get_local_group_coordinates(local_groups_postcodes):
    local_groups = []
    for name, postcode in local_groups_postcodes.items():
        lg = {
            'local_group': name,
            'postcode': postcode,
            'coordinates': postcode_to_coordinates(postcode)
        }
        local_groups.append(lg)
    return local_groups


def nearest_coordinates(destinations, target_coordinates):
    """returns destination with the nearest coordinates to target coordinates"""
    distances = []
    for d in destinations:
        d['distance'] = geodesic(target_coordinates, d['coordinates']).meters
        distances.append(d)
    nearest = min(distances, key=lambda k: k['distance'])
    return nearest


def nearest_local_group(local_groups, member):
    """returns local group nearest to a member"""
    member_postcode = get_primary_postcode(member)['postal_code']
    member_coordinates = postcode_to_coordinates(member_postcode)
    nearest = nearest_coordinates(local_groups, member_coordinates)
    return nearest['local_group']


def local_group_mapping(local_groups_postcodes, members):
    mapped_members = []
    local_groups = get_local_group_coordinates(local_groups_postcodes)
    for m in members:
        try:
            nearest_group = nearest_local_group(local_groups, m)
            m['custom_fields']['local_group'] = nearest_group
            mapped_members.append(m)
        except ValueError:  # invalid postcode
            continue
    return mapped_members


def update_members_local_group(members, api_key):
    success_logs = []
    error_logs = []

    headers = {'OSDI-API-Token': api_key}

    for m in members:
        URL = m['_links']['self']['href']
        new_local_group = m['custom_fields']['local_group']
        payload = {
            'custom_fields': {
                'local_group': new_local_group
            }
        }
        response = requests.put(URL, headers=headers, json=payload)
        log = {
            'identifiers': m['identifiers'],
            'postcode': get_primary_postcode(m)['postal_code'],
            'local_group': new_local_group,
            'timestamp_update': datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        }
        if response.status_code == 200:
            success_logs.append(log)
        else:
            log['status_code'] = response.status_code
            error_logs.append(log)

    record_logs(success_logs, file_name='success')
    record_logs(error_logs, file_name='error')


if __name__ == '__main__':
    api_key = load_api_key()
    members = get_all_members(api_key)
    members = filter_members(members)

    with open('local_groups_postcodes.json') as f:
        local_groups_postcodes = json.load(f)

    batch_size = 100
    for i in range(0, len(members), batch_size):
        members_batch = members[i:i + batch_size]
        members_batch = local_group_mapping(local_groups_postcodes, members_batch)
        update_members_local_group(members_batch, api_key)
