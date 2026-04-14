import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="SubMan Pro", layout="wide", page_icon="💰")


@st.dialog("הודעת מערכת")
def show_success_modal(message):
    # הוספנו direction: rtl; כדי לסדר את כיוון הטקסט בעברית
    st.markdown(f"""
        <div style="direction: rtl; text-align: center; padding: 20px;">
            <h1 style="color: #28a745; margin-bottom: 20px;">✅ מעולה!</h1>
            <h3 style="color: #333;">{message}</h3>
        </div>
    """, unsafe_allow_html=True)
    st.balloons()
    if st.button("סגור והמשך ✖️", use_container_width=True):
        del st.session_state["success_msg"]
        st.rerun()

if "success_msg" in st.session_state:
    show_success_modal(st.session_state["success_msg"])

st.title("💰 SubMan Pro - Intelligent Insights")
st.markdown("---")

def get_data(endpoint):
    try:
        res = requests.get(f"{API_URL}/{endpoint}")
        return res.json() if res.status_code == 200 else None
    except: return None

def delete_sub(name):
    try:
        res = requests.delete(f"{API_URL}/subscriptions/{name}")
        return res.status_code == 200
    except: return False

st.sidebar.header("➕ Add Subscription")
with st.sidebar.form("sub_form", clear_on_submit=True):
    name = st.text_input("Name")
    price = st.number_input("Price", step=0.5)
    currency = st.selectbox("Currency", ["ILS", "USD", "EUR"])
    category = st.selectbox("Category", ["Entertainment", "Software", "Health", "Food", "Other"])
    submit = st.form_submit_button("Add Subscription")

if submit:
    if not name or price <= 0:
        st.sidebar.error("Please provide a valid name and price greater than 0!")
    else:
        payload = {
            "name": name, "price": price, "currency": currency,
            "category": category.lower(), "billing_cycle": "monthly", "status": "active"
        }
        res = requests.post(f"{API_URL}/subscriptions", json=payload)
        
        if res.status_code == 201:
            st.session_state["success_msg"] = f"המנוי ל-'{name}' נוסף בהצלחה!"
            st.rerun()
        else:
            error_detail = res.json().get('detail', 'Unknown error')
            st.sidebar.error(f"שגיאה: {error_detail}")

summary = get_data("subscriptions/summary")
subs_list = get_data("subscriptions")

if summary:
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Burn (ILS)", f"₪{summary['monthly_burn_rate_ils']:.2f}")
    c2.metric("Active Subs", summary['active_subscriptions'])
    with c3:
        if summary['monthly_burn_rate_ils'] > 500:
            st.warning("⚠️ High spending detected!")
        else:
            st.info("💡 Spending is normalized")

st.markdown("---")

if subs_list:
    df = pd.DataFrame(subs_list)
    t1, t2 = st.tabs(["📋 Manage", "📊 Analytics"])
    
    with t1:
        st.subheader("Manage Your Subscriptions")
        
        # כפתור הורדה ל-CSV (Quick Win)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_data,
            file_name="subman_report.csv",
            mime="text/csv",
        )
        st.write("") # רווח קטן
        
        for idx, row in df.iterrows():
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(f"**{row['name']}**")
            cols[1].write(f"{row['price']} {row['currency']}")
            cols[2].write(row['category'])
            cols[3].write(row['status'])
            
            if cols[4].button("🗑️", key=f"btn_{row['name']}"):
                if delete_sub(row['name']):
                    st.session_state["success_msg"] = f"ההוצאה על מנוי ל-'{row['name']}' נמחקה בהצלחה"
                    st.rerun()

    with t2:
        st.subheader("Expenses Distribution")
        fig = px.pie(df, values='price', names='category', title="Monthly Expenses by Category")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Start by adding your first subscription in the sidebar!")