"""Simple Streamlit UI to browse transactions and monthly summary.
Run locally: `streamlit run streamlit_app/app.py`.
On AWS, you can package this as a container (ECS/Fargate) or run on EC2.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import List

import boto3
import pandas as pd
import streamlit as st

# Ensure project root is on PYTHONPATH when Streamlit executes from within this subdir.
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from extractor import CATEGORIES  # provided by extractor.__init__
except ImportError:
    # Fallback if package not discoverable
    from extractor.extract import CATEGORIES

from shared.models import Transaction


def load_transactions() -> List[Transaction]:
    table_name = os.environ.get("DYNAMODB_TABLE", "transactions")
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(table_name)
    resp = table.scan()
    items = resp.get("Items", [])
    txns = [Transaction.from_item(it) for it in items]
    return txns


def save_transaction(txn: Transaction) -> None:
    """Persist a new transaction to DynamoDB."""
    table_name = os.environ.get("DYNAMODB_TABLE", "transactions")
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(table_name)
    table.put_item(Item=txn.to_item())


st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

st.title("💳 Personal Finance Dashboard")

# ------------------------------------------------------------------
# Add Transaction Form
# ------------------------------------------------------------------
with st.expander("➕ Add Transaction", expanded=False):
    with st.form("add_txn"):
        col1, col2 = st.columns(2)
        txn_date = col1.date_input("Date", value=date.today())
        merchant = col2.text_input("Merchant")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        txn_type = st.selectbox("Type", ["debit", "credit"], index=0)
        # Using predefined categories for consistency
        category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index("other") if "other" in CATEGORIES else 0)
        submitted = st.form_submit_button("Add")

    if submitted:
        new_txn = Transaction(
            txn_date=txn_date,
            merchant=merchant,
            amount=float(amount),
            txn_type=txn_type,
            category=category,
        )
        save_transaction(new_txn)
        st.success("Transaction added!")
        # Rerun to refresh UI with new data
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.rerun()

txns = load_transactions()
if not txns:
    st.info("No transactions yet.")
    st.stop()

# DataFrame for tables/charts
rows = [
    {
        "Date": t.txn_date,
        "Merchant": t.merchant,
        "Amount": t.amount if t.txn_type == "debit" else -t.amount,
        "Type": t.txn_type,
        "Category": t.category,
    }
    for t in txns
]
df = pd.DataFrame(rows)

# ------------------------------------------------------------------
# Summary tiles
# ------------------------------------------------------------------
col1, col2 = st.columns(2)
col1.metric("Total Spent", f"${df[df.Amount>0].Amount.sum():,.0f}")
col2.metric("Net", f"${df.Amount.sum():,.0f}")

st.divider()

# Monthly bar chart
st.subheader("Monthly Spend")
# Group by calendar month (YYYY-MM) for clearer labels
month_series = pd.to_datetime(df["Date"]).dt.to_period("M").astype(str)
month_group = df.groupby(month_series)["Amount"].sum().sort_index()
st.bar_chart(month_group)

st.divider()

# Spend by Category
st.subheader("Spend by Category")
cat_group = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
st.bar_chart(cat_group)

st.divider()

# Detailed table
st.subheader("Transactions")
st.dataframe(df.sort_values("Date", ascending=False), hide_index=True)
