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

from shared.models import Transaction


def load_transactions() -> List[Transaction]:
    table_name = os.environ.get("DYNAMODB_TABLE", "transactions")
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(table_name)
    resp = table.scan()
    items = resp.get("Items", [])
    txns = [Transaction.from_item(it) for it in items]
    return txns


st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

st.title("💳 Personal Finance Dashboard")

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
