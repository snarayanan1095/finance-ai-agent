"""
Standalone script to fetch recent emails, extract transactions, and save them.
Run this script locally or schedule with cron.
"""
import os
import email
import logging
import ssl
from datetime import datetime, timedelta
from email.message import Message
from typing import List
import mailparser
from dotenv import load_dotenv
from extractor.extract import extract_transaction
from shared.models import Transaction

# Load environment variables from .env file
load_dotenv()

EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 993))
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "INBOX")

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

class EmailFetcher:
    def __init__(self):
        self.host = EMAIL_HOST
        self.port = EMAIL_PORT
        self.user = EMAIL_USER
        self.password = EMAIL_PASSWORD
        self.folder = IMAP_FOLDER

    def __enter__(self):
        context = ssl.create_default_context()
        self.conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
        self.conn.login(self.user, self.password)
        self.conn.select(self.folder)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.conn.close()
        finally:
            self.conn.logout()

    def fetch_recent(self, days: int = 1) -> List[tuple[str, Message]]:
        since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%d-%b-%Y")
        typ, msg_ids = self.conn.search(None, f"SINCE {since_date}")
        if typ != "OK":
            LOGGER.warning("IMAP search failed: %s", typ)
            return []
        ids = msg_ids[0].split()
        LOGGER.info("Found %s recent emails", len(ids))
        out: List[tuple[str, Message]] = []
        for uid in ids:
            typ, data = self.conn.fetch(uid, "(RFC822)")
            if typ != "OK":
                continue
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            out.append((uid.decode(), msg))
        return out

def main():
    with EmailFetcher() as fetcher:
        for uid, msg in fetcher.fetch_recent():
            sender = email.utils.parseaddr(msg.get("From"))[1]
            body = mailparser.parse_from_bytes(msg.as_bytes()).body
            txn = extract_transaction(body, sender)
            if txn is None:
                continue
            txn.raw_email_id = uid
            txn.txn_id = uid
            # TODO: Save transaction locally (e.g., to a file or database)
            print(f"Transaction: {txn}")

if __name__ == "__main__":
    main()
