import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

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

    df['Torque_raw'] = -df['Current_A'] * 1.6
    df['Torque_smoothed'] = savgol_filter(df['Torque_raw'], window_length=51, polyorder=3)
    df['Speed_RPM'] = -df['Speed_RPM']

    mean_speed = df[df['Speed_RPM'] > 10]['Speed_RPM'].mean()
    threshold = mean_speed - 5

    sections = []
    current_section = []
    for i in range(len(df)):
        if df['Speed_RPM'][i] > threshold:
            current_section.append(df['Torque_smoothed'][i])
        else:
            if current_section:
                sections.append(current_section)
                current_section = []
    if current_section:
        sections.append(current_section)

    min_len = min(len(sec) for sec in sections)
    section_array = np.array([s[:min_len] for s in sections])
    mean_curve = section_array.mean(axis=0)
    max_torque = section_array.max()
    mean_torque = mean_curve.mean()

    st.title(f"תוצאות עבור הקובץ: {filename}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔷 גרף מומנט ומהירות")
        fig1, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(df['Time_ms'], df['Torque_raw'], alpha=0.3, label='Raw', color='gray')
        ax1.plot(df['Time_ms'], df['Torque_smoothed'], label='Smoothed', color='blue')
        ax2.plot(df['Time_ms'], df['Speed_RPM'], label='Speed', linestyle='--', color='green')
        ax1.set_xlabel("Time [ms]")
        ax1.set_ylabel("Torque [Nm]")
        ax2.set_ylabel("Speed [RPM]")
        ax1.grid()
        fig1.tight_layout()
        st.pyplot(fig1)

    with col2:
        st.subheader(f"🟧 קטעים מעל {threshold:.1f} סל\"ד")
        fig2, ax = plt.subplots()
        for sec in section_array:
            ax.plot(sec, alpha=0.4, color='orange')
        ax.plot(mean_curve, label='Mean Curve', color='black')
        ax.axhline(mean_torque, color='blue', linestyle='--', label=f'Mean = {mean_torque:.2f}')
        ax.axhline(max_torque, color='red', linestyle='--', label=f'Max = {max_torque:.2f}')
        ax.set_ylabel("Torque [Nm]")
        ax.set_xlabel("Time Index")
        ax.grid()
        ax.legend()
        fig2.tight_layout()
        st.pyplot(fig2)
