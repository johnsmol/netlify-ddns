# Netlify DDNS

So you manage to get yourself a nice home lab or a beautiful Raspberry Pi and now you would like
to expose your services to the public Internet for you, or others, to access them from everywhere in the world.
However, your ISP doesn't provide you with a static public IP address, and you don't want to pay for a DDNS service.

Well, this Python script might be a good solution for you, if you have a domain and you use Netlify to manage your DNS. 

This Python script makes use the Netlify public API and allows you
to create and automatically update a Netlify DNS 'A' record associated to the
specified domain in order for it to always point to the public IP
of the system the script is running on.

In this way, you won't have to worry anymore about what your public IP is and just use a dedicated domain to point
at your server to access the exposed services or the system itself.

## Requisites

- Having a registered domain
- Using Netlify as your DNS manager

## Usage

Simply copy the content of ```example.env``` into ```.env``` inserting you Netlify API token and
the fully qualified name for which you want to create the DNS A record on Netlify.

There's no need to create the record manually before the first execution. The script will create it for
you. If it already exists, it will update it if your public IP address is different from the one shown
in the current record for the specified domain.

Since your public IP may change unexpectedly over time, it might be good to invoke this script with a cron job,
in order to always have an updated dns record and avoid downtimes reaching your services.

In case you automate the process it's important to note that the Netlify public API is rate limited to
500 requests per minute. However, for DDNS purposes, an interval of one execution every 5 minutes is more than enough
(and probably even a little overkill).

The script will create a ```netlify_ddns.log``` file for you to monitor the process and debug possible errors.
Log rotation is configured so that every week a new file is generated with a retention of up to three weeks. 

## Useful resources

- Guide to set up cron jobs on ubuntu: [link](https://www.geeksforgeeks.org/how-to-setup-cron-jobs-in-ubuntu/)
- Tool to create cron schedules: [link](https://crontab.guru/every-5-minutes)
