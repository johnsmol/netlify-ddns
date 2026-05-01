import logging
import logging.handlers as handlers
import os
import sys

import requests
import validators
from dotenv import load_dotenv

# logging configuration
logger = logging.getLogger('netlify_ddns')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logHandler = handlers.TimedRotatingFileHandler('netlify_ddns.log', when='D', interval=1, backupCount=2)
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# load .env and validate required variables
try:
    load_dotenv()

    FQDN = os.environ.get('FQDN')
    API_TOKEN = os.environ.get('NETLIFY_API_TOKEN')

    if not FQDN or not API_TOKEN:
        logger.error('FQDN and NETLIFY_API_TOKEN must both be set in .env')
        sys.exit(1)

    if not validators.domain(FQDN):
        logger.error(f"Provided hostname '{FQDN}' is not a valid FQDN")
        sys.exit(1)

except Exception as e:
    logger.error(f'Unexpected error retrieving required variables from .env file. Cause: {e}')
    sys.exit(1)

# constants
PUBLIC_IPV4_URI = 'https://api4.ipify.org?format=json'
PUBLIC_IPV6_URI = 'https://api6.ipify.org?format=json'
DNS_ZONES_URI = 'https://api.netlify.com/api/v1/dns_zones/'
DEFAULT_TTL = 600
ZONE_SLUG = f"{FQDN.split('.')[-2]}_{FQDN.split('.')[-1]}"
headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'Authorization': f'Bearer {API_TOKEN}'
}


def get_public_ip_address(version=4):
    uri = PUBLIC_IPV4_URI if version == 4 else PUBLIC_IPV6_URI
    try:
        ip = requests.get(uri, timeout=15).json()['ip']
        logger.info(f'System current public IPv{version} address is: {ip}')
        return ip
    except Exception as ex:
        if version == 6:
            logger.warning(f'Could not retrieve public IPv6 address, skipping AAAA record update. Cause: {ex}')
            return None
        logger.error(f'An error occurred trying to retrieve your public IPv{version} address. Cause: {ex}')
        sys.exit(1)


def create_dns_record(hostname, value, record_type):
    req_url = DNS_ZONES_URI + ZONE_SLUG + '/dns_records'
    body = {
        'type': record_type,
        'hostname': hostname,
        'value': value,
        'ttl': DEFAULT_TTL,
        'priority': None,
        'weight': None,
        'port': None,
        'flag': None,
        'tag': None,
    }
    try:
        res = requests.post(req_url, json=body, headers=headers, timeout=15)
        if res.status_code != 201:
            logger.error(f'Failed to create {record_type} record. Status: {res.status_code}')
            sys.exit(1)
        logger.info(f'New {record_type} record created successfully for hostname: {hostname}, with value: {value}')
        return res.json()
    except Exception as ex:
        logger.error(f'An error occurred trying to create new {record_type} record. Cause: {ex}')
        sys.exit(1)


def delete_dns_record(dns_record_id):
    req_url = DNS_ZONES_URI + ZONE_SLUG + '/dns_records/' + dns_record_id
    try:
        res = requests.delete(req_url, headers=headers, timeout=15)
        if res.status_code != 204:
            logger.error(f'Failed to delete old DNS record. Status: {res.status_code}')
            sys.exit(1)
        logger.info(f'Old DNS record with ID {dns_record_id} deleted successfully')
    except Exception as ex:
        logger.error(f'An error occurred trying to delete old DNS record with ID {dns_record_id}. Cause: {ex}')
        sys.exit(1)


def get_dns_records():
    req_url = DNS_ZONES_URI + ZONE_SLUG + '/dns_records'
    try:
        return requests.get(req_url, headers=headers, timeout=15).json()
    except Exception as ex:
        logger.error(f'An error occurred trying to fetch all DNS records. Cause: {ex}')
        sys.exit(1)


def extract_target_record_id(records, record_type):
    for record in records:
        if FQDN == record['hostname'] and record['type'] == record_type:
            return record['id'], record['value']
    return None, None


def update_record(records_list, current_ip, record_type):
    if current_ip is None:
        return

    record_id, record_ip = extract_target_record_id(records_list, record_type)

    if record_id is None:
        create_dns_record(FQDN, current_ip, record_type)
    elif current_ip != record_ip:
        create_dns_record(FQDN, current_ip, record_type)
        delete_dns_record(record_id)
    else:
        logger.info(f'{record_type} record already up-to-date for hostname: {FQDN}')


if __name__ == '__main__':

    logger.info('----- Executing netlify_ddns -----')

    current_ipv4 = get_public_ip_address(version=4)
    current_ipv6 = get_public_ip_address(version=6)

    records_list = get_dns_records()

    update_record(records_list, current_ipv4, 'A')
    update_record(records_list, current_ipv6, 'AAAA')

    logger.info('----- Script executed successfully -----')
    sys.exit(0)
