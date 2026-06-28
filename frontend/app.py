import io
import os
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = "http://api:8000"

st.set_page_config(
    page_title="SubMan Pro", 
    layout="wide", 
    page_icon="💳",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
#  TOKENS
# ─────────────────────────────────────────────
BG        = "#111827"   # page background
SB_BG     = "#1f2937"   # sidebar
CARD      = "#1f2937"   # card surface
CARD2     = "#374151"   # table header
BORDER    = "#374151"
ACCENT    = "#60a5fa"   # bright blue
SUCCESS   = "#34d399"   # bright green
WARNING   = "#fbbf24"   # bright amber
DANGER    = "#f87171"   # bright red
T1        = "#f9fafb"   # primary text
T2        = "#d1d5db"   # secondary text
T3        = "#9ca3af"   # muted text

CAT_COLORS = {
    "entertainment": "#a78bfa",
    "health":        "#34d399",
    "software":      "#60a5fa",
    "sport":         "#fbbf24",
    "other":         "#9ca3af",
}

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* Page */
html, body {{ background-color: {BG} !important; }}
[data-testid="stAppViewContainer"] {{ background-color: {BG} !important; }}
[data-testid="stMain"] {{ background-color: {BG} !important; }}
.main .block-container {{
    background-color: #111827 !important;
    padding: 1.5rem 2rem 2rem !important; /* ריווח עדין ומאוזן */
    max-width: 100% !important;           /* פריסה מלאה על כל רוחב המסך */
    font-family: 'Inter', sans-serif;
}}

/* Header & Collapse Buttons (Fixing the invisible icons) */
header[data-testid="stHeader"] {{
    background: transparent !important;
}}
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] span,
[data-testid="collapsedControl"] svg {{
    color: {T1} !important;
    fill: {T1} !important;
}}

/* Sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {{
    background-color: {SB_BG} !important;
    border-right: 1px solid {BORDER} !important;
}}

[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stDateInput label {{
    color: {T2} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    font-family: 'Inter', sans-serif !important;
}}

[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input[type="number"],
[data-testid="stSidebar"] input[type="date"] {{
    background-color: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {T1} !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
}}

[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background-color: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] span {{
    color: {T1} !important;
    font-size: 13px !important;
}}

[data-testid="stSidebar"] [data-testid="stForm"] {{
    background-color: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    padding: 14px !important;
}}

[data-testid="stSidebar"] .stFormSubmitButton button {{
    background: linear-gradient(135deg, {ACCENT}, #2563eb) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    width: 100% !important;
    padding: 10px !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton button:hover {{
    opacity: 0.85 !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {BORDER} !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {T3} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    font-family: 'Inter', sans-serif !important;
}}
.stTabs [aria-selected="true"] {{
    color: {T1} !important;
    border-bottom: 2px solid {ACCENT} !important;
}}

/* Buttons & Selectbox */
.stDownloadButton button, .stButton button {{
    background-color: {CARD} !important;
    border: 1px solid {BORDER} !important;
    color: {T1} !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}}
.stDownloadButton button:hover, .stButton button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}
[data-testid="stMain"] [data-baseweb="select"] > div {{
    background-color: {CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
[data-testid="stMain"] [data-baseweb="select"] span {{
    color: {T1} !important;
}}

#MainMenu, footer {{ visibility: hidden !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def get_data(endpoint):
    try:
        r = requests.get(f"{API_URL}/{endpoint}", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def delete_sub(name):
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = requests.delete(f"{API_URL}/subscriptions/{name}", headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def cat_pill(cat: str) -> str:
    c = CAT_COLORS.get(cat.lower(), CAT_COLORS["other"])
    return (f'<span style="background:{c}22;color:{c};border:1px solid {c}66;'
            f'border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">'
            f'{cat.capitalize()}</span>')

def section_label(text: str) -> str:
    return (f'<p style="font-size:11px;font-weight:700;color:{T3};'
            f'text-transform:uppercase;letter-spacing:.7px;margin:0 0 6px;'
            f'font-family:Inter,sans-serif;">{text}</p>')

def divider() -> str:
    return f'<div style="height:1px;background:{BORDER};margin:16px 0;"></div>'

# ─────────────────────────────────────────────
#  SUCCESS MODAL
# ─────────────────────────────────────────────
@st.dialog("Done")
def show_success_modal(message):
    st.markdown(
        f'<div style="text-align:center;padding:16px 0;">'
        f'<div style="font-size:44px;margin-bottom:10px;">✅</div>'
        f'<p style="color:{T2};font-size:15px;font-family:Inter,sans-serif;">{message}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.balloons()
    if st.button("Continue", use_container_width=True):
        del st.session_state["success_msg"]
        st.rerun()

if "success_msg" in st.session_state:
    show_success_modal(st.session_state["success_msg"])

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="padding:4px 6px 20px;font-family:Inter,sans-serif;">'
        f'<div style="font-size:22px;font-weight:800;color:{T1};letter-spacing:-0.5px;">'
        f'💳 SubMan Pro</div>'
        f'<div style="font-size:11px;color:{T3};margin-top:3px;">Subscription Intelligence</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(divider(), unsafe_allow_html=True)

    st.markdown(section_label("Budget Target"), unsafe_allow_html=True)
    budget_target = st.number_input(
        "Monthly Limit (₪)", min_value=100, value=1000,
        step=50, label_visibility="collapsed",
    )

    st.markdown(divider(), unsafe_allow_html=True)

    st.markdown(
        f'<p style="font-size:14px;font-weight:700;color:{T1};'
        f'font-family:Inter,sans-serif;margin-bottom:12px;">＋ New Subscription</p>',
        unsafe_allow_html=True,
    )

    st.markdown(divider(), unsafe_allow_html=True)
    st.markdown(section_label("Security Control"), unsafe_allow_html=True)

    if "token" not in st.session_state:
        st.session_state["token"] = None

    if not st.session_state["token"]:
        user_input = st.text_input("Username", key="auth_user")
        pass_input = st.text_input("Password", type="password", key="auth_pass")
        if st.button("🔐 Login", use_container_width=True):
            res = requests.post(
                f"{API_URL}/auth/token",
                data={"username": user_input, "password": pass_input},
            )
            if res.status_code == 200:
                st.session_state["token"] = res.json()["access_token"]
                st.success("Authenticated!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        st.markdown(
            f'<p style="color:{SUCCESS};font-size:12px;font-weight:600;">'
            f'✔️ Authenticated as Admin</p>',
            unsafe_allow_html=True,
        )
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["token"] = None
            st.rerun()

    with st.form("sub_form", clear_on_submit=True):
        name          = st.text_input("Name", placeholder="e.g. Netflix")
        price         = st.number_input("Price", min_value=0.0, step=1.0)
        currency      = st.selectbox("Currency", ["ILS", "USD", "EUR"])
        category      = st.selectbox("Category", ["Entertainment", "Software", "Health", "Sport", "Other"])
        cycle_map     = {"Daily": "daily", "Weekly": "weekly", "Monthly": "monthly",
                         "Yearly": "yearly", "One-Time": "one_time"}
        billing_label = st.selectbox("Billing Cycle", list(cycle_map.keys()), index=2)
        purchase_date = st.date_input("Purchase Date", value=date.today())
        submitted     = st.form_submit_button("Add Subscription", use_container_width=True)

    if submitted:
        if not name.strip() or price <= 0:
            st.error("Enter a valid name and price.")
        else:
            payload = {
                "name": name.strip(), "price": price, "currency": currency,
                "category": category.lower(), "billing_cycle": cycle_map[billing_label],
                "status": "active",
                "purchase_date": str(purchase_date),
            }
            try:
                res = requests.post(f"{API_URL}/subscriptions", json=payload, timeout=5)
                if res.status_code == 201:
                    st.session_state["success_msg"] = f"'{name}' added successfully."
                    st.rerun()
                else:
                    st.error(res.json().get("detail", "Unknown error"))
            except Exception:
                st.error("Could not reach the API.")
                

# ─────────────────────────────────────────────
#  HERO HEADER
# ─────────────────────────────────────────────
st.markdown(
    f'<h1 style="font-family:Inter,sans-serif;font-size:32px;font-weight:800;'
    f'color:{T1};letter-spacing:-0.5px;margin:0 0 4px;">Subscription Dashboard</h1>'
    f'<p style="font-family:Inter,sans-serif;font-size:13px;color:{T3};margin:0 0 28px;">'
    f'{date.today().strftime("%A, %B %d %Y")}</p>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
#  FETCH DATA
# ─────────────────────────────────────────────
summary   = get_data("subscriptions/summary")
subs_list = get_data("subscriptions")

# ─────────────────────────────────────────────
#  ALERT BANNER (Bills due in 3 days)
# ─────────────────────────────────────────────
if subs_list:
    today_    = date.today()
    threshold = today_ + timedelta(days=3)
    upcoming  = []
    for s in subs_list:
        nbd = s.get("next_billing_date")
        if nbd and nbd != "None":
            try:
                d = date.fromisoformat(nbd)
                if today_ <= d <= threshold:
                    upcoming.append((s["name"], d))
            except ValueError:
                pass

    if upcoming:
        pills = "".join(
            f'<span style="background:{WARNING}22;color:{WARNING};'
            f'border:1px solid {WARNING}55;border-radius:20px;'
            f'padding:3px 12px;font-size:12px;font-weight:600;'
            f'margin-right:6px;font-family:Inter,sans-serif;">'
            f'⚡ {n} — {d.strftime("%b %d")}</span>'
            for n, d in upcoming
        )
        st.markdown(
            f'<div style="background:{WARNING}11;border:1px solid {WARNING}44;'
            f'border-radius:10px;padding:14px 20px;margin-bottom:22px;'
            f'display:flex;align-items:center;gap:14px;">'
            f'<span style="font-size:20px;">🔔</span>'
            f'<div><span style="font-size:11px;font-weight:700;color:{WARNING};'
            f'text-transform:uppercase;letter-spacing:.5px;font-family:Inter,sans-serif;">'
            f'Billing soon</span>'
            f'<div style="margin-top:5px;">{pills}</div></div></div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
#  METRIC CARDS
# ─────────────────────────────────────────────
if summary:
    burn_rate    = summary["monthly_burn_rate_ils"]
    active_count = summary["active_subscriptions"]
    pct          = (burn_rate / budget_target * 100) if budget_target > 0 else 0
    bar_color    = DANGER if pct > 100 else WARNING if pct > 80 else SUCCESS
    bar_pct      = min(pct, 100)

    c1, c2, c3 = st.columns(3)

    def metric_card(col, gradient, label, value, sub_text, extra_html=""):
        col.markdown(
            f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:14px;'
            f'padding:22px 24px;position:relative;overflow:hidden;'
            f'font-family:Inter,sans-serif;">'
            f'<div style="position:absolute;top:0;left:0;right:0;height:3px;'
            f'background:{gradient};border-radius:14px 14px 0 0;"></div>'
            f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.7px;color:{T3};margin-bottom:12px;">{label}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:32px;'
            f'font-weight:700;color:{T1};letter-spacing:-1px;">{value}</div>'
            f'{extra_html}'
            f'<div style="font-size:11px;color:{T3};margin-top:8px;">{sub_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    metric_card(c1,
                f"linear-gradient(90deg,{ACCENT},{SUCCESS})",
                "Monthly Burn Rate",
                f"₪{burn_rate:,.2f}",
                "normalized to ILS")

    metric_card(c2,
                f"linear-gradient(90deg,{SUCCESS},{ACCENT})",
                "Active Subscriptions",
                str(active_count),
                "services running")

    metric_card(c3,
                f"linear-gradient(90deg,{bar_color},{bar_color}99)",
                "Budget Utilization",
                f'<span style="color:{bar_color};">{pct:.1f}%</span>',
                f"of ₪{budget_target:,} target",
                extra_html=(
                    f'<div style="background:{BORDER};border-radius:99px;height:5px;'
                    f'margin-top:10px;overflow:hidden;">'
                    f'<div style="width:{bar_pct}%;height:100%;background:{bar_color};'
                    f'border-radius:99px;"></div></div>'
                ))

st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────
if subs_list:
    df = pd.DataFrame(subs_list)
    if "purchase_date" in df.columns:
        df["purchase_date"] = pd.to_datetime(df["purchase_date"]).dt.date

    t1, t2 = st.tabs(["  📋  Manage Subscriptions  ", "  📊  Expense Analytics  "])

    # ── TAB 1: TABLE ──────────────────────────────────────────────────────
    # ── TAB 1: TABLE ──────────────────────────────────────────────────────
    with t1:
        h_left, h_right = st.columns([4, 1])
        h_left.markdown(
            f'<p style="font-size:16px;font-weight:700;color:{T1};'
            f'font-family:Inter,sans-serif;margin:0;">Active Inventory</p>'
            f'<p style="font-size:12px;color:{T3};font-family:Inter,sans-serif;'
            f'margin:3px 0 14px;">{len(df)} subscriptions tracked</p>',
            unsafe_allow_html=True,
        )

        # Excel export
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            ex = df.drop(columns=["id"], errors="ignore")
            ex.to_excel(writer, index=False, sheet_name="Subscriptions")
            ws = writer.sheets["Subscriptions"]
            for col in ws.columns:
                w = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = max(w + 5, 18)
        h_right.download_button(
            "📥 Export", data=buf.getvalue(), file_name="subman_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # 🎛️ 🔥 שורת פילטרים ומיון הייטקית חדשה ומתוחכמת
        st.markdown('<p style="font-size:11px;font-weight:700;color:' + T3 + ';text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">Filters & Sorting</p>', unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        
        with f1:
            # פילטר קטגוריות דינמי (לוקח את הרשימה הקיימת ומוסיף אופציית All)
            all_categories = ["All Categories"] + [c.capitalize() for c in df["category"].unique()]
            selected_cat = st.selectbox("Filter by Category", all_categories, label_visibility="collapsed")
            
        with f2:
            # אפשרויות מיון מתקדמות
            sort_options = {
                "Default (None)": None,
                "Price: High to Low 📉": ("price", False),
                "Price: Low to High 📈": ("price", True),
                "Closest Next Bill 📅": ("next_billing_date", True),
                "Newest Purchased 🆕": ("purchase_date", False)
            }
            selected_sort = st.selectbox("Sort Table By", list(sort_options.keys()), label_visibility="collapsed")

        # 🧠 החלת הפילטרים והמיון על ה-DataFrame בלייב באמצעות Pandas
        working_df = df.copy()
        
        # 1. החלת סינון קטגוריה
        # 🧠 החלת הפילטרים והמיון על ה-DataFrame בלייב באמצעות Pandas
        working_df = df.copy()
        
        # 1. החלת סינון קטגוריה (חסין ל-Case Sensitivity ורווחים)
        if selected_cat != "All Categories":
            working_df = working_df[working_df["category"].str.lower().str.strip() == selected_cat.lower().strip()]
            
        # 2. החלת לוגיקת המיון
        sort_config = sort_options[selected_sort]
        if sort_config:
            col_name, ascending_flag = sort_config
            if col_name == "next_billing_date":
                # טיפול חכם בשדות 'None' של מנויים חד פעמיים כדי שלא יקריסו את המיון של התאריכים
                working_df["sort_date"] = pd.to_datetime(working_df["next_billing_date"], errors="coerce")
                # מציב תאריך רחוק מאוד עבור 'None' כדי שהם תמיד יופיעו בסוף הרשימה
                working_df["sort_date"] = working_df["sort_date"].fillna(pd.Timestamp("2099-12-31"))
                working_df = working_df.sort_values(by="sort_date", ascending=ascending_flag).drop(columns=["sort_date"])
            else:
                working_df = working_df.sort_values(by=col_name, ascending=ascending_flag)
            
        # Build table rows מה-DataFrame המסונן והממוין החדש
        rows_html = ""
        for _, row in working_df.iterrows():
            nbd = row.get("next_billing_date", "")
            nbd_display = "—" if (not nbd or nbd == "None") else str(nbd)
            rows_html += (
                f'<tr style="border-bottom:1px solid {BORDER};">'
                f'<td style="padding:12px 16px;font-weight:600;color:{T1};'
                f'font-family:Inter,sans-serif;">{row.get("name","")}</td>'
                f'<td style="padding:12px 16px;">{cat_pill(str(row.get("category","other")))}</td>'
                f'<td style="padding:12px 16px;font-family:\'JetBrains Mono\',monospace;'
                f'font-size:13px;color:{T1};">'
                f'{row.get("price",0):.2f} '
                f'<span style="color:{T3};font-size:11px;">{row.get("currency","ILS")}</span></td>'
                f'<td style="padding:12px 16px;color:{T2};font-size:13px;">{row.get("billing_cycle","")}</td>'
                f'<td style="padding:12px 16px;color:{T2};font-size:12px;'
                f'font-family:\'JetBrains Mono\',monospace;">{row.get("purchase_date","")}</td>'
                f'<td style="padding:12px 16px;color:{T2};font-size:12px;'
                f'font-family:\'JetBrains Mono\',monospace;">{nbd_display}</td>'
                f'</tr>'
            )

        th_style = (f'padding:10px 16px;text-align:left;font-size:10px;font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:.8px;color:{T3};'
                    f'font-family:Inter,sans-serif;')

        st.markdown(
            f'<div style="border:1px solid {BORDER};border-radius:12px;'
            f'overflow:hidden;margin-top:10px;margin-bottom:20px;">'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            f'<thead>'
            f'<tr style="background:{CARD2};border-bottom:1px solid {BORDER};">'
            f'<th style="{th_style}">Name</th>'
            f'<th style="{th_style}">Category</th>'
            f'<th style="{th_style}">Price</th>'
            f'<th style="{th_style}">Cycle</th>'
            f'<th style="{th_style}">Purchased</th>'
            f'<th style="{th_style}">Next Bill</th>'
            f'</tr>'
            f'</thead>'
            f'<tbody style="background:{CARD};">'
            f'{rows_html}'
            f'</tbody>'
            f'</table>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Manage controls - עושה שימוש ברשימה המקורית המלאה כדי שיהיה אפשר למחוק תמיד הכל
        st.markdown(section_label("Manage"), unsafe_allow_html=True)
        cs, cd = st.columns([5, 1])
        selected = cs.selectbox("Select", df["name"].tolist(), label_visibility="collapsed")

        if cd.button("🗑 Delete", use_container_width=True):
            if delete_sub(selected):
                st.session_state["success_msg"] = f"'{selected}' deleted."
                st.rerun()
            else:
                st.error("Delete failed.")

    # ── TAB 2: ANALYTICS ────────────────────────────────────────────────────
    with t2:
        a1, a2 = st.columns(2)

        with a1:
            st.markdown(
                f'<p style="font-size:13px;font-weight:600;color:{T2};'
                f'font-family:Inter,sans-serif;margin-bottom:6px;">Spend by Category</p>',
                unsafe_allow_html=True,
            )
            cat_df = df.groupby("category")["price"].sum().reset_index()
            colors = [CAT_COLORS.get(c.lower(), CAT_COLORS["other"]) for c in cat_df["category"]]
            fig1 = go.Figure(go.Pie(
                labels=cat_df["category"].str.capitalize(),
                values=cat_df["price"],
                hole=0.6,
                marker=dict(colors=colors, line=dict(color=BG, width=2)),
                textinfo="label+percent",
                textfont=dict(family="Inter", size=12, color=T1),
                hovertemplate="<b>%{label}</b><br>₪%{value:.2f}<extra></extra>",
            ))
            fig1.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False, height=260,
            )
            st.plotly_chart(fig1, use_container_width=True)

        with a2:
            st.markdown(
                f'<p style="font-size:13px;font-weight:600;color:{T2};'
                f'font-family:Inter,sans-serif;margin-bottom:6px;">Spend by Currency</p>',
                unsafe_allow_html=True,
            )
            curr_df  = df.groupby("currency")["price"].sum().reset_index()
            curr_col = {"ILS": ACCENT, "USD": SUCCESS, "EUR": WARNING}
            fig2 = go.Figure(go.Bar(
                x=curr_df["currency"],
                y=curr_df["price"],
                marker_color=[curr_col.get(c, T3) for c in curr_df["currency"]],
                marker_line_width=0,
                text=curr_df["price"].apply(lambda v: f"₪{v:.0f}"),
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=11, color=T1),
                hovertemplate="<b>%{x}</b><br>₪%{y:.2f}<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, color=T3, tickfont=dict(family="Inter", size=12, color=T2)),
                yaxis=dict(showgrid=True, gridcolor=BORDER, color=T3,
                           tickfont=dict(family="Inter", size=11, color=T2)),
                margin=dict(t=28, b=10, l=0, r=0),
                height=260, bargap=0.4,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # 7-day billing timeline
        st.markdown(
            f'<div style="height:1px;background:{BORDER};margin:8px 0 20px;"></div>'
            f'<p style="font-size:14px;font-weight:700;color:{T1};'
            f'font-family:Inter,sans-serif;margin-bottom:12px;">'
            f'Billing Timeline — Next 7 Days</p>',
            unsafe_allow_html=True,
        )

        today_   = date.today()
        week_end = today_ + timedelta(days=7)
        timeline = []
        for s in subs_list:
            nbd = s.get("next_billing_date")
            if nbd and nbd != "None":
                try:
                    d = date.fromisoformat(nbd)
                    if today_ <= d <= week_end:
                        timeline.append(s)
                except ValueError:
                    pass

        if timeline:
            tl = ""
            for s in sorted(timeline, key=lambda x: x["next_billing_date"]):
                d        = date.fromisoformat(s["next_billing_date"])
                days_out = (d - today_).days
                col_tl   = DANGER if days_out == 0 else WARNING if days_out <= 2 else ACCENT
                label    = "Today" if days_out == 0 else f"in {days_out}d"
                tl += (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:14px 18px;border:1px solid {BORDER};border-radius:10px;'
                    f'background:{CARD};margin-bottom:8px;font-family:Inter,sans-serif;">'
                    f'<div style="display:flex;align-items:center;gap:14px;">'
                    f'<div style="width:9px;height:9px;border-radius:50%;background:{col_tl};'
                    f'box-shadow:0 0 8px {col_tl};flex-shrink:0;"></div>'
                    f'<div>'
                    f'<div style="font-weight:600;font-size:13px;color:{T1};">{s["name"]}</div>'
                    f'<div style="font-size:11px;color:{T3};margin-top:2px;">'
                    f'{s["category"].capitalize()} · {s["billing_cycle"]}</div>'
                    f'</div></div>'
                    f'<div style="text-align:right;">'
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:15px;'
                    f'font-weight:700;color:{T1};">₪{s["price"]:.2f}</div>'
                    f'<div style="font-size:11px;color:{col_tl};font-weight:600;'
                    f'margin-top:2px;">{label}</div>'
                    f'</div></div>'
                )
            st.markdown(tl, unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div style="text-align:center;padding:36px;'
                f'border:1px dashed {BORDER};border-radius:12px;'
                f'color:{T3};font-size:13px;font-family:Inter,sans-serif;">'
                f'No bills due in the next 7 days 🎉</div>',
                unsafe_allow_html=True,
            )

else:
    st.markdown(
        f'<div style="text-align:center;padding:64px 20px;'
        f'border:1px dashed {BORDER};border-radius:16px;margin-top:24px;'
        f'font-family:Inter,sans-serif;">'
        f'<div style="font-size:40px;margin-bottom:14px;">📭</div>'
        f'<div style="font-size:17px;font-weight:700;color:{T1};margin-bottom:6px;">'
        f'No subscriptions yet</div>'
        f'<div style="font-size:13px;color:{T3};">'
        f'Add your first one from the sidebar to get started.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )