"""Enterprise-Grade Email Sender with Attachments, CC/BCC, HTML, Logging, Dry-Run"""

import os
import argparse
import configparser
import logging
import smtplib
from configparser import SectionProxy
from logging.handlers import RotatingFileHandler
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List

# Constants
CONFIG_FILE = 'config.ini'
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'email_sender.log')

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Logging setup
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()],
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_config(path: str) -> SectionProxy:
    """Load configuration from INI file"""
    config = configparser.ConfigParser()
    if not os.path.exists(path):
        logging.error(f'Configuration file not found: {path}')
        raise FileNotFoundError(f'Configuration file not found: {path}')
    config.read(path)
    return config["EMAIL"]

def create_email(
    sender: str,
    receiver: str,
    subject: str,
    body: str,
    attachments: List[str],
    cc: List[str],
    bcc: List[str],
    html_content: str
) -> MIMEMultipart:
    """Create and return an email message"""
    message = MIMEMultipart()
    message['From'] = formataddr(('Sender', sender))
    message['To'] = receiver
    if cc:
        message['Cc'] = ", ".join(cc)
    message['Subject'] = subject

    # Attach message body
    if html_content:
        message.attach(MIMEText(html_content, 'html'))
    else:
        message.attach(MIMEText(body, 'plain'))

    # Attach files
    for file_path in attachments:
        try:
            with open(file_path, 'rb') as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                message.attach(part)
        except Exception as e:
            logging.error(f"Failed to attach {file_path}: {e}")
            continue

    return message

def send_email(
    config: dict,
    message: MIMEMultipart,
    sender: str,
    receiver: str,
    cc: List[str],
    bcc: List[str],
    dry_run: bool = False
) -> None:
    """Send email using SMTP"""
    if dry_run:
        logging.info("Dry run enabled. Email would be sent to: %s", receiver)
        return

    try:
        with smtplib.SMTP(config['SMTP_SERVER'], int(config['SMTP_PORT'])) as server:
            server.starttls()
            server.login(config['USERNAME'], config['PASSWORD'])
            all_recipients = [receiver] + cc + bcc
            server.sendmail(sender, all_recipients, message.as_string())
            logging.info(f"Email sent successfully to {', '.join(all_recipients)}")
    except smtplib.SMTPConnectError:
        logging.error("SMTP server connection failed.")
    except smtplib.SMTPServerDisconnected:
        logging.error("Server disconnected unexpectedly.")
    except smtplib.SMTPAuthenticationError:
        logging.error("Authentication failed.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Send emails with attachments securely.')
    parser.add_argument('--receiver', required=True, help='Email address of the receiver')
    parser.add_argument('--subject', required=True, help='Subject of the email')
    parser.add_argument('--body', required=True, help='Plain text of the email')
    parser.add_argument('--html', help='HTML content of the email')
    parser.add_argument('--attachments', nargs='*', default=[], help='List of file paths to attach')
    parser.add_argument('--cc', nargs='*', default=[], help='CC recipients')
    parser.add_argument('--bcc', nargs='*', default=[], help='BCC recipients')
    parser.add_argument('--dry_run', action='store_true', help='Test without actually sending email')

    args = parser.parse_args()

    try:
        config = load_config(CONFIG_FILE)
        message = create_email(
            sender=config["USERNAME"],
            receiver=args.receiver,
            subject=args.subject,
            body=args.body,
            html_content=args.html or "",
            attachments=args.attachments,
            cc=args.cc,
            bcc=args.bcc
        )
        send_email(
            config=dict(config),
            message=message,
            sender=config['USERNAME'],
            receiver=args.receiver,
            cc=args.cc,
            bcc=args.bcc,
            dry_run=args.dry_run
        )
    except (FileNotFoundError, PermissionError) as fp:
        logging.error(f'File or permission error: {fp}')
    except Exception as e:
        logging.error(f'Unexpected error occurred: {e}')

if __name__ == '__main__':
    main()
