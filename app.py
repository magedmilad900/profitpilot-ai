"""ProfitPilot AI — a focused business chat workspace.
Run with: streamlit run app.py --server.port 3000 --server.address 0.0.0.0
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="ProfitPilot AI", page_icon="PF", layout="wide", initial_sidebar_state="expanded")

SYSTEM_PROMPT = """You are ProfitPilot, a friendly business co-pilot. Reply in simple, natural English.
Be practical, honest, and concise. Use headings or bullets when useful. If business data is provided,
base your conclusions on it and state assumptions. If the user asks for current facts, use the research
context when available. Never claim to have browsed if no sources were provided."""

CSS = """
<style>
:root { --ink:#171717; --muted:#737373; --line:#e8e8e8; --soft:#f7f7f7; --accent:#5b6ee1; }
[data-testid="stAppViewContainer"] { background:#fff; }
[data-testid="stHeader"] { background:rgba(255,255,255,.9); }
.block-container { max-width:1280px; padding:0 2rem 2rem; }
[data-testid="stSidebar"] { background:#fafafa; border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding:1.1rem .8rem; }
.brand { display:flex; align-items:center; gap:.65rem; padding:.4rem .35rem 1.25rem; }
.brand-mark { width:30px; height:30px; border:1.5px solid #111; border-radius:9px; display:grid; place-items:center; font-size:11px; font-weight:700; letter-spacing:-.04em; }
.brand-name { font-weight:700; letter-spacing:-.03em; font-size:16px; }
.brand-sub { color:#999; font-size:11px; margin-top:1px; }
.section-label { color:#999; text-transform:uppercase; letter-spacing:.12em; font-size:10px; font-weight:700; padding:1rem .5rem .45rem; }
.chat-row { padding:.48rem .55rem; border-radius:9px; font-size:13px; margin:.12rem 0; color:#4a4a4a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chat-row.active { background:#ededed; color:#111; font-weight:600; }
.empty { text-align:center; padding:9rem 1rem 2rem; }
.empty-mark { width:46px; height:46px; border:1px solid #111; border-radius:14px; display:grid; place-items:center; margin:0 auto 1.35rem; font-weight:700; letter-spacing:-.08em; }
.empty h1 { font-size:2.15rem; letter-spacing:-.055em; margin:0; color:#111; }
.empty p { color:#777; font-size:14px; margin:.65rem 0 2rem; }
.prompt-card { border:1px solid var(--line); border-radius:13px; padding:.9rem 1rem; min-height:86px; background:#fff; }
.prompt-card b { font-size:13px; color:#222; } .prompt-card span { display:block; color:#888; font-size:12px; margin-top:.35rem; }
.message { display:flex; gap:1rem; max-width:820px; margin:1.3rem auto; }
.avatar { flex:0 0 28px; height:28px; border-radius:8px; display:grid; place-items:center; font-size:10px; font-weight:700; }
.avatar.user { background:#ededed; color:#333; } .avatar.ai { border:1px solid #111; color:#111; }
.message-body { font-size:15px; line-height:1.7; color:#222; min-width:0; }
.message-meta { font-size:11px; color:#999; margin-bottom:.2rem; }
.context { max-width:820px; margin:1rem auto; border:1px solid var(--line); border-radius:12px; padding:.7rem .9rem; background:#fbfbfb; color:#666; font-size:12px; }
[data-testid="stForm"] { border:1px solid #dcdcdc; border-radius:15px; padding:.25rem .45rem; box-shadow:0 4px 20px rgba(0,0,0,.04); }
button[kind="primary"] { background:#111 !important; border-color:#111 !important; }
button { border-radius:9px !important; }
.small-note { color:#999; font-size:11px; text-align:center; margin-top:.6rem; }
hr { border-color:var(--line); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def init_state() -> None:
    if "chats" not in st.session_state:
        st.session_state.chats = [{"id": "welcome", "title": "Getting started", "pinned": True, "messages": []}]
    if "active_id" not in st.session_state:
        st.session_state.active_id = "welcome"
    if "gemini_key" not in st.session_state:
        st.session_state.gemini_key = ""
    if "tavily_key" not in st.session_state:
        st.session_state.tavily_key = ""
    if "file_context" not in st.session_state:
        st.session_state.file_context = ""
    if "file_name" not in st.session_state:
        st.session_state.file_name = ""


def active_chat() -> dict[str, Any]:
    return next(c for c in st.session_state.chats if c["id"] == st.session_state.active_id)


def new_chat() -> None:
    cid = datetime.now().strftime("chat-%Y%m%d%H%M%S%f")
    st.session_state.chats.insert(0, {"id": cid, "title": "New conversation", "pinned": False, "messages": []})
    st.session_state.active_id = cid


def parse_upload(uploaded_file: Any) -> tuple[str, str]:
    name = uploaded_file.name
    raw = uploaded_file.getvalue()
    try:
        if name.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
            summary = f"File: {name}\nRows: {len(df):,}\nColumns: {', '.join(map(str, df.columns))}\n\nPreview:\n{df.head(12).to_csv(index=False)}"
            numeric = df.select_dtypes(include="number")
            if not numeric.empty:
                summary += f"\nNumeric totals:\n{numeric.sum(numeric_only=True).to_string()}"
            return name, summary[:18000]
        if name.lower().endswith(".txt") or name.lower().endswith(".md"):
            return name, raw.decode("utf-8", errors="ignore")[:18000]
        if name.lower().endswith(".pdf"):
            from pypdf import PdfReader
            text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(raw)).pages)
            return name, text[:18000]
        if name.lower().endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(raw))
            return name, "\n".join(p.text for p in doc.paragraphs)[:18000]
        return name, "This file type is not supported yet. Please upload CSV, PDF, DOCX, TXT, or MD."
    except Exception as exc:
        return name, f"Could not read this file: {exc}"


def research(query: str) -> tuple[str, list[dict[str, str]]]:
    key = st.session_state.tavily_key.strip()
    if not key:
        return "", []
    try:
        response = requests.post("https://api.tavily.com/search", json={"api_key": key, "query": query, "search_depth": "basic", "max_results": 5}, timeout=20)
        response.raise_for_status()
        results = response.json().get("results", [])
        context = "\n\n".join(f"Source: {r.get('title')}\nURL: {r.get('url')}\nContent: {r.get('content', '')}" for r in results)
        sources = [{"title": r.get("title", "Source"), "url": r.get("url", "")} for r in results]
        return context[:12000], sources
    except Exception as exc:
        return f"Research unavailable: {exc}", []


def ask_gemini(messages: list[dict[str, str]], research_context: str = "") -> str:
    key = st.session_state.gemini_key.strip()
    if not key:
        return local_reply(messages[-1]["content"], bool(st.session_state.file_context))
    contents = []
    for message in messages[-12:]:
        contents.append({"role": "user" if message["role"] == "user" else "model", "parts": [{"text": message["content"]}]})
    prompt = SYSTEM_PROMPT
    if st.session_state.file_context:
        prompt += "\n\nBusiness file context:\n" + st.session_state.file_context
    if research_context:
        prompt += "\n\nResearch context:\n" + research_context
    body = {"system_instruction": {"parts": [{"text": prompt}]}, "contents": contents, "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200}}
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        result = requests.post(url, params={"key": key}, json=body, timeout=45)
        result.raise_for_status()
        return result.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        return f"I couldn’t reach Gemini right now. Check your API key and connection.\n\nTechnical note: {exc}"


def local_reply(question: str, has_file: bool) -> str:
    q = question.lower()
    if has_file and any(word in q for word in ["sales", "revenue", "profit", "margin", "data", "file"]):
        return "I can see your business file, but I need a Gemini API key to give you a full natural-language analysis. Add it from Settings, then ask me about revenue, profit, best products, or growth opportunities."
    if any(word in q for word in ["hello", "hi", "hey"]):
        return "Hey — I’m ProfitPilot. Ask me about your business, research, writing, or your next best move."
    return "I’m ready to help. Add a Gemini API key in Settings for full AI answers, file analysis, and research. Without a key, I can still guide you through the setup."


def render_message(message: dict[str, Any]) -> None:
    role = message["role"]
    initials = "PF" if role == "assistant" else "You"
    st.markdown(f"<div class='message'><div class='avatar {'ai' if role == 'assistant' else 'user'}'>{initials}</div><div class='message-body'><div class='message-meta'>{'ProfitPilot' if role == 'assistant' else 'You'}</div>{message['content']}</div></div>", unsafe_allow_html=True)
    if message.get("sources"):
        links = " · ".join(f"[{s['title']}]({s['url']})" for s in message["sources"] if s.get("url"))
        st.markdown(f"<div class='context'><b>Sources</b><br>{links}</div>", unsafe_allow_html=True)


init_state()

with st.sidebar:
    st.markdown("<div class='brand'><div class='brand-mark'>PF</div><div><div class='brand-name'>ProfitPilot</div><div class='brand-sub'>AI business workspace</div></div></div>", unsafe_allow_html=True)
    if st.button("＋  New chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
    st.markdown("<div class='section-label'>Pinned</div>", unsafe_allow_html=True)
    pinned = [c for c in st.session_state.chats if c["pinned"]]
    for chat in pinned:
        if st.button("⌖  " + chat["title"], key="pin-" + chat["id"], use_container_width=True):
            st.session_state.active_id = chat["id"]; st.rerun()
    st.markdown("<div class='section-label'>Your chats</div>", unsafe_allow_html=True)
    for chat in [c for c in st.session_state.chats if not c["pinned"]]:
        col1, col2 = st.columns([5, 1], gap="small")
        with col1:
            if st.button(chat["title"], key="chat-" + chat["id"], use_container_width=True):
                st.session_state.active_id = chat["id"]; st.rerun()
        with col2:
            if st.button("×", key="del-" + chat["id"], help="Delete chat"):
                st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]
                if not st.session_state.chats: new_chat()
                else: st.session_state.active_id = st.session_state.chats[0]["id"]
                st.rerun()
    st.divider()
    with st.expander("Settings", expanded=False):
        st.caption("Keys stay in this session and are never shown in the chat.")
        st.session_state.gemini_key = st.text_input("Gemini API key", type="password", value=st.session_state.gemini_key)
        st.session_state.tavily_key = st.text_input("Tavily search key (optional)", type="password", value=st.session_state.tavily_key)
        if st.session_state.gemini_key:
            st.success("Gemini connected", icon="✓")
        else:
            st.info("Add Gemini to unlock full AI chat.")

chat = active_chat()
st.markdown("<div style='height:1.3rem'></div>", unsafe_allow_html=True)

if not chat["messages"]:
    st.markdown("<div class='empty'><div class='empty-mark'>PF</div><h1>What can I help you with?</h1><p>Your business, research, ideas, and everyday questions.</p></div>", unsafe_allow_html=True)
    cards = [("Analyze my business", "Understand sales, costs, and profit."), ("Research a topic", "Find information and useful sources."), ("Write something", "Plans, emails, reports, and ideas."), ("Solve a problem", "Think through the next best step.")]
    cols = st.columns(4, gap="small")
    for col, (title, desc) in zip(cols, cards):
        with col:
            st.markdown(f"<div class='prompt-card'><b>{title}</b><span>{desc}</span></div>", unsafe_allow_html=True)
else:
    for message in chat["messages"]:
        render_message(message)

uploaded = st.file_uploader("Attach a file", type=["csv", "pdf", "docx", "txt", "md"], label_visibility="collapsed")
if uploaded:
    name, context = parse_upload(uploaded)
    st.session_state.file_name, st.session_state.file_context = name, context
    st.caption(f"Attached: {name} · ready for analysis")

with st.form("chat_form", clear_on_submit=True):
    prompt = st.text_area("Message ProfitPilot…", height=72, label_visibility="collapsed", placeholder="Message ProfitPilot…")
    send_col, action_col = st.columns([6, 1])
    with send_col:
        submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
    with action_col:
        research_mode = st.form_submit_button("Research", use_container_width=True)

if submitted or research_mode:
    prompt = (prompt or "").strip()
    if prompt:
        if chat["title"] == "New conversation":
            chat["title"] = re.sub(r"\s+", " ", prompt)[:34] + ("…" if len(prompt) > 34 else "")
        chat["messages"].append({"role": "user", "content": prompt})
        with st.spinner("Thinking…"):
            research_context, sources = research(prompt) if research_mode else ("", [])
            answer = ask_gemini(chat["messages"], research_context)
        chat["messages"].append({"role": "assistant", "content": answer, "sources": sources})
        st.rerun()

st.markdown("<div class='small-note'>ProfitPilot can make mistakes. Check important business decisions with your own data.</div>", unsafe_allow_html=True)
