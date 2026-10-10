from __future__ import annotations

import html
import io
import re
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="ProfitPilot — AI + Business", page_icon="PF", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Fredoka:wght@400;500;600;700&family=Patrick+Hand&display=swap');
html, body, [data-testid="stAppViewContainer"], button, input, textarea, label, [data-testid="stDataFrame"] * { font-family:'Fredoka','Comic Sans MS',cursive !important; }
[data-testid="stSidebar"], .brand-name, .brand-sub, .side-link, .topline, [data-testid="stSidebar"] button, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { font-family:'Fredoka','Comic Sans MS',cursive !important; }
h1, h2, h3, h4, [data-testid="stMetricValue"], .stage-copy h2 { font-family:'Bangers','Fredoka','Comic Sans MS',cursive !important; font-weight:400 !important; letter-spacing:.02em; }
.stage-copy p, .story, .advice-card, [data-testid="stChatMessage"] { font-family:'Patrick Hand','Fredoka','Comic Sans MS',cursive !important; font-size:1.12rem; }
.insight, .insight *, [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p, [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li { font-family:'Patrick Hand','Fredoka','Comic Sans MS',cursive !important; font-size:1.12rem; line-height:1.45; }
.block-container { padding: 2.5rem 2rem 4rem; max-width: 980px; }
[data-testid="stSidebar"] { background:#f7f7f7; border-right:1px solid #e5e5e5; }
[data-testid="stSidebar"] .block-container { padding:1.3rem 1rem; }
.brand-row { display:flex; align-items:center; gap:.8rem; margin-bottom:2rem; }
.arrow-logo { width:38px; height:38px; border:1px solid #111; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:25px; font-weight:700; background:#111; color:#fff; }
.brand-name { font-weight:700; font-size:1.05rem; letter-spacing:-.02em; }
.brand-sub { color:#777; font-size:.76rem; margin-top:.1rem; }
.side-link { padding:.62rem .7rem; border-radius:9px; color:#333; font-size:.92rem; margin:.16rem 0; }
.side-link.active { background:#e9e9e9; color:#111; font-weight:600; }
.topline { display:flex; justify-content:space-between; align-items:center; color:#777; font-size:.78rem; margin-bottom:4rem; }
.center-brand { text-align:center; }
.center-arrow { width:58px; height:58px; border-radius:17px; background:#111; color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:37px; font-weight:700; }
.center-brand h1 { margin:.75rem 0 .15rem; font-size:2.2rem; letter-spacing:-.06em; color:#111; }
.center-brand p { margin:0; color:#777; font-size:.9rem; }
.story { max-width:620px; margin:1.5rem auto 2.2rem; text-align:center; color:#555; line-height:1.7; font-size:1rem; }
.chat-heading { text-align:center; font-size:.9rem; color:#777; margin-bottom:.7rem; }
[data-testid="stChatMessage"] { border:1px solid #e3e3e3; border-radius:15px; padding:.75rem 1rem; background:#fafafa; }
[data-testid="stChatMessageAvatarAssistant"] { background:#111 !important; color:#fff !important; }
[data-testid="stChatMessageAvatarUser"] { background:#777 !important; color:#fff !important; }
.insight { border-left:4px solid #111; background:#f5f5f5; padding:.75rem 1rem; border-radius:8px; margin:.45rem 0; }
.risk, .loss { border-left-color:#555; background:#eeeeee; }
.source { font-size:.78rem; color:#475569; }
.stApp, [data-testid="stAppViewContainer"] { background:#fff8e8; color:#191919; }
[data-testid="stAppViewContainer"]:before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.25; background-image:radial-gradient(#f28c8c 1.5px, transparent 1.5px), radial-gradient(#8fd3ff 1.5px, transparent 1.5px); background-size:46px 46px, 73px 73px; background-position:0 0, 22px 18px; animation:paperdrift 18s linear infinite; }
[data-testid="stSidebar"] { background:#ffe9c7; border-right:2px solid #191919; box-shadow:5px 0 0 #191919; }
[data-testid="stSidebar"] .block-container { background:transparent; }
[data-testid="stSidebar"] .side-link { border:2px solid transparent; transition:transform .2s ease, background .2s ease; }
[data-testid="stSidebar"] .side-link:hover { background:#ffcf56; border-color:#191919; transform:rotate(-1deg) translateX(3px); }
[data-testid="stSidebar"] [data-testid="stFileUploader"] { border:2px dashed #191919; border-radius:16px; background:#fff; padding:.35rem; }
[data-testid="stSidebar"] .stButton > button { font-size:.72rem !important; padding:.35rem .2rem !important; }
.stButton > button { border:2px solid #191919; border-radius:14px; background:#8fd3ff; color:#191919; font-weight:700; box-shadow:4px 5px 0 #191919; transition:transform .16s ease, box-shadow .16s ease; }
.stButton > button:hover { background:#ffcf56; color:#191919; transform:translate(-2px,-2px) rotate(-1deg); box-shadow:6px 7px 0 #191919; }
.stButton > button:active { transform:translate(2px,2px); box-shadow:2px 2px 0 #191919; }
[data-testid="stExpander"] { border:2px solid #191919; border-radius:16px; background:#fff; box-shadow:4px 5px 0 #191919; overflow:hidden; }
[data-testid="stExpander"] summary { background:#ffefcf; font-weight:700; }
[data-testid="stMetric"] { border:2px solid #191919; border-radius:16px; background:#fff; padding:.8rem; box-shadow:3px 4px 0 #191919; }
[data-testid="stDataFrame"] { border:2px solid #191919; border-radius:16px; overflow:hidden; box-shadow:4px 5px 0 #191919; background:#fff; }
[data-testid="stChatMessage"] { border:2px solid #191919; background:#fffef8; box-shadow:3px 4px 0 #191919; }
.stDownloadButton > button { border:2px solid #191919; border-radius:14px; background:#f28c8c; color:#191919; font-weight:700; box-shadow:4px 5px 0 #191919; }
.stDownloadButton > button:hover { background:#ffcf56; color:#191919; }
@keyframes paperdrift { 0% { transform:translate(0,0); } 50% { transform:translate(18px,10px); } 100% { transform:translate(0,0); } }
.advice-stage { position:relative; overflow:hidden; min-height:360px; border:2px solid #191919; border-radius:28px; background:#fff8e8; padding:2.2rem 2.4rem; box-shadow:7px 8px 0 #191919; }
.advice-stage:before, .advice-stage:after { content:""; position:absolute; border-radius:50%; opacity:.75; animation:drift 8s ease-in-out infinite; }
.advice-stage:before { width:120px; height:120px; background:#ffcf56; right:7%; top:12%; }
.advice-stage:after { width:76px; height:76px; background:#8fd3ff; left:7%; bottom:10%; animation-delay:-3s; }
.stage-copy { position:relative; z-index:2; max-width:480px; }
.stage-kicker { font-size:.78rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:#555; }
.stage-copy h2 { font-size:2.5rem; line-height:1.02; letter-spacing:-.06em; margin:.5rem 0 .8rem; color:#151515; }
.stage-copy p { color:#555; max-width:390px; line-height:1.6; }
.cartoon { position:absolute; z-index:2; right:9%; bottom:4%; width:290px; animation:bob 4.5s ease-in-out infinite; }
.cartoon .hose { fill:none; stroke:#191919; stroke-width:7; stroke-linecap:round; stroke-linejoin:round; }
.cartoon .blink { animation:blink 4s infinite; transform-origin:center; }
.floating-star { position:absolute; z-index:3; font-size:2rem; animation:spinfloat 5s ease-in-out infinite; }
.star-one { right:35%; top:13%; color:#191919; } .star-two { right:4%; bottom:17%; color:#f28c8c; animation-delay:-2s; }
@keyframes bob { 0%,100% { transform:translateY(0) rotate(-1deg); } 50% { transform:translateY(-13px) rotate(2deg); } }
@keyframes drift { 0%,100% { transform:translate(0,0) rotate(0deg); } 50% { transform:translate(18px,-12px) rotate(18deg); } }
@keyframes spinfloat { 0%,100% { transform:translateY(0) rotate(0deg); } 50% { transform:translateY(-10px) rotate(20deg); } }
@keyframes blink { 0%,44%,48%,100% { transform:scaleY(1); } 46% { transform:scaleY(.1); } }
.advice-card { border:1px solid #191919; border-radius:16px; padding:1rem 1.1rem; background:#fff; min-height:118px; box-shadow:3px 4px 0 #191919; }
.advice-card b { display:block; margin-bottom:.4rem; }
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


# ---------- Conversation state ----------
def chat_id() -> str:
    return datetime.now().strftime("chat-%Y%m%d%H%M%S%f")


def new_chat_record(title: str = "New chat") -> dict:
    return {"id": chat_id(), "title": title, "pinned": False, "created": datetime.now().isoformat(), "messages": []}


if "chats" not in st.session_state:
    first_chat = new_chat_record("Business analysis")
    st.session_state.chats = {first_chat["id"]: first_chat}
    st.session_state.active_chat_id = first_chat["id"]


def active_chat() -> dict:
    return st.session_state.chats[st.session_state.active_chat_id]


# ---------- Conversation sidebar ----------
with st.sidebar:
    st.markdown('<div class="brand-row"><div class="arrow-logo">↗</div><div><div class="brand-name">ProfitPilot</div><div class="brand-sub">AI + Business</div></div></div>', unsafe_allow_html=True)
    if st.button("＋  New chat", width="stretch"):
        record = new_chat_record()
        st.session_state.chats[record["id"]] = record
        st.session_state.active_chat_id = record["id"]
        st.rerun()
    st.markdown('<div class="side-link active">⌂  Chat</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("CHATS")
    ordered_chats = sorted(st.session_state.chats.values(), key=lambda item: (not item["pinned"], item["created"]), reverse=False)
    for record in ordered_chats:
        row = st.columns([4.6, 1.6], gap="small")
        label = ("Pinned · " if record["pinned"] else "") + ("• " if record["id"] == st.session_state.active_chat_id else "") + record["title"]
        if row[0].button(label, key=f"open-{record['id']}", width="stretch"):
            st.session_state.active_chat_id = record["id"]
            st.rerun()
        with row[1].popover("...", use_container_width=True):
            if st.button("Unpin" if record["pinned"] else "Pin", key=f"pin-{record['id']}", width="stretch"):
                record["pinned"] = not record["pinned"]
                st.rerun()
            rename_value = st.text_input("Chat name", value=record["title"], key=f"rename-input-{record['id']}")
            if st.button("Save name", key=f"save-name-{record['id']}", width="stretch"):
                cleaned = rename_value.strip()[:48]
                if cleaned:
                    record["title"] = cleaned
                st.rerun()
            if st.button("Delete", key=f"delete-{record['id']}", width="stretch"):
                if len(st.session_state.chats) == 1:
                    record["messages"] = []
                    record["title"] = "New chat"
                    record["pinned"] = False
                else:
                    del st.session_state.chats[record["id"]]
                    if st.session_state.active_chat_id == record["id"]:
                        st.session_state.active_chat_id = next(iter(st.session_state.chats))
                st.rerun()
    st.divider()
    st.caption("PROJECT DEMO")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"], label_visibility="visible")
    st.caption("No API no setup")

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

# ---------- Interactive cartoon advice experience ----------
st.markdown('<div class="topline"><span>ProfitPilot</span><span>DEMO MODE · AI + Business</span></div>', unsafe_allow_html=True)
components.html('''
<style>
  * { box-sizing:border-box; }
  @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Fredoka:wght@400;500;600;700&family=Patrick+Hand&display=swap');
  body { margin:0; background:transparent; font-family:'Fredoka','Comic Sans MS',cursive; }
  #scene { position:relative; overflow:hidden; height:360px; border:2px solid #191919; border-radius:28px; background:#fff8e8; box-shadow:7px 8px 0 #191919; cursor:crosshair; }
  #scene:before,#scene:after { content:""; position:absolute; border-radius:50%; opacity:.75; animation:drift 8s ease-in-out infinite; }
  #scene:before { width:120px; height:120px; background:#ffcf56; right:7%; top:12%; }
  #scene:after { width:76px; height:76px; background:#8fd3ff; left:7%; bottom:10%; animation-delay:-3s; }
  .copy { position:absolute; z-index:2; left:34px; top:34px; max-width:500px; }
  .copy-card { padding:22px 25px 20px; border:2px solid #191919; border-radius:22px; background:rgba(255,255,255,.78); box-shadow:5px 6px 0 #191919; }
  .kicker { font-size:12px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#555; }
  h2 { font-family:'Bangers','Fredoka','Comic Sans MS',cursive; font-size:47px; line-height:1.02; letter-spacing:1px; margin:10px 0 12px; color:#151515; }
  p { color:#555; max-width:390px; line-height:1.5; font-size:18px; font-family:'Patrick Hand','Comic Sans MS',cursive; }
  #bot { position:absolute; z-index:3; right:8%; bottom:8px; width:290px; transform-origin:50% 100%; transition:transform .18s cubic-bezier(.2,.8,.2,1); animation:bob 4.5s ease-in-out infinite; }
  #arrow-mascot { position:absolute; z-index:3; right:15%; bottom:66px; width:128px; height:128px; display:flex; align-items:center; justify-content:center; border:8px solid #191919; border-radius:38px; background:#8fd3ff; color:#191919; box-shadow:8px 9px 0 #191919; font:700 76px 'Fredoka','Comic Sans MS',cursive; transform-origin:50% 100%; transition:transform .18s cubic-bezier(.2,.8,.2,1); animation:bob 4.5s ease-in-out infinite; }
  .hose { fill:none; stroke:#191919; stroke-width:7; stroke-linecap:round; stroke-linejoin:round; }
  .eye-white { fill:#fff; stroke:#191919; stroke-width:5; }
  .pupil { fill:#191919; transition:transform .12s ease-out; }
  .brow { fill:none; stroke:#191919; stroke-width:6; stroke-linecap:round; }
  .cheek { fill:#f28c8c; opacity:.72; }
  .blink { animation:blink 4s infinite; transform-origin:center; }
  .spark { position:absolute; z-index:4; width:20px; height:20px; animation:spinfloat 5s ease-in-out infinite; }
  .spark:before,.spark:after { content:""; position:absolute; background:#191919; border-radius:5px; }
  .spark:before { width:4px; height:20px; left:8px; top:0; } .spark:after { width:20px; height:4px; left:0; top:8px; }
  .spark-one { right:35%; top:13%; } .spark-two { right:4%; bottom:17%; animation-delay:-2s; }
  @keyframes bob { 0%,100% { transform:translateX(0) translateY(0) rotate(-1deg); } 50% { transform:translateX(0) translateY(-13px) rotate(2deg); } }
  @keyframes drift { 0%,100% { transform:translate(0,0) rotate(0deg); } 50% { transform:translate(18px,-12px) rotate(18deg); } }
  @keyframes spinfloat { 0%,100% { transform:translateY(0) rotate(0deg); } 50% { transform:translateY(-10px) rotate(20deg); } }
  @keyframes blink { 0%,44%,48%,100% { transform:scaleY(1); } 46% { transform:scaleY(.1); } }
</style>
<div id="scene">
  <div class="copy"><div class="copy-card"><div class="kicker">A tiny business analyst</div><h2>Find the leak<br>fix the business</h2><p>ProfitPilot looks at your numbers and turns them into one clear next move</p></div></div>
  <div class="spark spark-one"></div><div class="spark spark-two"></div>
  <div id="arrow-mascot" aria-label="ProfitPilot arrow mascot">↗</div>
</div>
<script>
  const scene=document.getElementById('scene'); const bot=document.getElementById('arrow-mascot');
  scene.addEventListener('pointermove',(event)=>{
    const box=scene.getBoundingClientRect(); const x=(event.clientX-box.left)/box.width*2-1; const y=(event.clientY-box.top)/box.height*2-1;
    bot.style.transform=`translate(${x*18}px,${y*4}px) rotate(${x*2}deg)`;
  });
  scene.addEventListener('pointerleave',()=>{ bot.style.transform='translate(0,0) rotate(-1deg)'; });
</script>
''', height=380, scrolling=False)

st.markdown('<div class="story">A small business can have sales and still lose money ProfitPilot reads the numbers finds the leak and suggests the next move</div>', unsafe_allow_html=True)
st.markdown('<div class="chat-heading">Choose a move and get advice from your numbers</div>', unsafe_allow_html=True)

if "advice_text" not in st.session_state:
    st.session_state.advice_text = f"Start with {products.sort_values('net_profit').iloc[0]['product']} It is the first product I would review before spending more on growth"

b1, b2, b3 = st.columns(3)
with b1:
    if st.button("Find the leak", width="stretch"):
        weak = products.sort_values("net_profit").iloc[0]
        st.session_state.advice_text = f"Look at {weak['product']} first It has the weakest net profit at ${weak['net_profit']:,.2f} Check price cost and promotion spend"
with b2:
    if st.button("Boost profit", width="stretch"):
        best = products.sort_values("net_profit", ascending=False).iloc[0]
        st.session_state.advice_text = f"Protect {best['product']} It is your strongest profit driver with ${best['net_profit']:,.2f} Try a bundle with the weaker product"
with b3:
    if st.button("Next move", width="stretch"):
        st.session_state.advice_text = build_action_plan(products, net_profit, insights)[0].replace("1. ", "")

st.markdown(f'<div class="advice-card"><b>ProfitPilot says</b>{html.escape(st.session_state.advice_text)}</div>', unsafe_allow_html=True)

current_chat = active_chat()
st.markdown(f'<div class="chat-heading">{html.escape(current_chat["title"])} · Ask the business analyst</div>', unsafe_allow_html=True)
if not current_chat["messages"]:
    st.markdown('<div class="advice-card"><b>ProfitPilot is ready</b>Ask why a product is weak what is driving profit or what to do next</div>', unsafe_allow_html=True)
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for source in message.get("sources", []):
            st.markdown(f"<div class='source'>↗ <a href='{html.escape(source['url'], quote=True)}' target='_blank'>{html.escape(source['title'])}</a></div>", unsafe_allow_html=True)
question = st.chat_input("Ask about profit products or your next move")
if question:
    if current_chat["title"] in {"New chat", "Business analysis"}:
        compact_title = " ".join(question.strip().split())[:36]
        current_chat["title"] = compact_title or "New chat"
    current_chat["messages"].append({"role": "user", "content": question, "sources": []})
    answer, sources = assistant_reply(question, df, products, daily, revenue, gross_profit, expenses, net_profit, margin, insights)
    current_chat["messages"].append({"role": "assistant", "content": answer, "sources": sources})
    st.rerun()
