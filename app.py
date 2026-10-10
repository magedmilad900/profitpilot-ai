from __future__ import annotations

import html
import io
import re
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="ProfitPilot — AI + Business", page_icon="PF", layout="wide")

st.markdown(
    """
<style>
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
.hero { padding: 1.45rem 1.6rem; border-radius: 14px; background:#111; color:white; margin-bottom:1rem; }
.hero h1 { margin:0; font-size:2.15rem; letter-spacing:-.04em; } .hero p { margin:.4rem 0 0; opacity:.9; }
.metric-card { border:1px solid #e5e7eb; border-radius:14px; padding:1rem; background:#fff; }
.insight { border-left:4px solid #111; background:#f5f5f5; padding:.75rem 1rem; border-radius:8px; margin:.45rem 0; }
.risk, .loss { border-left-color:#555; background:#eeeeee; }
.chat-shell { border:1px solid #e5e7eb; border-radius:15px; padding:.7rem 1rem; background:#fafafa; }
.small-note { color:#64748b; font-size:.86rem; }
.source { font-size:.78rem; color:#475569; }
</style>
""",
    unsafe_allow_html=True,
)

REQUIRED = {"date", "product", "units", "unit_price", "unit_cost"}


def demo_data() -> pd.DataFrame:
    rows = [
        ["2026-09-01", "Wireless Mouse", 18, 18, 8, 9], ["2026-09-02", "Desk Lamp", 9, 32, 21, 18],
        ["2026-09-03", "Notebook Set", 30, 7, 2.5, 5], ["2026-09-04", "Wireless Mouse", 12, 18, 8, 7],
        ["2026-09-05", "Desk Lamp", 5, 32, 21, 14], ["2026-09-06", "Water Bottle", 22, 14, 6, 8],
        ["2026-09-07", "Notebook Set", 35, 7, 2.5, 5], ["2026-09-08", "Desk Lamp", 4, 32, 21, 13],
        ["2026-09-09", "Water Bottle", 17, 14, 6, 7], ["2026-09-10", "Wireless Mouse", 20, 18, 8, 10],
        ["2026-09-11", "Desk Lamp", 3, 32, 21, 12], ["2026-09-12", "Notebook Set", 27, 7, 2.5, 5],
        ["2026-09-13", "Water Bottle", 25, 14, 6, 8], ["2026-09-14", "Desk Lamp", 6, 32, 21, 16],
        ["2026-09-15", "Wireless Mouse", 16, 18, 8, 8], ["2026-09-16", "Notebook Set", 32, 7, 2.5, 5],
        ["2026-09-17", "Water Bottle", 19, 14, 6, 8], ["2026-09-18", "Desk Lamp", 2, 32, 21, 12],
        ["2026-09-19", "Wireless Mouse", 24, 18, 8, 11], ["2026-09-20", "Notebook Set", 29, 7, 2.5, 5],
        ["2026-09-21", "Water Bottle", 21, 14, 6, 8], ["2026-09-22", "Desk Lamp", 5, 32, 21, 14],
        ["2026-09-23", "Wireless Mouse", 14, 18, 8, 8], ["2026-09-24", "Notebook Set", 34, 7, 2.5, 5],
        ["2026-09-25", "Water Bottle", 18, 14, 6, 7],
    ]
    return pd.DataFrame(rows, columns=["date", "product", "units", "unit_price", "unit_cost", "operating_expense"])


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    expense_aliases = ["operating_expense", "operating_expenses", "expense", "expenses", "overhead", "fixed_expense"]
    expense_column = next((column for column in expense_aliases if column in df.columns), None)
    df["operating_expense"] = df[expense_column] if expense_column else 0
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["units", "unit_price", "unit_cost", "operating_expense"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["date", "product", "units", "unit_price", "unit_cost", "operating_expense"])
    df = df[(df["units"] >= 0) & (df["unit_price"] >= 0) & (df["unit_cost"] >= 0) & (df["operating_expense"] >= 0)]
    df["revenue"] = df["units"] * df["unit_price"]
    df["cost"] = df["units"] * df["unit_cost"]
    df["gross_profit"] = df["revenue"] - df["cost"]
    df["net_profit"] = df["gross_profit"] - df["operating_expense"]
    df["margin_pct"] = (df["gross_profit"] / df["revenue"].replace(0, pd.NA) * 100).fillna(0)
    df["net_margin_pct"] = (df["net_profit"] / df["revenue"].replace(0, pd.NA) * 100).fillna(0)
    return df


def summarize(df: pd.DataFrame):
    products = df.groupby("product", as_index=False).agg(
        units=("units", "sum"), revenue=("revenue", "sum"), cost=("cost", "sum"),
        gross_profit=("gross_profit", "sum"), operating_expense=("operating_expense", "sum"),
        net_profit=("net_profit", "sum"),
    )
    products["margin_pct"] = (products["gross_profit"] / products["revenue"].replace(0, pd.NA) * 100).fillna(0)
    products["net_margin_pct"] = (products["net_profit"] / products["revenue"].replace(0, pd.NA) * 100).fillna(0)
    daily = df.groupby("date", as_index=False).agg(
        revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"),
        operating_expense=("operating_expense", "sum"), net_profit=("net_profit", "sum"),
    )
    revenue = float(df["revenue"].sum())
    gross_profit = float(df["gross_profit"].sum())
    expenses = float(df["operating_expense"].sum())
    net_profit = float(df["net_profit"].sum())
    margin = (gross_profit / revenue * 100) if revenue else 0
    return products.sort_values("net_profit", ascending=False), daily, revenue, gross_profit, expenses, net_profit, margin


def evidence_insights(df, products, revenue, gross_profit, expenses, net_profit, margin) -> list[tuple[str, str]]:
    insights: list[tuple[str, str]] = []
    if len(products):
        best = products.iloc[0]
        worst = products.sort_values("net_profit").iloc[0]
        insights.append(("good", f"{best['product']} is the strongest profit contributor, generating ${best['net_profit']:,.2f} net profit after allocated operating expenses."))
        if worst["net_profit"] < 0:
            insights.append(("loss", f"{worst['product']} is losing ${abs(worst['net_profit']):,.2f}. Its gross margin is {worst['margin_pct']:.1f}%, so review its price, supplier cost, and promotion spend before scaling it."))
        elif worst["product"] != best["product"]:
            insights.append(("risk", f"{worst['product']} is the weakest product by net profit (${worst['net_profit']:,.2f}). Test a small pricing or sourcing change before committing more inventory."))
        low_margin = products[products["margin_pct"] < 25]
        if len(low_margin):
            names = ", ".join(low_margin["product"].astype(str).head(3).tolist())
            insights.append(("risk", f"Margin watchlist: {names} are below 25% gross margin. A small price or supplier-cost experiment is safer than a large immediate change."))
        high_units = products.sort_values("units", ascending=False).iloc[0]
        insights.append(("good", f"{high_units['product']} has the strongest demand signal with {high_units['units']:,.0f} units sold. Protect its stock and test bundles with a higher-margin product."))
    if revenue and expenses / revenue > 0.25:
        insights.append(("risk", f"Operating expenses consume {expenses / revenue * 100:.1f}% of revenue. Separate recurring overhead from campaign spend and cut the lowest-return line first."))
    if net_profit < 0:
        insights.append(("loss", "The business is net-negative in this snapshot. Prioritize stopping the largest loss driver, then protect the best seller; do not discount everything at once."))
    elif margin < 20:
        insights.append(("risk", "Overall gross margin is below 20%. Audit discounts, supplier costs, and product mix before trying to buy more volume."))
    else:
        insights.append(("good", f"Gross margin is {margin:.1f}%. Keep testing volume and pricing, but confirm that operating expenses are covered consistently."))
    return insights


def search_web(query: str) -> list[dict[str, str]]:
    """Best-effort public search with no API key. Search is optional and never blocks analysis."""
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/", params={"q": query},
            headers={"User-Agent": "ProfitPilot/1.0"}, timeout=12,
        )
        response.raise_for_status()
        results = []
        pattern = re.compile(r'class="result__a" href="//duckduckgo\.com/l/\?uddg=([^"&]+).*?>(.*?)</a>', re.S)
        for encoded_url, title in pattern.findall(response.text)[:5]:
            results.append({"title": re.sub(r"<.*?>", "", html.unescape(title)), "url": html.unescape(encoded_url)})
        return results
    except Exception:
        return []


def build_action_plan(products, net_profit: float, insights: list[tuple[str, str]]) -> list[str]:
    actions = []
    weakest = products.sort_values("net_profit").iloc[0] if len(products) else None
    strongest = products.sort_values("net_profit", ascending=False).iloc[0] if len(products) else None
    if weakest is not None and weakest["net_profit"] < 0:
        actions.append(f"Pause extra promotion for {weakest['product']} for one week and review its unit cost and price.")
    if strongest is not None:
        actions.append(f"Protect stock for {strongest['product']} and test a bundle with the weakest-margin product.")
    actions.append("Track revenue, gross profit, operating expense, and net profit weekly in the same format.")
    actions.append("Run one small experiment at a time; compare the result with the previous period before scaling.")
    if net_profit < 0:
        actions.insert(0, "Stop the largest loss driver first; growth before fixing contribution margin will make the loss larger.")
    return [f"{index}. {action}" for index, action in enumerate(actions, start=1)]


def assistant_reply(question: str, df, products, daily, revenue, gross_profit, expenses, net_profit, margin, insights) -> tuple[str, list[dict[str, str]]]:
    q = question.lower().strip()
    weak = products.sort_values("net_profit").iloc[0]
    best = products.sort_values("net_profit", ascending=False).iloc[0]
    wants_search = any(word in q for word in ["search", "research", "latest", "current", "competitor", "market", "trend", "بحث", "السوق"])
    sources = search_web(question) if wants_search else []
    if any(word in q for word in ["why", "loss", "losing", "problem", "خسر", "خسارة", "المشكلة"]):
        answer = f"Based on your data, the main issue is **{weak['product']}**. It made ${weak['net_profit']:,.2f} net profit after expenses, with a {weak['margin_pct']:.1f}% gross margin. Total net profit is ${net_profit:,.2f}. I would review its price, supplier cost, and promotion spend first — not discount every product."
    elif any(word in q for word in ["best", "top", "strong", "أحسن", "الأفضل"]):
        answer = f"**{best['product']}** is your strongest profit driver: ${best['net_profit']:,.2f} net profit and {best['units']:,.0f} units sold. Protect its availability, then test a bundle that lifts the weaker products without lowering its price."
    elif any(word in q for word in ["profit", "margin", "ربح", "هامش"]):
        answer = f"Revenue is **${revenue:,.2f}**, gross profit is **${gross_profit:,.2f}**, operating expenses are **${expenses:,.2f}**, and net profit is **${net_profit:,.2f}**. Gross margin is **{margin:.1f}%**. The next decision should focus on contribution after expenses, not revenue alone."
    elif any(word in q for word in ["next", "should", "plan", "action", "اعمل", "خطوة", "خطة"]):
        answer = "Here is a practical next-step plan:\n\n" + "\n".join(build_action_plan(products, net_profit, insights))
    elif any(word in q for word in ["data", "file", "csv", "بيانات", "ملف"]):
        answer = f"I analyzed {len(df):,} valid rows across {products['product'].nunique()} products. I found {products['net_profit'].lt(0).sum()} product(s) with negative net profit, and the overall business net profit is ${net_profit:,.2f}. Ask me why you are losing, which product is strongest, or what to do next."
    else:
        answer = f"I read your message. In this dataset, revenue is ${revenue:,.2f}, net profit is ${net_profit:,.2f}, and the main product to review is {weak['product']}. You can ask me in plain English about losses, profit, products, the next step, or research a market topic."
    if sources:
        answer += "\n\nI also found a few public web results related to your question; treat them as context, not proof about your business."
    return answer, sources


# ---------- Sidebar: data input ----------
with st.sidebar:
    st.header("Your data")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"])
    st.caption("Upload a file to analyze it. Without a file, the built-in demo loads automatically.")
    st.divider()
    st.subheader("Expected columns")
    st.caption("Required: date, product, units, unit_price, unit_cost. Optional: operating_expense or expense.")
    st.caption("DEMO MODE · No API key · Explainable local analysis")

try:
    if uploaded is not None:
        df = normalize(pd.read_csv(uploaded))
        data_label = uploaded.name
    else:
        df = normalize(demo_data())
        data_label = "Built-in demo dataset"
except Exception as exc:
    st.error(f"Could not read this dataset: {exc}")
    st.markdown("Required columns: `date, product, units, unit_price, unit_cost`. Optional: `operating_expense`.")
    st.stop()

if df.empty:
    st.warning("No valid rows found. Check your CSV values and try again.")
    st.stop()

products, daily, revenue, gross_profit, expenses, net_profit, margin = summarize(df)
insights = evidence_insights(df, products, revenue, gross_profit, expenses, net_profit, margin)

st.markdown('<div class="hero"><h1>ProfitPilot</h1><p>AI + Business Demo · Find the money leak, understand why, and choose the next best move.</p></div>', unsafe_allow_html=True)
st.caption(f"Data source: {data_label} · {len(df):,} valid rows · Gross profit excludes fixed overhead not included in your file.")

# ---------- Real conversational assistant ----------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [{"role": "assistant", "content": "Hi — I’ve loaded your business data. Ask me why profits are down, which product is weakest, or what to do next." , "sources": []}]

st.subheader("Ask ProfitPilot")
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for source in message.get("sources", []):
            st.markdown(f"<div class='source'>• <a href='{html.escape(source['url'], quote=True)}' target='_blank'>{html.escape(source['title'])}</a></div>", unsafe_allow_html=True)

question = st.chat_input("Ask anything about your business or search a market topic…")
if question:
    st.session_state.chat_messages.append({"role": "user", "content": question, "sources": []})
    answer, sources = assistant_reply(question, df, products, daily, revenue, gross_profit, expenses, net_profit, margin, insights)
    st.session_state.chat_messages.append({"role": "assistant", "content": answer, "sources": sources})
    st.rerun()

# ---------- Dashboard ----------
st.subheader("Business snapshot")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", f"${revenue:,.2f}")
c2.metric("Gross profit", f"${gross_profit:,.2f}")
c3.metric("Operating expense", f"${expenses:,.2f}")
c1.metric("Net profit", f"${net_profit:,.2f}")
c5.metric("Gross margin", f"{margin:.1f}%")

st.subheader("What the data is telling us")
for kind, text in insights:
    css_class = "insight loss" if kind == "loss" else "insight risk" if kind == "risk" else "insight"
    st.markdown(f"<div class='{css_class}'>{html.escape(text)}</div>", unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    fig = px.line(daily, x="date", y=["revenue", "net_profit"], markers=True, title="Revenue vs. net profit", color_discrete_sequence=["#111111", "#777777"])
    fig.update_layout(legend_title_text="Metric", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, width="stretch")
with right:
    chart = products.sort_values("net_profit", ascending=True)
    fig2 = px.bar(chart, x="net_profit", y="product", orientation="h", title="Net profit by product", labels={"net_profit": "Net profit", "product": "Product"}, color_discrete_sequence=["#111111"])
    fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig2, width="stretch")

st.subheader("Product scorecard")
display = products.copy()
for column in ["revenue", "cost", "gross_profit", "operating_expense", "net_profit"]:
    display[column] = display[column].map(lambda value: f"${value:,.2f}")
display["margin_pct"] = display["margin_pct"].map(lambda value: f"{value:.1f}%")
display["net_margin_pct"] = display["net_margin_pct"].map(lambda value: f"{value:.1f}%")
st.dataframe(display, width="stretch", hide_index=True)

st.subheader("Recommended action plan")
for step in build_action_plan(products, net_profit, insights):
    st.markdown(step)

st.download_button("Download product scorecard CSV", data=products.to_csv(index=False).encode("utf-8"), file_name="profitpilot_product_scorecard.csv", mime="text/csv", width="stretch")

with st.expander("CSV format and assumptions"):
    st.markdown("""
Your CSV must contain:

- `date`: transaction date, for example `2026-09-01`
- `product`: product name
- `units`: number of units sold
- `unit_price`: selling price per unit
- `unit_cost`: direct cost per unit
- `operating_expense` (optional): daily expense, overhead, or campaign cost

Revenue = units × unit price. Gross profit = revenue − direct cost. Net profit = gross profit − operating expense. This is decision support, not financial advice; validate the data before acting.
""")
