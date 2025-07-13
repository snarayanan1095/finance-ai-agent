"""Email → Transaction extractor using OpenAI function-calling.
This file is **runtime-agnostic** (works locally or in Lambda).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import List, Optional

import openai

from shared.models import Transaction


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------
CATEGORIES = [
    "groceries",
    "dining",
    "utilities",
    "transportation",
    "entertainment",
    "health",
    "subscriptions",
    "shopping",
    "travel",
    "income",
    "investment",
    "other",
]

SCHEMA = {
    "name": "extract_transaction",
    "description": "Extract the first monetary transaction mentioned in the input text and classify its spending category.",
    "parameters": {
        "type": "object",
        "properties": {
            "txn_date": {"type": "string", "description": "YYYY-MM-DD date of the transaction"},
            "amount": {"type": "number"},
            "currency": {"type": "string"},
            "txn_type": {"type": "string", "enum": ["credit", "debit"]},
            "merchant": {"type": "string"},
            "category": {"type": "string", "enum": CATEGORIES},
        },
        "required": ["txn_date", "amount", "txn_type", "category"],
    },
}

SYSTEM_PROMPT = """You are a strict financial parsing engine. Given an email body, you must:
1. If the message confirms an OUTGOING SPEND/CHARGE (money leaving the user, e.g. a credit-card purchase, ATM withdrawal, bill payment), extract ONLY the first such transaction and respond by calling the function `extract_transaction` with JSON arguments that match the schema. Mark it with `txn_type = \"debit\"`.
2. Ignore deposits, refunds, salary credits, statement summaries, reward points/miles notifications, promotions, newsletters, and any message that does NOT confirm money being spent. For those, DO NOT call any function and instead reply with the literal string `NO_TRANSACTION`.
"""

# ---------------------------------------------------------------------------


def extract_transaction(email_text: str, sender: str, *, openai_client: Optional[object] = None) -> Optional[Transaction]:
    """Return a Transaction or None if no transaction found."""

    # Fast path: some banks include obvious patterns we can regex to save cost
    txn = _regex_fast_path(email_text, sender)
    if txn:
        return txn

    # Trim very long bodies to stay within model context window (~16k tokens)
    MAX_CHARS = 8000  # ≈ 2–3k tokens
    if len(email_text) > MAX_CHARS:
        email_text = email_text[:MAX_CHARS]

    client = openai_client or openai
    # openai<1.0.0 uses openai.ChatCompletion.create
    response = client.ChatCompletion.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": email_text},
        ],
        functions=[SCHEMA],
    )
    choice = response["choices"][0]
    msg = choice.get("message", {})
    fc = msg.get("function_call")
    if not fc:
        # Model decided there is no transaction (likely replied with "NO_TRANSACTION")
        return None
    if not fc.get("arguments"):
        return None

    args = json.loads(fc["arguments"])

    # We only store spending (debit) transactions. Skip anything else.
    if args["txn_type"] != "debit":
        return None

    try:
        txn_date = datetime.fromisoformat(args["txn_date"]).date()
    except Exception:
        txn_date = datetime.now(timezone.utc).date()

    return Transaction(
        txn_date=txn_date,
        amount=float(args["amount"]),
        currency=args.get("currency", "USD"),
        txn_type=args["txn_type"],
        merchant=args.get("merchant", ""),
        category=args.get("category", "other"),
        source_email=sender,
    )


# ---------------------------------------------------------------------------
# Cheap regex fallback for known issuers
# ---------------------------------------------------------------------------

PATTERNS = {
    # e.g. "Your HDFC Bank Credit Card ending 1234 has been charged Rs. 4,578.90 at AMAZON on 30-06-2025" → INR debit
    "hdfcbank.com": re.compile(
        r"charged\s+Rs\.\s*([\d,]+\.\d{2})\s+at\s+(?P<merchant>[A-Z0-9 &]+).*?(?P<date>\d{2}-\d{2}-\d{4})",
        re.I,
    ),
}


def _regex_fast_path(body: str, sender: str) -> Optional[Transaction]:
    domain = sender.split("@")[-1]
    pat = PATTERNS.get(domain)
    if not pat:
        return None
    m = pat.search(body)
    if not m:
        return None
    amt = float(m.group(1).replace(",", ""))
    txn_date = datetime.strptime(m.group("date"), "%d-%m-%Y").date()
    return Transaction(
        txn_date=txn_date,
        amount=amt,
        currency="INR",
        txn_type="debit",
        merchant=m.group("merchant"),
        source_email=sender,
    )
