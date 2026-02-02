import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import savgol_filter
import io
import matplotlib.pyplot as plt
import plotly.io as pio

# הגדרת דף רחב
st.set_page_config(layout="wide", page_title="Torque Visualizer")

st.title("📊 מנתח נתוני מומנט ומהירות")

uploaded_file = st.file_uploader("📁 העלה קובץ CSV עם מדידות", type="csv")

if uploaded_file is not None:
    # --- שלב 1: זיהוי אוטומטי של תחילת הנתונים ---
    content = uploaded_file.getvalue().decode("utf-8").splitlines()
    start_line = 0
    for i, line in enumerate(content):
        # מחפש את השורה שמכילה את כותרות העמודות (X עבור זמן)
        if line.startswith("X,") or "X," in line:
            start_line = i
            break
    
    uploaded_file.seek(0)
    # טעינת הקובץ החל מהשורה שנמצאה
    df = pd.read_csv(uploaded_file, skiprows=start_line)
    filename = uploaded_file.name

    # ניקוי שמות עמודות מרווחים
    df.columns = [col.strip() for col in df.columns]
    
    # שינוי שמות עמודות לפי הפורמט של הקבצים שלך 
    df = df.rename(columns={
        'X': 'Time_ms',
        '#03.002': 'Speed_RPM',
        '#04.002': 'Current_A'
    })

    # --- שלב 2: ניקוי והמרת נתונים ---
    # המרה למספרים (ערכים לא תקינים יהפכו ל-NaN)
    for col in ['Time_ms', 'Speed_RPM', 'Current_A']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # הסרת שורות ריקות (מונע שגיאות בסינון ובחישובים)
    df = df.dropna(subset=['Time_ms', 'Speed_RPM', 'Current_A'])

    if df.empty:
        st.error("הקובץ אינו מכיל נתונים מספריים תקינים לאחר ניקוי.")
        st.stop()

    # --- שלב 3: חישובים והחלקה ---
    df['Torque_raw'] = -df['Current_A'] * 4.8
    df['Speed_RPM_fixed'] = -df['Speed_RPM']

    # הגדרת חלון החלקה דינמי (חייב להיות אי-זוגי וקטן ממספר השורות)
    window = 51
    if len(df) < window:
        window = len(df) if len(df) % 2 != 0 else len(df) - 1

    if window > 3:
        df['Torque_smoothed'] = savgol_filter(df['Torque_raw'], window, polyorder=3)
        df['Speed_smoothed'] = savgol_filter(df['Speed_RPM_fixed'], window, polyorder=3)
    else:
        df['Torque_smoothed'] = df['Torque_raw']
        df['Speed_smoothed'] = df['Speed_RPM_fixed']

    # --- שלב 4: חלוקה למקטעים לפי מהירות ---
    # מציאת מהירות ממוצעת רק בזמן פעולה (מעל 10 RPM)
    active_mask = df['Speed_smoothed'] > 10
    if not active_mask.any():
        st.warning("לא נמצאה מהירות מעל 10 RPM. מציג נתונים ללא חלוקה למקטעים.")
        threshold = 0
    else:
        mean_speed = df[active_mask]['Speed_smoothed'].mean()
        threshold = max(0, mean_speed - 10)
    
    st.info(f"סף סינון מהירות שנקבע: {threshold:.2f} RPM")

    sections = []
    current_section = []
    # לוגיקת הפרדה למקטעים
    for i in range(len(df)):
        if df['Speed_smoothed'].iloc[i] > threshold:
            current_section.append(df['Torque_smoothed'].iloc[i])
        else:
            if current_section:
                sections.append(current_section)
                current_section = []
    if current_section:
        sections.append(current_section)

    # --- שלב 5: תצוגה גרפית ---
    st.header(f"🔎 ניתוח עבור: {filename}")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 מומנט ומהירות לאורך זמן")
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Torque_raw'], name='Torque Raw', opacity=0.3), secondary_y=False)
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Torque_smoothed'], name='Torque Smoothed'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Speed_smoothed'], name='Speed [RPM]', line=dict(dash='dash')), secondary_y=True)
        fig1.update_yaxes(title_text="Torque [Nm]", secondary_y=False)
        fig1.update_yaxes(title_text="Speed [RPM]", secondary_y=True)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("📈 השוואת מקטעים וממוצע")
        if sections:
            min_len = min(len(sec) for sec in sections)
            trimmed_sections = [sec[:min_len] for sec in sections]
            section_array = np.array(trimmed_sections)
            mean_curve = section_array.mean(axis=0)
            
            fig2 = go.Figure()
            for sec in section_array:
                fig2.add_trace(go.Scatter(y=sec, mode='lines', opacity=0.2, line=dict(color='orange'), showlegend=False))
            fig2.add_trace(go.Scatter(y=mean_curve, mode='lines', name='Mean Curve', line=dict(color='black', width=3)))
            st.plotly_chart(fig2, use_container_width=True)
            
            # נתונים להורדה
            mean_torque = mean_curve.mean()
            st.metric("מומנט ממוצע במקטעים", f"{mean_torque:.2f} Nm")
        else:
            st.write("לא נמצאו מקטעים לניתוח.")

    # --- שלב 6: אפשרויות הורדה ---
    st.divider()
    st.subheader("⬇️ הורדת תוצאות")
    
    # הכנת CSV להורדה
    df_export = df.copy()
    if sections: df_export['Section_Mean_Torque'] = mean_torque
    csv_buf = io.StringIO()
    df_export.to_csv(csv_buf, index=False)
    
    st.download_button(
        label="📥 הורד נתונים מעובדים (CSV)",
        data=csv_buf.getvalue(),
        file_name=f"processed_{filename}",
        mime="text/csv"
    )
