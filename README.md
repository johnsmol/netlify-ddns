# Netlify DDNS

A lightweight Python script that implements Dynamic DNS (DDNS) for domains managed by Netlify. It automatically keeps a DNS `A` record (IPv4) and `AAAA` record (IPv6) pointed at the current public IP address of the machine running it — no paid DDNS service required.

## How it works

On each run the script:

1. Fetches the machine's current public IPv4 and IPv6 addresses from [ipify](https://www.ipify.org/)
2. Retrieves all DNS records for the configured domain from the Netlify API
3. For each record type (`A` / `AAAA`):
   - Creates the record if it does not exist
   - Replaces it if the IP has changed
   - Does nothing if it is already up to date
4. Writes a timestamped entry to `netlify_ddns.log`

IPv6 is handled gracefully: if the machine has no public IPv6 address the `AAAA` update is skipped with a warning and the script continues normally.

## Requirements

- Python 3.9+
- A domain registered with Netlify as the DNS provider
- A Netlify personal access token with DNS write permissions ([create one here](https://app.netlify.com/user/applications#personal-access-tokens))

## Installation

```bash
git clone https://github.com/johnsmol/netlify-ddns.git
cd netlify-ddns
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy the example environment file and fill in your values:

```bash
cp example.env .env
```

`.env` contents:

```env
FQDN="home.example.com"
NETLIFY_API_TOKEN="your-netlify-api-token"
```

| Variable | Description |
|---|---|
| `FQDN` | The fully-qualified domain name to keep updated (e.g. `home.example.com`) |
| `NETLIFY_API_TOKEN` | Netlify personal access token with DNS write permissions |

The record does not need to exist beforehand — the script creates it on the first run.

## Running manually

```bash
python main.py
```

Output is written to `netlify_ddns.log` in the same directory. Logs rotate daily with a two-day retention window.

## Deploying on Ubuntu Server with cron

The recommended setup is to run the script every 5 minutes via cron. The Netlify API is rate-limited to 500 requests per minute; one execution every 5 minutes is well within that limit.

### 1. Clone and install

```bash
cd /opt
sudo git clone https://github.com/johnsmol/netlify-ddns.git
sudo chown -R $USER:$USER /opt/netlify-ddns
cd /opt/netlify-ddns
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 2. Configure

```bash
cp /opt/netlify-ddns/example.env /opt/netlify-ddns/.env
nano /opt/netlify-ddns/.env
```

### 3. Test the script

```bash
/opt/netlify-ddns/venv/bin/python /opt/netlify-ddns/main.py
cat /opt/netlify-ddns/netlify_ddns.log
```

Confirm that the log shows a successful run before enabling the cron job.

### 4. Add the cron job

Open the crontab editor:

```bash
crontab -e
```

Add the following line:

```
*/5 * * * * /opt/netlify-ddns/venv/bin/python /opt/netlify-ddns/main.py
```

Save and exit. Verify the job is registered:

```bash
crontab -l
```

### 5. Monitor

```bash
# Follow the log in real time
tail -f /opt/netlify-ddns/netlify_ddns.log

# Check the last recorded IP update
grep "created successfully" /opt/netlify-ddns/netlify_ddns.log | tail -5
```

## Development

Install development dependencies (includes `pytest`):

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

## Logging

All runs append to `netlify_ddns.log` in the project directory. The log rotates daily and retains the two most recent files. Each entry follows the format:

```
2024-11-01 12:00:01,234 - netlify_ddns - INFO - System current public IPv4 address is: 1.2.3.4
2024-11-01 12:00:01,891 - netlify_ddns - INFO - A record already up-to-date for hostname: home.example.com
```

## License

MIT — see [LICENSE.md](LICENSE.md).
