import json
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ProfitPilot", page_icon="📈", layout="wide")

# Clean, mostly-white interface inspired by modern chat apps
st.markdown("""
<style>
:root { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background: #ffffff !important;
}
[data-testid="stSidebar"] {
    background: #f7f7f8 !important;
    border-right: 1px solid #e8e8eb;
}
[data-testid="stSidebar"] > div { background: #f7f7f8 !important; }
.block-container { max-width: 980px; padding-top: 1.8rem; padding-bottom: 7rem; }
h1, h2, h3, p, label, span, div { color: #202123; }
.brand { font-size: 1.12rem; font-weight: 700; letter-spacing: -.3px; padding: .4rem 0 1rem; }
.brand-mark { display:inline-flex; width:30px; height:30px; align-items:center; justify-content:center;
    background:#202123; color:white; border-radius:9px; margin-right:8px; }
.welcome { text-align:center; padding: 3.0rem 1rem 1.2rem; }
.welcome h1 { font-size:2rem; font-weight:650; letter-spacing:-.8px; margin-bottom:.5rem; }
.welcome p { color:#6b7280; font-size:1rem; }
div[data-testid="stChatMessage"] { border: 0; padding: .9rem 0; }
div[data-testid="stChatMessageContent"] { line-height:1.7; }
div[data-testid="stChatInput"] {
    border-radius: 18px !important;
    border: 1px solid #dedee3 !important;
    box-shadow: 0 4px 18px rgba(0,0,0,.04);
}
div[data-testid="stChatInput"] textarea { background:#fff !important; }
.stButton > button {
    border-radius: 12px; border: 1px solid #e5e5e8; background: #fff;
    color:#242424; min-height: 2.5rem;
}
.stButton > button:hover { border-color:#b7b7bf; background:#f9f9fa; }
div[data-testid="stMetric"] { background:#fafafa; border:1px solid #ededf0; padding:1rem; border-radius:14px; }
hr { border-color:#eeeeef; }
.small-muted { color:#777; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

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
        units=("units","sum"), revenue=("revenue","sum"), cost=("cost","sum"), profit=("profit","sum")
    )
    product["margin_pct"] = (product["profit"] / product["revenue"].replace(0, pd.NA) * 100).fillna(0)
    daily = df.groupby("date", as_index=False).agg(revenue=("revenue","sum"), profit=("profit","sum"))
    total_rev, total_profit = float(df["revenue"].sum()), float(df["profit"].sum())
    margin = total_profit / total_rev * 100 if total_rev else 0
    return product.sort_values("profit", ascending=False), daily, total_rev, total_profit, margin

def rules_based_insights(df, products, revenue, profit, margin):
    insights = []
    if len(products):
        best = products.iloc[0]
        worst = products.sort_values("profit").iloc[0]
        insights.append(f"أعلى منتج في إجمالي الربح هو **{best['product']}**، وحقق {best['profit']:,.2f} ربحًا إجماليًا.")
        if worst["product"] != best["product"]:
            insights.append(f"راجع أداء **{worst['product']}**؛ فهو الأقل في إجمالي الربح ({worst['profit']:,.2f}). راجع الطلب والتسعير وتكلفة المورد قبل اتخاذ قرار.")
        low = products[products["margin_pct"] < 25]
        if len(low):
            names = "، ".join(low["product"].astype(str).head(3).tolist())
            insights.append(f"هامش الربح أقل من 25% في: {names}. جرّب تغييرًا بسيطًا في السعر أو التكلفة واختبر أثره.")
        popular = products.sort_values("units", ascending=False).iloc[0]
        insights.append(f"الأكثر مبيعًا بالوحدات هو **{popular['product']}** ({popular['units']:,.0f} وحدة). تأكد من توفر مخزون كافٍ.")
    if margin < 20:
        insights.append("هامش الربح الإجمالي أقل من 20%؛ راجع الخصومات وتكلفة الشراء ومزيج المنتجات.")
    elif margin >= 40:
        insights.append("هامش الربح الإجمالي جيد في البيانات الحالية، لكن تأكد أن حجم المبيعات يغطي المصاريف الثابتة.")
    return insights

def gemini_reply(api_key, history, summary_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    system = (
        "You are ProfitPilot, a warm, practical business analyst for small businesses. "
        "Speak naturally, clearly, and without exaggerated AI language. Use the provided sales summary as evidence. "
        "Do not invent facts. State uncertainty when needed. Give concise actionable advice. "
        "Reply in the same language as the latest user message. Data summary: " + summary_text
    )
    contents = [{"role":"user", "parts":[{"text":system}]}]
    for msg in history[-10:]:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role":role, "parts":[{"text":msg["content"]}]})
    try:
        r = requests.post(url, params={"key":api_key},
                          json={"contents":contents, "generationConfig":{"temperature":0.6}},
                          timeout=30)
        if r.ok:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return "مش قادر أوصل لخدمة Gemini دلوقتي. جرّب تاني بعد شوية، أو استخدم التحليل الأساسي من غير مفتاح API."
    except Exception:
        return "حصلت مشكلة في الاتصال بخدمة Gemini. اتأكد من الإنترنت ومفتاح API، وجرب تاني."

def local_reply(prompt, products, revenue, profit, margin, insights):
    q = prompt.lower()
    best = products.iloc[0] if len(products) else None
    worst = products.sort_values("profit").iloc[0] if len(products) else None
    if any(x in q for x in ["profit", "ربح", "مكسب", "أربح"]):
        return f"بص، إجمالي الإيرادات عندك **{revenue:,.2f}**، والربح الإجمالي **{profit:,.2f}** بهامش **{margin:.1f}%**. الربح هنا قبل المصاريف الثابتة والضرائب والشحن غير المسجل في تكلفة الوحدة."
    if any(x in q for x in ["best", "أحسن", "افضل", "أفضل", "منتج"]):
        return f"حسب البيانات، **{best['product']}** هو الأعلى في إجمالي الربح بقيمة **{best['profit']:,.2f}**، بينما **{worst['product']}** هو الأقل. ده مش معناه نوقف المنتج الأقل فورًا؛ راجع الطلب والمخزون وتكلفة المورد الأول."
    if any(x in q for x in ["marketing", "تسويق", "مبيعات", "sales", "grow", "نمو", "ازود", "أزود"]):
        return "أقترح تبدأ بتجربة صغيرة بدل ما تزود الميزانية مرة واحدة: اختار منتجًا بهامش ربح جيد، جرّب عليه حملة لمدة أسبوع، وقارن الربح الناتج بتكلفة الحملة. البيانات الحالية لا توضح تكلفة التسويق أو عدد العملاء، فدي معلومات هتساعدنا نحكم بدقة."
    return "أقدر أساعدك في فهم الأرقام واتخاذ خطوة عملية. من البيانات الحالية:\n\n" + "\n\n".join(f"- {x}" for x in insights[:4]) + "\n\nلو تحب، اسألني مثلًا: «أنهي منتج أكتر ربحًا؟» أو «إزاي أزود هامش الربح؟»"

# Session state: conversations remain during this browser session
if "chats" not in st.session_state:
    st.session_state.chats = [{"id": 1, "title": "تحليل المبيعات", "messages": []}]
    st.session_state.active_chat = 1
    st.session_state.next_chat_id = 2
if "page" not in st.session_state:
    st.session_state.page = "Chat"

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">↗</span>ProfitPilot</div>', unsafe_allow_html=True)
    if st.button("＋  محادثة جديدة", use_container_width=True):
        new_id = st.session_state.next_chat_id
        st.session_state.next_chat_id += 1
        st.session_state.chats.insert(0, {"id":new_id, "title":"محادثة جديدة", "messages":[]})
        st.session_state.active_chat = new_id
        st.session_state.page = "Chat"
        st.rerun()
    st.markdown("---")
    st.caption("WORKSPACE")
    if st.button("💬  المحادثة", use_container_width=True):
        st.session_state.page = "Chat"
    if st.button("📊  التحليلات", use_container_width=True):
        st.session_state.page = "Analytics"
    if st.button("📄  التقارير", use_container_width=True):
        st.session_state.page = "Reports"
    st.markdown("---")
    st.caption("محادثاتك الأخيرة")
    for chat in st.session_state.chats:
        label = chat["title"][:27] + ("…" if len(chat["title"]) > 27 else "")
        if st.button("◦  " + label, key=f"chat_{chat['id']}", use_container_width=True):
            st.session_state.active_chat = chat["id"]
            st.session_state.page = "Chat"
            st.rerun()
    st.markdown("---")
    uploaded = st.file_uploader("ارفع ملف مبيعات CSV", type=["csv"])
    use_demo = st.toggle("استخدم بيانات تجريبية", value=True if not uploaded else False)
    with st.expander("إعدادات الذكاء الاصطناعي"):
        api_key = st.text_input("Gemini API key (اختياري)", type="password",
                                help="لا ترفع المفتاح على GitHub.")
        st.caption("من غير المفتاح، تقدر تستخدم التحليل الأساسي.")

try:
    if uploaded is not None:
        df = normalize(pd.read_csv(uploaded))
        data_label = uploaded.name
    elif use_demo:
        df = normalize(demo_data())
        data_label = "بيانات تجريبية"
    else:
        df = pd.DataFrame()
        data_label = "لا توجد بيانات"
except Exception as exc:
    st.error(f"مش قادر أقرأ الملف: {exc}")
    st.info("الأعمدة المطلوبة: date, product, units, unit_price, unit_cost")
    st.stop()

if df.empty:
    products, daily, revenue, profit, margin = pd.DataFrame(), pd.DataFrame(), 0, 0, 0
    insights = ["ارفع ملف CSV أو فعّل البيانات التجريبية علشان نبدأ."]
else:
    products, daily, revenue, profit, margin = business_summary(df)
    insights = rules_based_insights(df, products, revenue, profit, margin)

active = next((c for c in st.session_state.chats if c["id"] == st.session_state.active_chat), st.session_state.chats[0])

if st.session_state.page == "Analytics":
    st.title("نظرة عامة على البزنس")
    st.caption(f"مصدر البيانات: {data_label} · {len(df):,} صف صالح")
    a,b,c,d = st.columns(4)
    a.metric("الإيرادات", f"{revenue:,.2f}")
    b.metric("الربح الإجمالي", f"{profit:,.2f}")
    c.metric("هامش الربح", f"{margin:.1f}%")
    d.metric("الوحدات المباعة", f"{df['units'].sum():,.0f}" if not df.empty else "0")
    if not df.empty:
        left,right = st.columns(2)
        with left:
            st.plotly_chart(px.line(daily, x="date", y=["revenue","profit"], markers=True,
                                    title="الإيرادات والربح بمرور الوقت"), use_container_width=True)
        with right:
            st.plotly_chart(px.bar(products.sort_values("profit"), x="profit", y="product", orientation="h",
                                   title="الربح الإجمالي حسب المنتج"), use_container_width=True)
        st.subheader("أداء المنتجات")
        st.dataframe(products, use_container_width=True, hide_index=True)
elif st.session_state.page == "Reports":
    st.title("التقارير")
    st.write("نزّل ملخص أداء المنتجات كملف CSV، وافتحه في Excel أو Google Sheets.")
    if not products.empty:
        st.download_button("تنزيل تقرير المنتجات CSV", products.to_csv(index=False).encode("utf-8-sig"),
                           "profitpilot_report.csv", "text/csv")
    st.subheader("ملاحظات التحليل")
    for item in insights:
        st.markdown("- " + item)
else:
    if not active["messages"]:
        st.markdown('<div class="welcome"><h1>أهلاً بيك، نقدر نطوّر البزنس إزاي؟</h1><p>اسأل عن المبيعات، الأرباح، المنتجات، أو الخطوة الجاية.</p></div>', unsafe_allow_html=True)
        cols = st.columns(2)
        suggestions = [
            "حلّل أداء المبيعات عندي",
            "أنهي منتج بيحقق أعلى ربح؟",
            "إزاي أزود هامش الربح؟",
            "اقترح عليّ 3 خطوات عملية للنمو",
        ]
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.pending_prompt = suggestion
                    st.rerun()
    for message in active["messages"]:
        with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "↗"):
            st.markdown(message["content"])

    prompt = st.chat_input("اكتب سؤالك عن البزنس...")
    if "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")
    if prompt:
        active["messages"].append({"role":"user", "content":prompt})
        if active["title"] == "محادثة جديدة":
            active["title"] = prompt[:28]
        summary = json.dumps({
            "revenue": round(revenue,2), "gross_profit": round(profit,2), "gross_margin_pct": round(margin,2),
            "products": products.round(2).to_dict(orient="records") if not products.empty else [],
            "recent_daily_totals": daily.tail(10).round(2).to_dict(orient="records") if not daily.empty else []
        }, ensure_ascii=False, default=str)
        if api_key.strip() and not df.empty:
            reply = gemini_reply(api_key.strip(), active["messages"], summary)
        else:
            reply = local_reply(prompt, products, revenue, profit, margin, insights)
        active["messages"].append({"role":"assistant", "content":reply})
        st.rerun()

st.markdown('<p class="small-muted">ProfitPilot يساعدك تفهم بياناتك؛ راجع الأرقام قبل اتخاذ قرارات مالية.</p>', unsafe_allow_html=True)
