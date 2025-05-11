import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from scipy.signal import firwin, lfilter

# Streamlit Widgets
st.title('Filterbank Design mit Python')

# Eingabewerte
fs = 500.0  # Abtastrate (Hz)
nyquist = fs / 2  # Nyquist-Frequenz
num_bands = st.slider("Anzahl der Filterbänder", min_value=2, max_value=10, value=4)

# Zeitvektor
t = np.arange(0, 1.0, 1.0/fs)

# Signal erzeugen: Sinuswelle + Rauschen
f_sin = 5  # Frequenz der Sinuswelle (Hz)
noise_level = st.slider("Rauschstärke", min_value=0.0, max_value=1.0, value=0.5)
x = np.sin(2 * np.pi * f_sin * t) + np.random.normal(0, noise_level, t.shape)

# Frequenzbereiche für die Filterbank definieren
bands = [(1, 5), (6, 15), (16, 30), (31, 50)]  # Beispiel: 4 Filterbänder

# Filterbank erstellen
filters = []
for band in bands:
    lowcut, highcut = band
    band_filter = firwin(101, [lowcut/nyquist, highcut/nyquist], pass_zero=False)
    filters.append(band_filter)

# Anwenden der Filter auf das Signal
filtered_signals = []
for band_filter in filters:
    y = lfilter(band_filter, 1.0, x)
    filtered_signals.append(y)

# Plot der Ergebnisse
fig, axes = plt.subplots(len(filters)+1, 1, figsize=(10, 12))

# Originalsignal plotten
axes[0].plot(t, x, label='Original Signal', color='blue')
axes[0].set_title('Original Signal (Rauschen + Sinus)')
axes[0].set_xlabel('Zeit [s]')
axes[0].set_ylabel('Amplitude')
axes[0].grid(True)

# Gefilterte Signale plotten
for i, (band, y) in enumerate(zip(bands, filtered_signals)):
    axes[i+1].plot(t, y, label=f'Band {band[0]}-{band[1]} Hz', color=f'C{i+1}')
    axes[i+1].set_title(f'Gefiltertes Signal: {band[0]}-{band[1]} Hz Band')
    axes[i+1].set_xlabel('Zeit [s]')
    axes[i+1].set_ylabel('Amplitude')
    axes[i+1].grid(True)

# Layout und Anzeige
plt.tight_layout()
st.pyplot(fig)
