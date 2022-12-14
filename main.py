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

# load .env and FQDN validation
try:
    load_dotenv()

    FQDN = os.environ.get('FQDN')
    API_TOKEN = os.environ.get('NETLIFY_API_TOKEN')

    if len(FQDN.split('.')) > 3 or not validators.domain(FQDN):
        logger.error('Provided hostname \' {} \' is not a valid FQDN'.format(FQDN))
        sys.exit(1)

except Exception as e:
    logger.error('Unexpected error trying to retrieve required variables from .env file. Cause: ' + e.__str__())
    sys.exit(1)

# constants
PUBLIC_IP_URI = 'https://api.bigdatacloud.net/data/client-ip'
DNS_ZONES_URI = 'https://api.netlify.com/api/v1/dns_zones/'
headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'Authorization': 'Bearer ' + API_TOKEN
}


# get current public IP address
def get_public_ip_address():
    try:
        logger.debug('HTTP GET to {}'.format(PUBLIC_IP_URI))
        public_ip_address = requests.get(PUBLIC_IP_URI).json()['ipString']
        logger.info('System current public IP address is: {}'.format(public_ip_address))
        return public_ip_address
    except Exception as ex:
        logger.error('An error occurred trying to retrieve your public IP address. Cause: {}'.format(ex.__str__()))
        sys.exit(1)


# creating new dns record
def create_dns_record(hostname, value):
    req_url = DNS_ZONES_URI + FQDN.split('.')[-2] + '_' + FQDN.split('.')[-1] + '/dns_records'

    body = {
        'type': "A",
        'hostname': hostname,
        'value': value,
        'ttl': 600,
        'priority': None,
        'weight': None,
        'port': None,
        'flag': None,
        'tag': None
    }

    try:
        res = requests.post(req_url, json=body, headers=headers)
        if res.status_code != 201:
            logger.error('An error occurred trying to create new DNS record. Response status code: {}'.format(res.status_code))
            sys.exit(1)
        elif res.status_code == 201:
            logger.info('New DNS record created successfully for hostname: {}, with value: {}'.format(hostname, value))
            return res.json()
    except Exception as ex:
        logger.error('An error occurred trying to create new DNS record. Cause: {}'.format(ex.__str__()))
        sys.exit(1)


def delete_dns_record(dns_record_id):
    req_url = DNS_ZONES_URI + FQDN.split('.')[-2] + '_' + FQDN.split('.')[-1] + '/dns_records/' + dns_record_id

    try:
        res = requests.delete(req_url, headers=headers)
        if res.status_code != 204:
            logger.error('An error occurred trying to delete the old DNS record. Response status code: {}'.format(res.status_code))
            sys.exit(1)
        elif res.status_code == 204:
            logger.info('Old DNS record with ID {} deleted successfully'.format(dns_record_id))
    except Exception as ex:
        logger.error('An error occurred trying to delete old DNS record with ID {}. Cause: {}'.format(dns_record_id, ex.__str__()))
        sys.exit(1)


def get_dns_records():
    req_url = DNS_ZONES_URI + FQDN.split('.')[-2] + '_' + FQDN.split('.')[-1] + '/dns_records'
    try:
        return requests.get(req_url, headers=headers).json()
    except Exception as ex:
        logger.error('An error occurred trying to fetch all DNS records. Cause: {}'.format(ex.__str__()))


def extract_target_record_id(records):
    for record in records:
        if FQDN == record['hostname'] and 'A' == record['type']:
            return record['id'], record['value']
    return None, None


if __name__ == '__main__':

    logger.info('----- Executing netlify_ddns -----')

    current_public_ip = get_public_ip_address()

    # fetch all dns records
    records_list = get_dns_records()
    # check if a DNS A record already exists for the provided FQDN
    record_id, record_ip = extract_target_record_id(records_list)

    if record_id is None:  # create a new record
        new_dns_record = create_dns_record(FQDN, current_public_ip)
    elif (record_id is not None) and (current_public_ip != record_ip):  # create new record and delete the old one
        new_dns_record = create_dns_record(FQDN, current_public_ip)
        delete_dns_record(record_id)
    else:
        logger.info('DNS record already present with correct IP for the hostname: {}'.format(FQDN))

    logger.info('----- Script executed successfully -----')
    sys.exit(0)
