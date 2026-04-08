import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="TDS Compliance Pro V4", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .status-box { padding: 20px; border-radius: 10px; margin-top: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        df.columns = [c.strip() for c in df.columns]
        # Clean text data
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        return df
    except Exception as e:
        st.error(f"Setup Error: {e}")
        return None

df = load_data()

if df is not None:
    st.sidebar.title("🛡️ Compliance Settings")
    st.sidebar.info("V4 Pro: Automatic Threshold Detection")
    
    st.title("🏛️ TDS Compliance Professional - V4")
    st.caption(f"Reporting Date: {datetime.now().strftime('%d %B, %Y')}")
    st.write("---")

    # INPUT AREA
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Payment Profile")
        sections = sorted([s for s in df['Section'].unique() if str(s) != 'nan'])
        section = st.selectbox("1. Select Section", options=sections)
        
        f_df = df[df['Section'] == section]
        natures = sorted([n for n in f_df['Nature of Payment'].unique() if str(n) != 'nan'])
        nature_sel = st.selectbox("2. Nature of Payment", options=natures)
        
        amount = st.number_input("3. Transaction Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        st.subheader("👤 Payee Configuration")
        sub_f = f_df[f_df['Nature of Payment'] == nature_sel]
        p_types = sorted([p for p in sub_f['Payee Type'].unique() if str(p) != 'nan'])
        
        if len(p_types) > 1:
            payee_sel = st.selectbox("4. Category of Payee", options=p_types)
        else:
            payee_sel = p_types[0] if p_types else "Any Resident"
            st.info(f"Detected Category: **{payee_sel}**")

        pan_status = st.radio("5. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("6. Transaction Date")
        calc_mode = st.radio("7. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    # 3. CALCULATION & COMPLIANCE LOGIC
    if st.button("🚀 EXECUTE TDS CHECK", use_container_width=True):
        target = pd.to_datetime(pay_date)
        final_match = sub_f[sub_f['Payee Type'] == payee_sel]
        rule = final_match[(final_match['Effective From'] <= target) & (final_match['Effective To'] >= target)]
        
        if rule.empty and not final_match.empty:
            rule = final_match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # Apply 194C Aggregate Logic if selected
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                # Automatic 20% PAN Penalty
                final_rate = 20.0 if pan_status == "No" else base_rate
                calculated_tds = (amount * final_rate) / 100
                
                # TOP METRICS DASHBOARD
                r1, r2, r3 = st.columns(3)
                
                if amount > thresh:
                    # SITUATION A: BREACHED
                    r1.metric("TDS PAYABLE", f"₹{calculated_tds:,.2f}", delta="DEDUCT NOW", delta_color="inverse")
                    r2.metric("APPLIED RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="BREACHED")
                    
                    st.success(f"### ✅ CALCULATED TDS: ₹{calculated_tds:,.2f}")
                    st.write(f"**Compliance Note:** TDS is applicable as the amount (₹{amount:,.0f}) has breached the threshold of ₹{thresh:,.0f}.")
                else:
                    # SITUATION B: BELOW THRESHOLD
                    r1.metric("CALCULATED TDS", f"₹{calculated_tds:,.2f}", delta="NOT APPLICABLE")
                    r2.metric("POTENTIAL RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="NOT BREACHED")
                    
                    st.warning("### ⚠️ TDS NOT APPLICABLE")
                    st.write(f"**Compliance Note:** TDS is **not applicable** because the amount (₹{amount:,.0f}) is below the statutory threshold of **₹{thresh:,.0f}**.")
                    st.info(f"**Mathematical Breakdown:** If the threshold were exceeded, the TDS at {final_rate}% would have been ₹{calculated_tds:,.2f}.")

                with st.expander("📝 View Statutory Reference"):
                    st.write(f"**Section:** {section}")
                    st.write(f"**Payer:** {sel['Payer Category']}")
                    st.info(f"**Legal Basis:** {sel['Notes']}")
            
            except Exception as e:
                st.error(f"Data Error: Ensure Excel columns for Rate and Threshold are numbers. Error: {e}")
        else:
            st.error("No statutory rule found for this specific date and payee combination.")
