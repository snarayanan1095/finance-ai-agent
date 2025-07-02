"""AWS Lambda entry-point: fetch recent emails, extract transactions, store in DynamoDB.

Environment variables expected (configure in Lambda console or IaC):
--------------------------------------------------------------------
EMAIL_HOST          – IMAP server hostname (e.g. imap.gmail.com)
EMAIL_PORT          – IMAP SSL port (e.g. 993)
EMAIL_USER          – mailbox login
EMAIL_PASSWORD      – mailbox password / app password
IMAP_FOLDER         – optional, defaults to "INBOX"
DYNAMODB_TABLE      – DynamoDB table name (with PK = txn_id)
OPENAI_API_KEY      – OpenAI key (Lambda env var picked up by openai SDK)

You can deploy via Terraform / CloudFormation; see infra/eventbridge.tf for a sketch.
"""
from __future__ import annotations

import email
import imaplib
import logging
import os
import ssl
from datetime import datetime, timedelta
from email.message import Message
from typing import List, Optional

import boto3
import mailparser
from boto3.dynamodb.conditions import Attr

from extractor.extract import extract_transaction
from shared.models import Transaction

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DDB = boto3.resource("dynamodb")

# ---------------------------------------------------------------------------


class EmailFetcher:
    def __init__(self):
        self.host = os.environ["EMAIL_HOST"]
        self.port = int(os.environ.get("EMAIL_PORT", 993))
        self.user = os.environ["EMAIL_USER"]
        self.password = os.environ["EMAIL_PASSWORD"]
        self.folder = os.environ.get("IMAP_FOLDER", "INBOX")

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

    # ------------------------------------------------------------------
    def fetch_recent(self, days: int = 1) -> List[tuple[str, Message]]:
        """Return list of (uid, Message) from the last *days* days."""
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


# ---------------------------------------------------------------------------


def save_transaction(table, txn: Transaction) -> None:
    """Put item only if it does not already exist (idempotent)."""
    try:
        table.put_item(
            Item=txn.to_item(),
            ConditionExpression=Attr("txn_id").not_exists(),
        )
        LOGGER.info("Saved %s %.2f %s", txn.merchant, txn.amount, txn.txn_type)
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        LOGGER.info("Duplicate txn %s skipped", txn.txn_id)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):  # noqa: D401  # AWS entrypoint name fixed
    table_name = os.environ["DYNAMODB_TABLE"]
    table = DDB.Table(table_name)

    with EmailFetcher() as fetcher:
        for uid, msg in fetcher.fetch_recent():
            sender = email.utils.parseaddr(msg.get("From"))[1]
            # Flatten email body (plain pref first else html)
            body = mailparser.parse_from_bytes(msg.as_bytes()).body

            txn = extract_transaction(body, sender)
            if txn is None:
                continue
            txn.raw_email_id = uid  # store IMAP UID to deduplicate in future
            save_transaction(table, txn)

    return {
        "statusCode": 200,
        "body": "Processed emails",
    }
