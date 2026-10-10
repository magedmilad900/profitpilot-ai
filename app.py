"""
ProfitPilot - an AI business advisor for small business owners.

Losing money?   It finds out why and gives a step-by-step fix.
Making money?   It finds the fastest ways to grow profit.

Run:  streamlit run app.py
"""
import json
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ───────────────────────── 1. Config ─────────────────────────
APP_NAME = "ProfitPilot"
STORE = Path("chats.json")
MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
FILE_TYPES = ["csv", "tsv", "xlsx", "txt", "md", "json", "pdf", "png", "jpg", "jpeg"]

SYSTEM_PROMPT = """You are ProfitPilot, a friendly business advisor for small business owners.
Talk in simple, warm English like a smart friend who knows business. Short sentences. No jargon
(or explain it in one line). If the user writes in another language, answer in that language.

Your job has two modes. Work out which one applies from the user's numbers:

1) LOSING MONEY or low profit -> be a business doctor:
   - Check revenue, cost of goods, gross margin, fixed costs, discounts, returns, and break-even.
   - Find the real cause (pricing too low, costs too high, weak products, slow sales, too many discounts...).
   - Give a ranked fix list: what to do first, how, and the rough money impact.

2) MAKING PROFIT -> be a growth coach:
   - Find the best products, customers and channels, and what is holding profit back.
   - Give practical levers: pricing, upsells and bundles, repeat customers, cutting weak items,
     better marketing spend, cost savings.

Rules:
- If you lack numbers, ask 2-4 simple questions first (revenue, costs, best sellers, goals).
- Use real figures from attached files. Show your math briefly. Never invent data.
- Use tables for comparisons. End with "Next steps" (max 3 clear actions).
- Use web search for market facts, competitor prices and trends, and name your sources.
- Be honest when unsure. You are an advisor, not a lawyer or an accountant."""

STARTERS = [
    ("I'm losing money", "My business is losing money. Ask me a few simple questions, then help me find out why and how to fix it."),
    ("I'm making a profit", "My business is making a profit. Help me find the fastest ways to grow it."),
    ("Analyze my sales file", "I'll attach my sales file. Tell me what is working, what is not, and what to do next."),
    ("Research my market", "Research my market and my competitors, and tell me where I can win."),
]

st.set_page_config(page_title=APP_NAME, page_icon=":material/trending_up:", layout="centered")

# ───────────────────────── 2. Styling ─────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none}
.stApp{background:#fff}
section[data-testid="stSidebar"]{background:#f7f7f8;border-right:1px solid #e5e5e8}
[data-testid="stChatMessageAvatarUser"],[data-testid="stChatMessageAvatarAssistant"]{display:none}
[data-testid="stChatMessage"]{background:none;padding:.4rem 0}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  flex-direction:row-reverse;background:#f1f1f3;border-radius:20px;padding:.5rem 1.1rem;width:fit-content;max-width:85%;margin-left:auto}
.stButton>button{border-radius:10px;border:1px solid #e5e5e8;background:#fff;color:#1a1a1c}
.stButton>button:hover{background:#ececee;border-color:#e5e5e8;color:#1a1a1c}
section[data-testid="stSidebar"] .stButton>button{border:0;background:transparent;text-align:left;justify-content:flex-start}
section[data-testid="stSidebar"] .stButton>button:hover{background:#ececee}
.hero{text-align:center;padding:12vh 0 1.5rem}
.hero h1{font-size:2rem;font-weight:600;letter-spacing:-.02em;margin-bottom:.2rem}
.hero p{color:#76767d}
.src a{font-size:.78rem;color:#76767d;border:1px solid #e5e5e8;border-radius:999px;padding:2px 10px;margin-right:6px;text-decoration:none}
</style>
""", unsafe_allow_html=True)

# ───────────────────────── 3. Storage ─────────────────────────
def load_chats() -> dict:
    try:
        return json.loads(STORE.read_text("utf-8"))
    except Exception:
        return {}


def save_chats() -> None:
    STORE.write_text(json.dumps(st.session_state.chats, ensure_ascii=False), "utf-8")


def init_state() -> None:
    st.session_state.setdefault("chats", load_chats())
    st.session_state.setdefault("cid", None)
    st.session_state.setdefault("blobs", {})  # PDFs / images stay in memory only


def current_chat() -> dict | None:
    return st.session_state.chats.get(st.session_state.cid)


# ───────────────────────── 4. File analysis ─────────────────────────
def to_number(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def snapshot(df: pd.DataFrame) -> str:
    """Quick, reliable numbers computed with pandas so the AI does not have to guess."""
    cols = {c.lower(): c for c in df.columns}
    find = lambda keys: next((cols[c] for c in cols if any(k in c for k in keys)), None)
    rev, cost, prof = find(["revenue", "sales", "amount", "total"]), find(["cogs", "cost", "expense"]), find(["profit"])
    item, date = find(["product", "item", "name", "category"]), find(["date", "month", "day"])

    out = [f"Rows: {len(df)} | Columns: {', '.join(map(str, df.columns))}",
           "(Columns below were auto-detected - double-check they are right.)"]
    d = df.copy()
    for c in (rev, cost, prof):
        if c:
            d[c] = to_number(d[c])
    profit = d[prof] if prof else (d[rev] - d[cost] if rev and cost else None)
    if rev:
        out.append(f"Total revenue ({rev}): {d[rev].sum():,.2f}")
    if cost:
        out.append(f"Total cost ({cost}): {d[cost].sum():,.2f}")
    if profit is not None:
        total, revenue = profit.sum(), d[rev].sum() if rev else 0
        out.append(f"Total profit: {total:,.2f}" + (f" | Margin: {total / revenue:.1%}" if revenue else ""))
        out.append(f"Loss-making rows: {(profit < 0).sum()} of {len(d)}")
        if item:
            by = profit.groupby(d[item]).sum().sort_values()
            out.append(f"Top 5 by profit ({item}):\n{by.tail(5)[::-1].round(2).to_string()}")
            out.append(f"Bottom 5 by profit ({item}):\n{by.head(5).round(2).to_string()}")
        if date:
            when = pd.to_datetime(d[date], errors="coerce")
            if when.notna().any():
                out.append(f"Profit by month:\n{profit.groupby(when.dt.to_period('M')).sum().round(2).to_string()}")
    return "\n".join(out)


def read_upload(f) -> dict:
    """Turn an uploaded file into {name, text} or {name, mime, id}."""
    name, ext = f.name, f.name.rsplit(".", 1)[-1].lower()
    if ext in ("csv", "tsv", "xlsx"):
        df = pd.read_excel(f) if ext == "xlsx" else pd.read_csv(f, sep=None, engine="python")
        return {"name": name, "text": snapshot(df) + "\n\nData (first rows):\n" + df.head(400).to_csv(index=False)[:100_000]}
    if ext in ("txt", "md", "json"):
        return {"name": name, "text": f.getvalue().decode("utf-8", "ignore")[:100_000]}
    fid = uuid.uuid4().hex
    st.session_state.blobs[fid] = f.getvalue()
    return {"name": name, "id": fid, "mime": "application/pdf" if ext == "pdf" else f"image/{'jpeg' if ext == 'jpg' else ext}"}


# ───────────────────────── 5. Gemini ─────────────────────────
def build_contents(messages: list[dict]) -> list[types.Content]:
    contents = []
    for m in messages:
        parts = []
        for a in m.get("files", []):
            if a.get("text"):
                parts.append(types.Part(text=f"[File: {a['name']}]\n{a['text']}"))
            elif a.get("id") in st.session_state.blobs:
                parts.append(types.Part.from_bytes(data=st.session_state.blobs[a["id"]], mime_type=a["mime"]))
            else:
                parts.append(types.Part(text=f"[File '{a['name']}' is no longer available. Ask the user to re-attach it if needed.]"))
        if m["content"]:
            parts.append(types.Part(text=m["content"]))
        if parts:
            contents.append(types.Content(role="user" if m["role"] == "user" else "model", parts=parts))
    return contents


def stream_answer(api_key: str, model: str, web: bool, messages: list[dict], box) -> tuple[str, list[dict]]:
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(google_search=types.GoogleSearch())] if web else None,
    )
    text, sources = "", {}
    for chunk in client.models.generate_content_stream(model=model, contents=build_contents(messages), config=config):
        text += chunk.text or ""
        for cand in chunk.candidates or []:
            meta = cand.grounding_metadata
            for g in (meta.grounding_chunks or []) if meta else []:
                if g.web:
                    sources[g.web.uri] = g.web.title or g.web.uri
        box.markdown(text + " ▌")
    box.markdown(text)
    return text, [{"uri": u, "title": t} for u, t in sources.items()]


def show_sources(sources: list[dict]) -> None:
    if sources:
        links = "".join(f'<a href="{s["uri"]}" target="_blank">{s["title"][:40]}</a>' for s in sources)
        st.markdown(f'<div class="src">{links}</div>', unsafe_allow_html=True)


# ───────────────────────── 6. Sidebar ─────────────────────────
def sidebar() -> tuple[str, str, bool]:
    chats = st.session_state.chats
    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        if st.button("New chat", icon=":material/add:", use_container_width=True):
            st.session_state.cid = None
            st.rerun()

        query = st.text_input("Search chats", placeholder="Search chats", label_visibility="collapsed").lower()
        shown = [(i, c) for i, c in chats.items() if query in c["title"].lower()]
        shown.sort(key=lambda x: (not x[1].get("pinned"), -x[1]["created"]))

        for i, c in shown:
            a, b, d = st.columns([6, 1.3, 1.3], gap="small")
            label = ("● " if i == st.session_state.cid else "") + c["title"]
            if a.button(label, key=f"o{i}", use_container_width=True):
                st.session_state.cid = i
                st.rerun()
            if b.button("", key=f"p{i}", icon=":material/push_pin:" if c.get("pinned") else ":material/keep:", help="Pin / unpin"):
                c["pinned"] = not c.get("pinned")
                save_chats()
                st.rerun()
            if d.button("", key=f"d{i}", icon=":material/delete:", help="Delete chat"):
                chats.pop(i)
                if st.session_state.cid == i:
                    st.session_state.cid = None
                save_chats()
                st.rerun()

        st.divider()
        with st.expander("Settings", icon=":material/settings:"):
            try:
                key = st.secrets.get("GEMINI_API_KEY", "")
            except Exception:  # no secrets file
                key = ""
            key = key or st.text_input("Gemini API key", type="password", help="Free at aistudio.google.com/apikey")
            model = st.selectbox("Model", MODELS)
            web = st.toggle("Search the web", value=True)
    return key, model, web


# ───────────────────────── 7. Main ─────────────────────────
def main() -> None:
    init_state()
    api_key, model, web = sidebar()
    chat = current_chat()

    # Past messages
    if chat:
        for m in chat["messages"]:
            with st.chat_message(m["role"]):
                for a in m.get("files", []):
                    st.caption(f":material/description: {a['name']}")
                st.markdown(m["content"])
                show_sources(m.get("sources", []))
    else:
        st.markdown('<div class="hero"><h1>How is your business doing?</h1>'
                    '<p>Tell me your numbers. I will find where money leaks, or where it can grow.</p></div>',
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for n, (title, prompt) in enumerate(STARTERS):
            if cols[n % 2].button(f"**{title}**\n\n{prompt}", key=f"s{n}", use_container_width=True):
                st.session_state.queued = prompt

    # New input
    entry = st.chat_input("Message ProfitPilot", accept_file="multiple", file_type=FILE_TYPES)
    text, uploads = (entry.text, entry.files) if entry else (st.session_state.pop("queued", ""), [])
    if not (text or uploads):
        return
    if not api_key:
        st.warning("Add your Gemini API key in the sidebar (Settings) to start.")
        return

    if chat is None:
        cid = uuid.uuid4().hex
        chat = st.session_state.chats[cid] = {"title": "New chat", "pinned": False, "created": pd.Timestamp.now().timestamp(), "messages": []}
        st.session_state.cid = cid
    files = [read_upload(f) for f in uploads]
    chat["messages"].append({"role": "user", "content": text, "files": files})
    if chat["title"] == "New chat":
        chat["title"] = (text or files[0]["name"])[:40]

    with st.chat_message("user"):
        for a in files:
            st.caption(f":material/description: {a['name']}")
        st.markdown(text)
    with st.chat_message("assistant"):
        box = st.empty()
        box.markdown("Thinking...")
        try:
            answer, sources = stream_answer(api_key, model, web, chat["messages"], box)
            show_sources(sources)
            chat["messages"].append({"role": "assistant", "content": answer, "sources": sources})
        except Exception as e:  # keep the chat usable if the API fails
            box.error(f"Something went wrong: {e}")
            chat["messages"].pop()
            return
    save_chats()
    st.rerun()


main()
