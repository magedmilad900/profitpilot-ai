import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="ProfitPilot", page_icon="💬", layout="wide")

st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#fff !important;}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {background:#f7f7f8 !important;}
[data-testid="stSidebar"] {border-right:1px solid #ececef;}
.block-container {max-width:900px; padding-top:1.4rem; padding-bottom:6rem;}
.brand {font-size:1.25rem;font-weight:700;letter-spacing:-.5px;padding:.5rem 0 1rem;}
.brand span {display:inline-flex;background:#202123;color:white;border-radius:9px;width:31px;height:31px;align-items:center;justify-content:center;margin-right:8px;}
.welcome {text-align:center;padding:3rem .5rem 1.5rem;}
.welcome h1 {font-size:2.1rem;letter-spacing:-1px;font-weight:650;}
.welcome p {color:#777;font-size:1rem;}
.stButton>button {border-radius:14px;background:white;border:1px solid #e5e5e8;color:#202123;min-height:2.7rem;}
.stButton>button:hover {background:#f8f8f9;border-color:#c7c7cd;}
div[data-testid="stChatInput"] {border-radius:18px!important;border:1px solid #dedee3!important;box-shadow:0 4px 20px #00000008;}
div[data-testid="stChatMessage"] {padding:.7rem 0;border:0;}
div[data-testid="stMetric"] {border:1px solid #eee;border-radius:12px;padding:.8rem;background:#fafafa;}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="brand"><span>↗</span>ProfitPilot</div>', unsafe_allow_html=True)

REQUIRED = {"date", "product", "units", "unit_price", "unit_cost"}

def demo_data():
    return pd.DataFrame([
        ["2026-09-01","Wireless Mouse",18,18,8], ["2026-09-02","Desk Lamp",9,32,21],
        ["2026-09-03","Notebook Set",30,7,2.5], ["2026-09-04","Wireless Mouse",12,18,8],
        ["2026-09-05","Desk Lamp",5,32,21], ["2026-09-06","Water Bottle",22,14,6],
        ["2026-09-07","Notebook Set",35,7,2.5], ["2026-09-08","Desk Lamp",4,32,21],
        ["2026-09-09","Water Bottle",17,14,6], ["2026-09-10","Wireless Mouse",20,18,8],
        ["2026-09-11","Desk Lamp",3,32,21], ["2026-09-12","Notebook Set",27,7,2.5],
        ["2026-09-13","Water Bottle",25,14,6], ["2026-09-14","Desk Lamp",6,32,21],
        ["2026-09-15","Wireless Mouse",16,18,8], ["2026-09-16","Notebook Set",32,7,2.5],
        ["2026-09-17","Water Bottle",19,14,6], ["2026-09-18","Desk Lamp",2,32,21],
        ["2026-09-19","Wireless Mouse",24,18,8], ["2026-09-20","Notebook Set",29,7,2.5],
        ["2026-09-21","Water Bottle",21,14,6], ["2026-09-22","Desk Lamp",5,32,21],
        ["2026-09-23","Wireless Mouse",14,18,8], ["2026-09-24","Notebook Set",34,7,2.5],
        ["2026-09-25","Water Bottle",18,14,6],
    ], columns=["date","product","units","unit_price","unit_cost"])

def prepare_data(frame):
    frame = frame.copy()
    frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for col in ["units", "unit_price", "unit_cost"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["date", "product", "units", "unit_price", "unit_cost"])
    frame = frame[(frame["units"] >= 0) & (frame["unit_price"] >= 0) & (frame["unit_cost"] >= 0)]
    frame["revenue"] = frame["units"] * frame["unit_price"]
    frame["cost"] = frame["units"] * frame["unit_cost"]
    frame["profit"] = frame["revenue"] - frame["cost"]
    frame["margin_pct"] = (frame["profit"] / frame["revenue"].replace(0, pd.NA) * 100).fillna(0)
    return frame

def summarize(frame):
    if frame.empty:
        return {"revenue":0,"profit":0,"margin":0,"units":0,"products":pd.DataFrame(),"daily":pd.DataFrame()}
    products = frame.groupby("product", as_index=False).agg(
        units=("units","sum"), revenue=("revenue","sum"), cost=("cost","sum"), profit=("profit","sum"))
    products["margin_pct"] = (products["profit"] / products["revenue"].replace(0, pd.NA) * 100).fillna(0)
    daily = frame.groupby("date", as_index=False).agg(revenue=("revenue","sum"), profit=("profit","sum"))
    revenue, profit = float(frame["revenue"].sum()), float(frame["profit"].sum())
    return {"revenue":revenue,"profit":profit,"margin":profit/revenue*100 if revenue else 0,
            "units":float(frame["units"].sum()),"products":products.sort_values("profit",ascending=False),"daily":daily}

def basic_answer(question, data, frame):
    products = data["products"]
    rev, prof, margin = data["revenue"], data["profit"], data["margin"]
    q = question.lower()
    if frame.empty:
        return "I can chat with you, but I need sales data to calculate real business numbers. Upload a CSV from the left, or turn on demo data to try me."
    if any(x in q for x in ["hello", "hi", "hey", "good morning", "how are you"]):
        return "Hey! 😊 I'm doing well, thanks. What would you like to figure out about your business today?"
    if any(x in q for x in ["profit", "revenue", "sales", "margin", "ربح", "مبيعات"]):
        return (f"Here’s the quick picture: your revenue is **{rev:,.2f}**, gross profit is **{prof:,.2f}**, "
                f"and gross margin is **{margin:.1f}%**. Gross profit does not include fixed overhead or taxes unless they’re included in your unit costs.")
    if any(x in q for x in ["best", "top", "product", "most profitable", "أفضل", "منتج"]):
        best = products.iloc[0]
        worst = products.sort_values("profit").iloc[0]
        return (f"Your strongest product by total gross profit is **{best['product']}** "
                f"({best['profit']:,.2f} profit, {best['margin_pct']:.1f}% margin). "
                f"**{worst['product']}** is currently the lowest by total gross profit. I’d check demand and costs before making a decision.")
    if any(x in q for x in ["grow", "growth", "marketing", "increase", "improve", "نمو", "تسويق"]):
        return ("Here’s a practical place to start:\n\n1. Pick one product with a healthy margin.\n"
                "2. Run a small marketing test for one week.\n3. Track the extra profit—not just clicks or sales.\n\n"
                "I don’t have your ad spend or customer data yet, so treat this as a test, not a guarantee.")
    best = products.iloc[0]
    return (f"Let’s look at this together. Your revenue is **{rev:,.2f}**, gross profit is **{prof:,.2f}**, "
            f"and gross margin is **{margin:.1f}%**. **{best['product']}** currently contributes the most gross profit. "
            "Ask me about a product, your margins, sales trends, or ways to grow.")

def ai_answer(api_key, messages, data):
    p = data["products"]
    summary = {
        "total_revenue": round(data["revenue"],2), "gross_profit":round(data["profit"],2),
        "gross_margin_percent":round(data["margin"],2), "units_sold":round(data["units"],2),
        "product_performance":p.round(2).to_dict(orient="records") if not p.empty else [],
        "daily_totals":data["daily"].tail(14).round(2).to_dict(orient="records") if not data["daily"].empty else []
    }
    instruction = (
        "You are ProfitPilot, a friendly, practical small-business advisor. Speak in simple, natural English. "
        "Be warm and human, not robotic. Answer the user's question directly. Use the supplied sales data for calculations; "
        "never invent facts. Give clear next steps and mention uncertainty. Keep answers concise unless asked for detail. "
        "If the user writes Arabic, answer in Arabic. Sales summary: " + json.dumps(summary, default=str)
    )
    contents = [{"role":"user","parts":[{"text":instruction}]}]
    for m in messages[-12:]:
        contents.append({"role":"model" if m["role"]=="assistant" else "user",
                         "parts":[{"text":m["content"]}]})
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    try:
        res = requests.post(endpoint, params={"key":api_key},
                            json={"contents":contents,"generationConfig":{"temperature":0.65}},
                            timeout=35)
        if res.ok:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return basic_answer(messages[-1]["content"], data, pd.DataFrame() if p.empty else pd.DataFrame({"x":[1]})) if False else f"Gemini returned an error ({res.status_code}). Check your API key and try again."
    except Exception:
        return "I couldn't connect to Gemini right now. Please check your connection and try again."

if "conversations" not in st.session_state:
    st.session_state.conversations = [{"id":1,"title":"New chat","messages":[]}]
    st.session_state.active_id = 1
    st.session_state.counter = 2

with st.sidebar:
    if st.button("＋  New chat", use_container_width=True):
        st.session_state.conversations.insert(0, {"id":st.session_state.counter,"title":"New chat","messages":[]})
        st.session_state.active_id = st.session_state.counter
        st.session_state.counter += 1
        st.rerun()
    st.markdown("---")
    st.caption("YOUR CHATS")
    for conversation in st.session_state.conversations:
        if st.button("💬  " + conversation["title"][:25], key=f"open_{conversation['id']}", use_container_width=True):
            st.session_state.active_id = conversation["id"]
            st.rerun()
    st.markdown("---")
    st.caption("BUSINESS DATA")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"])
    use_demo = st.toggle("Use demo data", value=True if not uploaded else False)
    st.caption("Required columns: date, product, units, unit_price, unit_cost")
    with st.expander("AI settings"):
        api_key = st.text_input("Gemini API key (optional)", type="password")
        st.caption("Keep your API key private. Never add it to GitHub.")

try:
    if uploaded is not None:
        sales = prepare_data(pd.read_csv(uploaded))
        source_name = uploaded.name
    elif use_demo:
        sales = prepare_data(demo_data())
        source_name = "Demo data"
    else:
        sales = pd.DataFrame(columns=list(REQUIRED))
        source_name = "No data loaded"
except Exception as err:
    st.error(f"Could not read that CSV: {err}")
    st.stop()

data = summarize(sales)
active = next((c for c in st.session_state.conversations if c["id"] == st.session_state.active_id), st.session_state.conversations[0])

st.markdown('<div class="welcome"><h1>What’s happening in your business?</h1><p>Your friendly business sidekick for sales, profit, and your next move.</p></div>' if not active["messages"] else "", unsafe_allow_html=True)

if not active["messages"]:
    cols = st.columns(2)
    prompts = ["Give me a quick business check-up", "Which product makes the most profit?",
               "How can I improve my profit margin?", "Suggest 3 practical growth ideas"]
    for i, item in enumerate(prompts):
        with cols[i % 2]:
            if st.button(item, key=f"prompt_{i}", use_container_width=True):
                st.session_state.pending_prompt = item
                st.rerun()

for message in active["messages"]:
    with st.chat_message(message["role"], avatar="🙂" if message["role"]=="user" else "↗"):
        st.markdown(message["content"])

question = st.chat_input("Ask anything about your business...")
if "pending_prompt" in st.session_state:
    question = st.session_state.pop("pending_prompt")

if question:
    active["messages"].append({"role":"user","content":question})
    if active["title"] == "New chat":
        active["title"] = question[:25]
    if api_key.strip():
        answer = ai_answer(api_key.strip(), active["messages"], data)
    else:
        answer = basic_answer(question, data, sales)
    active["messages"].append({"role":"assistant","content":answer})
    st.rerun()

if not sales.empty:
    with st.expander("Quick numbers from your data"):
        x1,x2,x3 = st.columns(3)
        x1.metric("Revenue", f"{data['revenue']:,.2f}")
        x2.metric("Gross profit", f"{data['profit']:,.2f}")
        x3.metric("Gross margin", f"{data['margin']:.1f}%")
        st.caption(f"Data source: {source_name}")
        if not data["products"].empty:
            st.download_button("Download product report", data["products"].to_csv(index=False).encode("utf-8-sig"),
                               "profitpilot_report.csv", "text/csv")
