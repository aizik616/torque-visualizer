import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import savgol_filter
import io
import plotly.io as pio
from datetime import datetime

# הגדרת דף
st.set_page_config(layout="wide", page_title="Motor Torque Analyzer")

st.title("📊 מנתח מומנט פריצה ומדידות")

uploaded_file = st.file_uploader("📁 העלה קובץ CSV", type="csv")

if uploaded_file is not None:
    # --- שלב 1: קריאת נתונים ---
    content = uploaded_file.getvalue().decode("utf-8").splitlines()
    start_line = 0
    for i, line in enumerate(content):
        if line.startswith("X,") or "X," in line:
            start_line = i
            break
    
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, skiprows=start_line)
    
    df.columns = [col.strip() for col in df.columns]
    df = df.rename(columns={'X': 'Time_ms', '#03.002': 'Speed_RPM', '#04.002': 'Current_A'})

    for col in ['Time_ms', 'Speed_RPM', 'Current_A']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['Time_ms', 'Speed_RPM', 'Current_A'])

    # --- שלב 2: עיבוד והחלקה ---
    df['Torque_raw'] = -df['Current_A'] * 4.8
    df['Speed_RPM_fixed'] = -df['Speed_RPM']

    window = 51
    if len(df) < window:
        window = len(df) if len(df) % 2 != 0 else len(df) - 1

    if window > 3:
        df['Torque_smoothed'] = savgol_filter(df['Torque_raw'], window, polyorder=3)
        df['Speed_smoothed'] = savgol_filter(df['Speed_RPM_fixed'], window, polyorder=3)
    else:
        df['Torque_smoothed'] = df['Torque_raw']
        df['Speed_smoothed'] = df['Speed_RPM_fixed']

    # --- שלב 3: זיהוי מקטעים ומומנט פריצה ---
    active_mask = df['Speed_smoothed'] > 10
    threshold = (df[active_mask]['Speed_smoothed'].mean() - 10) if active_mask.any() else 0

    sections = []
    current_section = []
    for i in range(len(df)):
        if df['Speed_smoothed'].iloc[i] > threshold:
            current_section.append(df['Torque_smoothed'].iloc[i])
        else:
            if current_section:
                sections.append(current_section)
                current_section = []
    if current_section: sections.append(current_section)

    breakaway_torques = [max(sec) for sec in sections if len(sec) > 0]
    avg_breakaway = np.mean(breakaway_torques) if breakaway_torques else 0

    # --- שלב 4: תצוגת מדדים ---
    st.subheader(f"ניתוח עבור: {uploaded_file.name}")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric("מומנט פריצה ממוצע", f"{avg_breakaway:.2f} Nm")
    with m_col2:
        st.metric("מספר מחזורים שזוהו", len(sections))

    # --- שלב 5: יצירת הגרפים ---
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Torque_smoothed'], name='Torque [Nm]'), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Speed_smoothed'], name='Speed [RPM]', line=dict(dash='dot', color='green')), secondary_y=True)
    fig1.update_layout(title="מומנט ומהירות לאורך זמן", hovermode="x unified")

    fig2 = go.Figure()
    if sections:
        min_len = min(len(sec) for sec in sections)
        trimmed_sections = [sec[:min_len] for sec in sections]
        mean_curve = np.array(trimmed_sections).mean(axis=0)
        
        for sec in trimmed_sections:
            fig2.add_trace(go.Scatter(y=sec, mode='lines', opacity=0.2, line=dict(color='orange'), showlegend=False))
        fig2.add_trace(go.Scatter(y=mean_curve, name='ממוצע מחזורים', line=dict(color='black', width=3)))
        fig2.add_hline(y=avg_breakaway, line_dash="dash", line_color="red", 
                       annotation_text=f"Breakaway: {avg_breakaway:.2f} Nm")
    fig2.update_layout(title="השוואת מחזורי פריצה")

    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)

    # --- שלב 6: יצירת שם קובץ דינמי והורדה ---
    st.divider()
    
    # יצירת חותמת זמן ושם קובץ לפי הפורמט שביקשת
    now = datetime.now().strftime("%d.%m.%y - %H:%M")
    dynamic_filename = f"{now} - {avg_breakaway:.2f}Nm.html"

    html_report = f"""
    <html>
    <head><meta charset='utf-8'></head>
    <body dir='rtl' style='font-family: sans-serif; padding: 20px;'>
        <h1>דוח ניתוח מומנט</h1>
        <p>תאריך הרצה: {now}</p>
        <hr>
        <h2 style='color: red;'>מומנט פריצה ממוצע: {avg_breakaway:.2f} Nm</h2>
        <h3>מספר מחזורים שנותחו: {len(sections)}</h3>
        <div style='margin-bottom: 50px;'>{pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')}</div>
        <div>{pio.to_html(fig2, full_html=False, include_plotlyjs=False)}</div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 הורד דוח גרפים אינטראקטיבי",
        data=html_report,
        file_name=dynamic_filename,
        mime="text/html"
    )
