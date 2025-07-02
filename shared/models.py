from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from typing import Optional, Union
from decimal import Decimal
import uuid


@dataclass
class Transaction:
    """Canonical representation of a single credit-card / bank transaction."""

    txn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    txn_date: date = field(default_factory=date.today)
    amount: float = 0.0
    currency: str = "USD"
    txn_type: str = "debit"  # or "credit"
    merchant: str = ""
    category: str = "Uncategorised"
    source_email: str = ""  # email address of the sender
    raw_email_id: str = ""  # IMAP UID or message-id
    inserted_at: datetime = field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------------------
    # DynamoDB helpers
    # ---------------------------------------------------------------------

    def to_item(self) -> dict:
        """Return a dict ready for boto3.Table.put_item."""
        item = asdict(self)
        # DynamoDB cannot store date/datetime objects directly → serialise
        item["txn_date"] = self.txn_date.isoformat()
        item["inserted_at"] = self.inserted_at.isoformat()
        # use Decimal for numeric fields
        item["amount"] = Decimal(str(self.amount))
        return item

    @classmethod
    def from_item(cls, item: dict) -> "Transaction":
        return cls(
            txn_id=item["txn_id"],
            txn_date=date.fromisoformat(item["txn_date"]),
            amount=float(item["amount"]) if not isinstance(item["amount"], Decimal) else float(item["amount"].quantize(Decimal("0.01"))),
            currency=item.get("currency", "USD"),
            txn_type=item.get("txn_type", "debit"),
            merchant=item.get("merchant", ""),
            category=item.get("category", "Uncategorised"),
            source_email=item.get("source_email", ""),
            raw_email_id=item.get("raw_email_id", ""),
            inserted_at=datetime.fromisoformat(item["inserted_at"]),
        )
