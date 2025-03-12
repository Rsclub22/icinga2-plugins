#!/usr/bin/env python3
#------------
# Service notification script for Icinga 2
# Customized for Icinga 2 v2.14 and Icinga Web 2 v2.12, Icingadb 1.2 and Graphite 1.1.10
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
ICINGA2BASE = 'http://icinga2.fqdn.here/icingaweb2'
GRAPHITEBASE = 'http://graphite.fqdn.here/render'
WIDTH = '640'
HEIGHT = '321'
COLUMN = '144'
DIFFERENCE = str(int(WIDTH) - int(COLUMN))

# Icinga 2 >= 2.7.x uses command line parameters
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
parser.add_argument("--servicedisplayname", "-u", help="set service.display_name")
args = parser.parse_args()

if not all([args.longdatetime, args.servicename, args.hostname, args.hostdisplayname,
            args.serviceoutput, args.useremail, args.servicestate, args.notificationtype,
            args.servicedisplayname]):
    print("Missing required parameters!")
    os.sys.exit(2)

DEBUG = args.verbose
TO = args.useremail

if not args.hostaddress:
    args.hostaddress = args.hostname

SUBJECTMESSAGE = f"{args.notificationtype} - {args.hostdisplayname} - {args.servicedisplayname} is {args.servicestate}"

# Prepare plain text message
TEXT = '***** Icinga  *****'
TEXT += f'\n\nNotification Type: {args.notificationtype}'
TEXT += f'\n\nService: {args.servicedisplayname}'
TEXT += f'\n\nHost: {args.hostname}'
TEXT += f'\n\nAddress: {args.hostaddress}'
TEXT += f'\n\nState: {args.servicestate}'
TEXT += f'\n\nDate/Time: {args.longdatetime}'
TEXT += f'\n\nAdditional Info: {args.serviceoutput}'
TEXT += f'\n\nComment: [{args.notificationauthorname}] {args.notificationcomment}'

# Prepare HTML message
HTML = '<html><head><style type="text/css">'
HTML += '\nbody {text-align: left; font-family: Calibri, sans-serif, Verdana; font-size: 10pt; color: #7f7f7f;}'
HTML += '\ntable {margin-left: auto; margin-right: auto;}'
HTML += '\na:link {color: #0095bf; text-decoration: none;}'
HTML += '\na:visited {color: #0095bf; text-decoration: none;}'
HTML += '\na:hover {color: #0095bf; text-decoration: underline;}'
HTML += '\na:active {color: #0095bf; text-decoration: underline;}'
HTML += '\nth {font-family: Calibri, sans-serif, Verdana; font-size: 10pt; text-align: left; white-space: nowrap; color: #535353;}'
HTML += '\nth.icinga {background-color: #0095bf; color: #ffffff; margin: 5px 7px;}'
HTML += '\nth.perfdata {background-color: #0095bf; color: #ffffff; margin: 5px 7px; text-align: center;}'
HTML += '\ntd {font-family: Calibri, sans-serif, Verdana; font-size: 10pt; text-align: left; color: #7f7f7f;}'
HTML += '\ntd.center {text-align: center; white-space: nowrap;}'
HTML += '\ntd.OK {background-color: #44bb77; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.WARNING {background-color: #ffaa44; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.CRITICAL {background-color: #ff5566; color: #ffffff; margin-left: 2px;}'
HTML += '\ntd.UNKNOWN {background-color: #aa44ff; color: #ffffff; margin-left: 2px;}'
HTML += '\n</style></head><body>'
HTML += f'\n<table width="{WIDTH}">'

logoImagePath = '/usr/share/icingaweb2/public/img/icinga-logo.png'
if os.path.exists(logoImagePath):
    HTML += f'\n<tr><th colspan="2" class="icinga" width="{WIDTH}"><img src="cid:icinga2_logo"></th></tr>'

HTML += f'\n<tr><th width="{COLUMN}">Notification Type:</th><td class="{args.servicestate}">{args.notificationtype}</td></tr>'
HTML += f'\n<tr><th>Service Name:</th><td>{args.servicedisplayname}</td></tr>'
HTML += f'\n<tr><th>Service Status:</th><td>{args.servicestate}</td></tr>'
HTML += f'\n<tr><th>Service Data:</th><td><a style="color: #0095bf; text-decoration: none;" href="{ICINGA2BASE}/monitoring/service/show?host={args.hostname}&service={args.servicedisplayname}">{args.serviceoutput.replace(chr(10), "<br>")}</a></td></tr>'
HTML += f'\n<tr><th>Hostalias:</th><td><a style="color: #0095bf; text-decoration: none;" href="{ICINGA2BASE}/monitoring/host/show?host={args.hostname}">{args.hostname}</a></td></tr>'
HTML += f'\n<tr><th>IP Address:</th><td>{args.hostaddress}</td></tr>'
HTML += f'\n<tr><th>Event Time:</th><td>{args.longdatetime}</td></tr>'

if args.notificationauthorname and args.notificationcomment:
    HTML += f'\n<tr><th>Comment:</th><td>{args.notificationcomment} ({args.notificationauthorname})</td></tr>'

# Performance data and Graphite image
HTML += '\n</table><br>'
HTML += f'\n<table width="{WIDTH}">'
HTML += '\n<tr><th colspan="6" class="perfdata">Performance Data</th></tr>'
if args.serviceperfdata:
    PERFDATALIST = args.serviceperfdata.split(" ")
    # Anzeige der Wertetabelle wie bisher
    HTML += '\n<tr><th>Label</th><th>Last Value</th><th>Warning</th><th>Critical</th><th>Min</th><th>Max</th></tr>'
    for perfdata in PERFDATALIST:
        if '=' not in perfdata:
            continue
        LABEL, DATA = perfdata.split("=")
        parts = DATA.split(";")
        VALUE = parts[0] if len(parts) > 0 else ''
        WARNING = parts[1] if len(parts) > 1 else ''
        CRITICAL = parts[2] if len(parts) > 2 else ''
        MIN = parts[3] if len(parts) > 3 else ''
        MAX = parts[4] if len(parts) > 4 else ''
        HTML += f'\n<tr><td>{LABEL}</td><td>{VALUE}</td><td>{WARNING}</td><td>{CRITICAL}</td><td>{MIN}</td><td>{MAX}</td></tr>'
    
    # Für jede Metrik einen separaten Graphite-Plot generieren
    for perfdata in PERFDATALIST:
        if '=' not in perfdata:
            continue
        LABEL, _ = perfdata.split("=")
        # Angepasster Target-Pfad: "icinga2.<hostname>.services.<servicedisplayname>.<servicedisplayname>.perfdata.<LABEL>.value"
        target = f"icinga2.{args.hostname}.services.{args.servicedisplayname}.{args.servicedisplayname}.perfdata.{LABEL}.value"
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
            f"&title=Metric {LABEL}"
        )
        response = requests.get(graphite_url)
        if response.status_code == 200:
            encoded_image = base64.b64encode(response.content).decode('utf-8')
            HTML += f'\n<tr><td colspan="6"><strong>{LABEL}</strong><br><img src="data:image/png;base64,{encoded_image}"></td></tr>'
        else:
            HTML += f'\n<tr><td colspan="6">Cannot fetch Graphite image for {LABEL}, status code: {response.status_code}</td></tr>'
else:
    HTML += f'\n<tr><th width="{COLUMN}" colspan="1">Last Value:</th><td width="{DIFFERENCE}" colspan="5">none</td></tr>'

HTML += '\n</table><br>'
HTML += f'\n<table width="{WIDTH}">'
HTML += '\n<tr><td class="center">Generated by Icinga 2 and Graphite</td></tr>'
HTML += '\n</table><br>'
HTML += '\n</body></html>'

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

msgHTML = MIMEText(HTML, 'html')
msgAlternative.attach(msgHTML)

# Attach logo image if available
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
    os.sys.exit(1)

os.sys.exit(0)