#!/usr/bin/env python3
#------------
# Service notification script for Icinga 2
# Customized for Icinga 2 v2.10.2, InfluxDB 1.7.2 and Graphite
# v0.1 by Philipp Wagner
#
# https://github.com/mmarodin/icinga2-plugins
#
import argparse
import os
import smtplib
import socket
import requests
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# User customization here
FROM = 'icinga@icinga2.fqdn.here'
SERVER = 'localhost'
USERNAME = ''
PASSWORD = ''
ICINGA2BASE = 'http://icinga2.fqdn.here/icingaweb2' # use your icingaweb2 URL
GRAPHITEBASE = 'http://graphite.fqdn.here/render' # for container use http://graphite/render
WIDTH = '640'
HEIGHT = '321'
COLUMN = '144'
DIFFERENCE = str(int(WIDTH) - int(COLUMN))

# Icinga 2 >= 2.7.x uses command line parameters instead of environment variables
text = 'Service notification script for Icinga2'
parser = argparse.ArgumentParser(description=text)
parser.add_argument("--longdatetime", "-d", help="set icinga.long_date_time")
parser.add_argument("--hostname", "-l", help="set host.name")
parser.add_argument("--hostdisplayname", "-n", help="set host.display_name")
parser.add_argument("--serviceoutput", "-o", help="set service.output")
parser.add_argument("--useremail", "-r", help="set user.email")
parser.add_argument("--servicestate", "-s", help="set service.state")
parser.add_argument("--notificationtype", "-t", help="set notification.type")
parser.add_argument("--hostaddress", "-4", help="set address")
parser.add_argument("--hostaddress6", "-6", help="set address6")
parser.add_argument("--notificationauthorname", "-b", help="set notification.author")
parser.add_argument("--notificationcomment", "-c", help="set notification.comment")
parser.add_argument("--icingaweb2url", "-i", help="set notification_icingaweb2url")
parser.add_argument("--mailfrom", "-f", help="set notification_mailfrom")
parser.add_argument("--verbose", "-v", help="set notification_sendtosyslog")
parser.add_argument("--serviceperfdata", "-p", help="set service.perfdata")
parser.add_argument("--servicename", "-e", help="set service.name")
args = parser.parse_args()

if not all([args.longdatetime, args.hostname, args.hostdisplayname, args.serviceoutput, args.useremail, args.servicestate, args.notificationtype]):
    print("Missing required parameters!")
    os.sys.exit(2)

DEBUG = args.verbose

TO = args.useremail

# Logo for Icinga 2 >= 2.6.x
logoImagePath = '/usr/share/icingaweb2/public/img/icinga-logo.png'

if not args.hostaddress:
    args.hostaddress = args.hostname

SUBJECTMESSAGE = f"{args.notificationtype} - HOST {args.hostdisplayname} is {args.servicestate}"

TEXT = '***** Icinga  *****'
TEXT += f'\n\nNotification Type: {args.notificationtype}'
TEXT += f'\n\nHost: {args.hostname}'
TEXT += f'\nAddress: {args.hostaddress}'
TEXT += f'\nState: {args.servicestate}'
TEXT += f'\n\nDate/Time: {args.longdatetime}'
TEXT += f'\n\nAdditional Info: {args.serviceoutput}'
TEXT += f'\n\nComment: [{args.notificationauthorname}] {args.notificationcomment}'

HTML = '<html><head><style type="text/css">'
HTML += '\nbody {text-align: left; font-family: calibri, sans-serif, verdana; font-size: 10pt; color: #7f7f7f;}'
HTML += '\ntable {margin-left: auto; margin-right: auto;}'
HTML += '\na:link {color: #0095bf; text-decoration: none;}'
HTML += '\na:visited {color: #0095bf; text-decoration: none;}'
HTML += '\na:hover {color: #0095bf; text-decoration: underline;}'
HTML += '\na:active {color: #0095bf; text-decoration: underline;}'
HTML += '\nth {font-family: calibri, sans-serif, verdana; font-size: 10pt; text-align:left; white-space: nowrap; color: #535353;}'
HTML += '\nth.icinga {background-color: #0095bf; color: #ffffff; margin-left: 7px; margin-top: 5px; margin-bottom: 5px;}'
HTML += '\nth.perfdata {background-color: #0095bf; color: #ffffff; margin-left: 7px; margin-top: 5px; margin-bottom: 5px; text-align:center;}'
HTML += '\ntd {font-family: calibri, sans-serif, verdana; font-size: 10pt; text-align:left; color: #7f7f7f;}'
HTML += '\ntd.center {text-align:center; white-space: nowrap;}'
HTML += '\ntd.OK {background-color: #44bb77; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.WARNING {background-color: #ffaa44; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.CRITICAL {background-color: #ff5566; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.UNKNOWN {background-color: #aa44ff; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.RECOVERY {background-color: #44bb77; color: #ffffff; margin-left: 2px;}'
HTML += '\n</style></head><body>'
HTML += f'\n<table width={WIDTH}>'

if os.path.exists(logoImagePath):
    HTML += f'\n<tr><th colspan=2 class=icinga width={WIDTH}><img src="cid:icinga2_logo"></th></tr>'

HTML += f'\n<tr><th width={COLUMN}>Notification Type:</th><td class={args.notificationtype}>{args.notificationtype}</td></tr>'
HTML += f'\n<tr><th>Host Name:</th><td>{args.hostname}</td></tr>'
HTML += f'\n<tr><th>Service Name:</th><td>{args.servicename}</td></tr>'
HTML += f'\n<tr><th>Host Status:</th><td>{args.servicestate}</td></tr>'

# Vorbereitende Variable definieren:
serviceoutput_formatted = args.serviceoutput.replace("\n", "<br>")

# Dann im HTML einbinden:
HTML += f'\n<tr><th>Host Data:</th><td><a style="color: #0095bf; text-decoration: none;" href="{ICINGA2BASE}/monitoring/host/show?host={args.hostname}">{serviceoutput_formatted}</a></td></tr>'

HTML += f'\n<tr><th>Hostalias:</th><td><a style="color: #0095bf; text-decoration: none;" href="{ICINGA2BASE}/monitoring/host/show?host={args.hostname}">{args.hostname}</a></td></tr>'
HTML += f'\n<tr><th>IP Address:</th><td>{args.hostaddress}</td></tr>'
HTML += f'\n<tr><th>Event Time:</th><td>{args.longdatetime}</td></tr>'

if args.notificationauthorname and args.notificationcomment:
    HTML += f'\n<tr><th>Comment:</th><td>{args.notificationcomment} ({args.notificationauthorname})</td></tr>'

if args.serviceperfdata:
    HTML += f'\n</table><br>'
    HTML += f'\n<table width={WIDTH}>'
    HTML += f'\n<tr><th colspan=6 class=perfdata>Performance Data</th></tr>'
    HTML += f'\n<tr><th>Label</th><th>Last Value</th><th>Warning</th><th>Critical</th><th>Min</th><th>Max</th></tr>'
    PERFDATALIST = args.serviceperfdata.split(" ")
    for PERFDATA in PERFDATALIST:
        if '=' not in PERFDATA:
            continue
        LABEL, DATA = PERFDATA.split("=")
        DATA_PARTS = DATA.split(";")
        VALUE = DATA_PARTS[0]
        WARNING = DATA_PARTS[1] if len(DATA_PARTS) > 1 else ''
        CRITICAL = DATA_PARTS[2] if len(DATA_PARTS) > 2 else ''
        MIN = DATA_PARTS[3] if len(DATA_PARTS) > 3 else ''
        MAX = DATA_PARTS[4] if len(DATA_PARTS) > 4 else ''
        HTML += f'\n<tr><td>{LABEL}</td><td>{VALUE}</td><td>{WARNING}</td><td>{CRITICAL}</td><td>{MIN}</td><td>{MAX}</td></tr>'

# Definiere den target-Parameter für einen Host dynamisch:
target = f"icinga2.{args.hostname}.host.hostalive.perfdata.rta.value"

# Erstelle die vollständige Graphite-URL mit den gewünschten Query-Parametern:
graphite_url = (
    f"{GRAPHITEBASE}/?width=586"
    f"&height=308"
    f"&from=-6hours"
    f"&lineMode=connected"
    f"&target={target}"
    f"&fgcolor=000000"
    f"&bgcolor=FFFFFF"
    f"&hideNullFromLegend=false"
    f"&yUnitSystem=si"
    f"&connectedLimit="
    f"&majorGridLineColor=000000"
    f"&minorGridLineColor=969696"
    f"&title=HOST {args.hostname}"
)

# Download the Graphite image and encode as base64
response = requests.get(graphite_url)
if response.status_code == 200:
    encoded_image = base64.b64encode(response.content).decode('utf-8')
    HTML += f'\n<tr><td colspan=6><img src="data:image/png;base64,{encoded_image}"></td></tr>'

HTML += f'\n</table><br>'
HTML += f'\n<table width={WIDTH}>'
HTML += f'\n<tr><td class=center>Generated by Icinga 2 and Graphite</td></tr>'
HTML += f'\n</table><br>'
HTML += f'\n</body></html>'

if DEBUG == 'true':
    print(HTML)

# Prepare email
msgRoot = MIMEMultipart('related')
msgRoot['Subject'] = SUBJECTMESSAGE
msgRoot['From'] = FROM
msgRoot['To'] = TO
msgRoot.preamble = 'This is a multi-part message in MIME format.'

msgAlternative = MIMEMultipart('alternative')
msgRoot.attach(msgAlternative)

msgText = MIMEText(TEXT)
msgAlternative.attach(msgText)

msgText = MIMEText(HTML, 'html')
msgAlternative.attach(msgText)

# Attach images
if os.path.exists(logoImagePath):
    with open(logoImagePath, 'rb') as fp:
        msgImage = MIMEImage(fp.read())
    msgImage.add_header('Content-ID', '<icinga2_logo>')
    msgRoot.attach(msgImage)

# Send mail using SMTP
smtp = smtplib.SMTP()
try:
    smtp.connect(SERVER)
except socket.error as e:
    print(f"Unable to connect to SMTP server '{SERVER}': {e.strerror}")
    os.sys.exit(e.errno)
if USERNAME and PASSWORD:
    smtp.login(USERNAME, PASSWORD)
try:
    smtp.sendmail(FROM, TO, msgRoot.as_string())
    smtp.quit()
except Exception as e:
    print(f"Cannot send mail using SMTP: {e}")
    os.sys.exit(e.errno)

os.sys.exit(0)