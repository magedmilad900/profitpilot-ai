import os
import json
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ProfitPilot AI", page_icon="📈", layout="wide")

# ---------- Visual style ----------
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(120deg,#10243a,#176b63); color: white; margin-bottom: 1rem;}
.hero h1 {margin:0; font-size:2.2rem;}
.hero p {margin:.4rem 0 0 0; opacity:.92;}
.small-note {color:#64748b; font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>📈 ProfitPilot AI</h1><p>Your AI business analyst: turn sales data into clearer, smarter profit decisions.</p></div>', unsafe_allow_html=True)

REQUIRED = {"date", "product", "units", "unit_price", "unit_cost"}

def demo_data():
    return pd.DataFrame([
        ["2026-09-01","Wireless Mouse",18,18,8],
        ["2026-09-02","Desk Lamp",9,32,21],
        ["2026-09-03","Notebook Set",30,7,2.5],
        ["2026-09-04","Wireless Mouse",12,18,8],
        ["2026-09-05","Desk Lamp",5,32,21],
        ["2026-09-06","Water Bottle",22,14,6],
        ["2026-09-07","Notebook Set",35,7,2.5],
        ["2026-09-08","Desk Lamp",4,32,21],
        ["2026-09-09","Water Bottle",17,14,6],
        ["2026-09-10","Wireless Mouse",20,18,8],
        ["2026-09-11","Desk Lamp",3,32,21],
        ["2026-09-12","Notebook Set",27,7,2.5],
        ["2026-09-13","Water Bottle",25,14,6],
        ["2026-09-14","Desk Lamp",6,32,21],
        ["2026-09-15","Wireless Mouse",16,18,8],
        ["2026-09-16","Notebook Set",32,7,2.5],
        ["2026-09-17","Water Bottle",19,14,6],
        ["2026-09-18","Desk Lamp",2,32,21],
        ["2026-09-19","Wireless Mouse",24,18,8],
        ["2026-09-20","Notebook Set",29,7,2.5],
        ["2026-09-21","Water Bottle",21,14,6],
        ["2026-09-22","Desk Lamp",5,32,21],
        ["2026-09-23","Wireless Mouse",14,18,8],
        ["2026-09-24","Notebook Set",34,7,2.5],
        ["2026-09-25","Water Bottle",18,14,6],
    ], columns=["date","product","units","unit_price","unit_cost"])

def normalize(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["units", "unit_price", "unit_cost"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "product", "units", "unit_price", "unit_cost"])
    df = df[(df["units"] >= 0) & (df["unit_price"] >= 0) & (df["unit_cost"] >= 0)]
    df["revenue"] = df["units"] * df["unit_price"]
    df["cost"] = df["units"] * df["unit_cost"]
    df["profit"] = df["revenue"] - df["cost"]
    df["margin_pct"] = (df["profit"] / df["revenue"].replace(0, pd.NA) * 100).fillna(0)
    return df

def business_summary(df):
    product = df.groupby("product", as_index=False).agg(
        units=("units","sum"), revenue=("revenue","sum"), cost=("cost","sum"),
        profit=("profit","sum")
    )
    product["margin_pct"] = (product["profit"] / product["revenue"].replace(0, pd.NA) * 100).fillna(0)
    daily = df.groupby("date", as_index=False).agg(revenue=("revenue","sum"), profit=("profit","sum"))
    total_rev = float(df["revenue"].sum())
    total_profit = float(df["profit"].sum())
    margin = (total_profit / total_rev * 100) if total_rev else 0
    return product.sort_values("profit", ascending=False), daily, total_rev, total_profit, margin

def rules_based_insights(df, products, revenue, profit, margin):
    insights = []
    if len(products):
        best = products.iloc[0]
        worst = products.sort_values("profit").iloc[0]
        insights.append(f"Top profit contributor: {best['product']} generated {best['profit']:,.2f} in gross profit.")
        if worst["product"] != best["product"]:
            insights.append(f"Review {worst['product']}: it generated the lowest total gross profit ({worst['profit']:,.2f}). Check demand, pricing, and supplier costs before changing stock.")
        low_margin = products[products["margin_pct"] < 25]
        if len(low_margin):
            names = ", ".join(low_margin["product"].astype(str).head(3).tolist())
            insights.append(f"Margin watchlist: {names} have gross margins below 25%; test a small price or sourcing change rather than making a large immediate change.")
        high_units = products.sort_values("units", ascending=False).iloc[0]
        insights.append(f"Demand signal: {high_units['product']} sold the most units ({high_units['units']:,.0f}); check inventory availability before promotions.")
    if margin < 20:
        insights.append("Overall gross margin is below 20%. Audit discounts, supplier costs, and product mix.")
    elif margin >= 40:
        insights.append("Overall gross margin is healthy at this snapshot; validate whether sales volume is sufficient to cover fixed operating costs.")
    if len(df) >= 7:
        half = max(1, len(df)//2)
        first = df.sort_values("date").iloc[:half]["profit"].sum()
        second = df.sort_values("date").iloc[half:]["profit"].sum()
        if first and second < first * 0.8:
            insights.append("Recent rows show lower total profit than earlier rows. Check whether this reflects fewer days, seasonality, stockouts, or a genuine decline before acting.")
    return insights

def gemini_insights(api_key, summary_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    prompt = f"""You are a cautious small-business analyst. Analyze the following summarized sales data.
Give 4 concise recommendations. For each, state the evidence, a practical next step, and a caveat.
Do not invent facts, do not claim causation, and label estimates as estimates. Focus on profit, margin, inventory, and experiments.
Data:
{summary_text}
Return plain text with numbered recommendations."""
    try:
        r = requests.post(url, params={"key": api_key}, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=25)
        if r.ok:
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        return f"AI service returned status {r.status_code}. Showing built-in analysis instead."
    except Exception as e:
        return f"Could not reach the AI service ({type(e).__name__}). Showing built-in analysis instead."

with st.sidebar:
    st.header("📂 Your data")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"])
    use_demo = st.toggle("Use built-in demo data", value=True if not uploaded else False)
    st.divider()
    st.header("✨ AI settings")
    api_key = st.text_input("Gemini API key (optional)", type="password", help="Used only for generating AI recommendations. Leave blank to use built-in analysis.")
    st.caption("Get a key from Google AI Studio. Never commit your key to GitHub.")

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        df = normalize(raw)
        data_label = uploaded.name
    elif use_demo:
        df = normalize(demo_data())
        data_label = "Built-in demo dataset"
    else:
        st.info("Upload a CSV or enable the demo dataset in the sidebar.")
        st.stop()
except Exception as exc:
    st.error(f"Could not read this dataset: {exc}")
    st.markdown("Required CSV columns: `date, product, units, unit_price, unit_cost`.")
    st.stop()

if df.empty:
    st.warning("No valid rows found. Check your CSV values and try again.")
    st.stop()

products, daily, revenue, profit, margin = business_summary(df)
st.caption(f"Data source: {data_label} · {len(df):,} valid rows · Gross profit excludes fixed overhead, tax, and shipping unless included in unit_cost.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"${revenue:,.2f}")
c2.metric("Gross profit", f"${profit:,.2f}")
c3.metric("Gross margin", f"{margin:.1f}%")
c4.metric("Units sold", f"{df['units'].sum():,.0f}")

st.subheader("Business performance")
left, right = st.columns(2)
with left:
    fig = px.line(daily, x="date", y=["revenue","profit"], markers=True, title="Revenue vs. gross profit over time")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig2 = px.bar(products.sort_values("profit", ascending=True), x="profit", y="product", orientation="h",
                  color="margin_pct", title="Gross profit by product", labels={"profit":"Gross profit","product":"Product","margin_pct":"Margin %"})
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Product scorecard")
display = products.copy()
for col in ["revenue","cost","profit"]:
    display[col] = display[col].map(lambda x: f"${x:,.2f}")
display["margin_pct"] = display["margin_pct"].map(lambda x: f"{x:.1f}%")
st.dataframe(display, use_container_width=True, hide_index=True)

st.subheader("🧠 AI business recommendations")
rule_insights = rules_based_insights(df, products, revenue, profit, margin)
summary_text = {
    "total_revenue": round(revenue,2),
    "gross_profit": round(profit,2),
    "gross_margin_pct": round(margin,2),
    "product_performance": products.round(2).to_dict(orient="records"),
    "daily_totals": daily.tail(10).round(2).to_dict(orient="records"),
}
if api_key.strip():
    with st.spinner("Analyzing your business summary..."):
        ai_text = gemini_insights(api_key.strip(), json.dumps(summary_text, default=str))
    st.markdown(ai_text)
else:
    st.caption("Built-in evidence-based checks are active. Add a Gemini API key in the sidebar for natural-language AI recommendations.")
    for item in rule_insights:
        st.markdown(f"- {item}")

st.download_button("⬇️ Download product scorecard CSV", data=products.to_csv(index=False).encode("utf-8"),
                   file_name="profitpilot_product_scorecard.csv", mime="text/csv")

with st.expander("CSV format and assumptions"):
    st.markdown("""
    Your CSV must contain these columns:
    - `date`: transaction date (for example, `2026-09-01`)
    - `product`: product name
    - `units`: number of units sold
    - `unit_price`: selling price per unit
    - `unit_cost`: direct cost per unit

    Revenue = units × unit price. Gross profit = revenue − direct cost. Gross margin = gross profit ÷ revenue.
    This prototype provides decision support, not financial advice. Validate data and test recommendations before acting.
    """)
