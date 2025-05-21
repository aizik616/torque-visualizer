
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

# Load the Excel file
file_path = 'binic- rothanium - 6.5nm - procedded.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Extract columns
time = df['Time (ms)']
torque = df['Torque [Nm]']

# Smooth the torque signal
smoothed_torque = savgol_filter(torque, window_length=51, polyorder=3)

# Calculate average and max torque
average_torque = np.mean(torque)
max_torque = np.max(torque)

# Plot
plt.figure(figsize=(12, 6))
plt.plot(time, torque, label='Raw Torque', alpha=0.5)
plt.plot(time, smoothed_torque, label='Smoothed Torque', linewidth=2)
plt.axhline(average_torque, color='green', linestyle='--', label=f'Average Torque = {average_torque:.3f} Nm')
plt.axhline(max_torque, color='red', linestyle='--', label=f'Max Torque = {max_torque:.3f} Nm')
plt.title('Torque vs. Time')
plt.xlabel('Time (ms)')
plt.ylabel('Torque [Nm]')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
