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
PUBLIC_IP_URI = 'https://api.bigdatacloud.net/data/client-ip'
DNS_ZONES_URI = 'https://api.netlify.com/api/v1/dns_zones/'
DEFAULT_TTL = 600
ZONE_SLUG = f"{FQDN.split('.')[-2]}_{FQDN.split('.')[-1]}"
headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'Authorization': f'Bearer {API_TOKEN}'
}


def get_public_ip_address():
    try:
        public_ip_address = requests.get(PUBLIC_IP_URI, timeout=15).json()['ipString']
        logger.info(f'System current public IP address is: {public_ip_address}')
        return public_ip_address
    except Exception as ex:
        logger.error(f'An error occurred trying to retrieve your public IP address. Cause: {ex}')
        sys.exit(1)


def create_dns_record(hostname, value):
    req_url = DNS_ZONES_URI + ZONE_SLUG + '/dns_records'
    body = {
        'type': 'A',
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
            logger.error(f'Failed to create DNS record. Status: {res.status_code}')
            sys.exit(1)
        logger.info(f'New DNS record created successfully for hostname: {hostname}, with value: {value}')
        return res.json()
    except Exception as ex:
        logger.error(f'An error occurred trying to create new DNS record. Cause: {ex}')
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


def extract_target_record_id(records):
    for record in records:
        if FQDN == record['hostname'] and record['type'] == 'A':
            return record['id'], record['value']
    return None, None


if __name__ == '__main__':

    logger.info('----- Executing netlify_ddns -----')

    current_public_ip = get_public_ip_address()

    records_list = get_dns_records()
    record_id, record_ip = extract_target_record_id(records_list)

    if record_id is None:
        create_dns_record(FQDN, current_public_ip)
    elif current_public_ip != record_ip:
        create_dns_record(FQDN, current_public_ip)
        delete_dns_record(record_id)
    else:
        logger.info(f'DNS record already up-to-date for hostname: {FQDN}')

    logger.info('----- Script executed successfully -----')
    sys.exit(0)
