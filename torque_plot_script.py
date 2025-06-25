import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import savgol_filter
import io
import matplotlib.pyplot as plt
import plotly.io as pio

st.set_page_config(layout="wide")

uploaded_file = st.file_uploader("📁 העלה קובץ CSV עם מדידות", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    filename = uploaded_file.name

    df.columns = [col.strip() for col in df.columns]
    df = df.rename(columns={
        'X': 'Time_ms',
        '#03.002': 'Speed_RPM',
        '#04.002': 'Current_A'
    })

    df['Torque_raw'] = -df['Current_A'] * 4.8
    df['Torque_smoothed'] = savgol_filter(df['Torque_raw'], window_length=51, polyorder=3)
    df['Speed_RPM'] = -df['Speed_RPM']
    df['Speed_smoothed'] = savgol_filter(df['Speed_RPM'], window_length=51, polyorder=3)  # ← תוקן כאן

    mean_speed = df[df['Speed_smoothed'] > 10]['Speed_smoothed'].mean()
    threshold = mean_speed - 10
    st.info(f"סף סינון מהירות: {threshold:.2f} RPM")

    sections = []
    current_section = []
    for i in range(len(df)):
        if df['Speed_smoothed'][i] > threshold:
            current_section.append(df['Torque_smoothed'][i])
        else:
            if current_section:
                sections.append(current_section)
                current_section = []
    if current_section:
        sections.append(current_section)

    if not sections:
        st.error("לא נמצאו מקטעים עם מהירות מעל הסף")
        st.stop()

    min_len = min(len(sec) for sec in sections)
    trimmed_sections = [sec[:min_len] for sec in sections]
    section_array = np.array(trimmed_sections)
    mean_curve = section_array.mean(axis=0)
    max_torque = section_array.max()
    mean_torque = mean_curve.mean()

    st.title(f"🔎 תוצאות עבור הקובץ: {filename}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 גרף מומנט + מהירות (אינטראקטיבי עם סקאלות נפרדות)")
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Torque_raw'],
                                  mode='lines', name='Torque Raw', opacity=0.3), secondary_y=False)
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Torque_smoothed'],
                                  mode='lines', name='Torque Smoothed'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=df['Time_ms'], y=df['Speed_smoothed'],
                                  mode='lines', name='Speed [RPM]', line=dict(dash='dash')), secondary_y=True)

        fig1.update_layout(title="Torque + Speed",
                           xaxis_title="Time [ms]",
                           height=500,
                           legend_title="Signal")
        fig1.update_yaxes(title_text="Torque [Nm]", secondary_y=False)
        fig1.update_yaxes(title_text="Speed [RPM]", secondary_y=True)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("📈 גרף ממוצע מומנט מקטעים (אינטראקטיבי)")
        fig2 = go.Figure()
        for sec in section_array:
            fig2.add_trace(go.Scatter(y=sec, mode='lines', opacity=0.3, line=dict(color='orange'), showlegend=False))
        fig2.add_trace(go.Scatter(y=mean_curve, mode='lines', name='Mean Curve', line=dict(color='black')))
        fig2.add_hline(y=mean_torque, line_dash="dash", line_color="blue",
                       annotation_text=f"Mean = {mean_torque:.2f}", annotation_position="bottom right")
        fig2.add_hline(y=max_torque, line_dash="dash", line_color="red",
                       annotation_text=f"Max = {max_torque:.2f}", annotation_position="top right")
        fig2.update_layout(xaxis_title="Time Index", yaxis_title="Torque [Nm]",
                           legend_title="", height=500)
        st.plotly_chart(fig2, use_container_width=True)

    # גרף משולב להורדה (matplotlib)
    fig_combined, axs_combined = plt.subplots(1, 2, figsize=(16, 6))
    ax1c = axs_combined[0]
    ax2c = ax1c.twinx()
    ax1c.plot(df['Time_ms'], df['Torque_raw'], alpha=0.3, label='Raw', color='gray')
    ax1c.plot(df['Time_ms'], df['Torque_smoothed'], label='Smoothed', color='blue')
    ax2c.plot(df['Time_ms'], df['Speed_smoothed'], label='Speed', linestyle='--', color='green')
    ax1c.set_xlabel("Time [ms]")
    ax1c.set_ylabel("Torque [Nm]")
    ax2c.set_ylabel("Speed [RPM]")
    ax1c.set_title("Torque + Speed")

    axc = axs_combined[1]
    for sec in section_array:
        axc.plot(sec, alpha=0.4, color='orange')
    axc.plot(mean_curve, label='Mean Curve', color='black')
    axc.axhline(mean_torque, color='blue', linestyle='--', label=f'Mean = {mean_torque:.2f}')
    axc.axhline(max_torque, color='red', linestyle='--', label=f'Max = {max_torque:.2f}')
    axc.set_xlabel("Time Index")
    axc.set_ylabel("Torque [Nm]")
    axc.set_title(f'Smoothed Torque > {threshold:.2f} RPM')
    axc.grid()
    axc.legend()
    fig_combined.tight_layout()

    st.subheader("⬇️ הורדה של שני הגרפים כתמונה אחת")
    combined_buf = io.BytesIO()
    fig_combined.savefig(combined_buf, format="png")
    combined_buf.seek(0)

    st.download_button(
        label="📥 הורד גרף משולב",
        data=combined_buf.getvalue(),
        file_name=f"{filename}_combined.png",
        mime="image/png"
    )

    # הורדת קובץ CSV עם עמודות מקוריות + ממוצע מומנט כעמודה חדשה
    df_export = df.copy()
    df_export['Torque_mean_value'] = mean_torque

    csv_buf = io.StringIO()
    df_export.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    st.download_button(
        label="📄 הורד קובץ נתונים עם ממוצע מומנט",
        data=csv_buf.getvalue(),
        file_name=f"{filename.replace('.csv','')}_mean_{mean_torque:.2f}.csv",
        mime="text/csv"
    )

    # יצירת HTML עם שני הגרפים
    html_buf = io.StringIO()
    html_content = f"<h2>Torque + Speed</h2>" + pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')
    html_content += f"<h2>Mean Torque Segments</h2>" + pio.to_html(fig2, full_html=False, include_plotlyjs=False)
    html_buf.write(html_content)
    html_buf.seek(0)

    st.download_button(
        label="🌐 הורד גרפים אינטרקטיביים (HTML)",
        data=html_buf.getvalue(),
        file_name=f"{filename.replace('.csv','')}_interactive.html",
        mime="text/html"
    )
