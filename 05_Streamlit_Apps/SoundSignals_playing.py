import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from scipy.signal import firwin, lfilter

# Streamlit Widgets
st.title('Digitales Filterdesign: Tiefpassfilter')

# Eingabewerte
fs = 500.0  # Abtastrate (Hz)
nyquist = fs / 2  # Nyquist-Frequenz
cutoff = st.slider("Grenzfrequenz des Tiefpassfilters (Hz)", min_value=1, max_value=100, value=10)
numtaps = st.slider("Anzahl der Filterkoeffizienten", min_value=5, max_value=100, value=29)

# Zeitvektor
t = np.arange(0, 1.0, 1.0/fs)

# Signal erzeugen: Sinuswelle + Rauschen
f_sin = 5  # Frequenz der Sinuswelle (Hz)
noise_level = st.slider("Rauschstärke", min_value=0.0, max_value=1.0, value=0.5)
x = np.sin(2 * np.pi * f_sin * t) + np.random.normal(0, noise_level, t.shape)

# Filterdesign: FIR-Tiefpassfilter
b = firwin(numtaps, cutoff/nyquist)

# Anwenden des Filters auf das Signal
y = lfilter(b, 1.0, x)

# Plot der Ergebnisse
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

# Originalsignal
ax1.plot(t, x, label='Original Signal', color='blue')
ax1.set_title('Original Signal (Rauschen + Sinus)')
ax1.set_xlabel('Zeit [s]')
ax1.set_ylabel('Amplitude')
ax1.grid(True)

# Gefiltertes Signal
ax2.plot(t, y, label='Gefiltertes Signal', color='orange')
ax2.set_title('Gefiltertes Signal (Tiefpassfilter angewendet)')
ax2.set_xlabel('Zeit [s]')
ax2.set_ylabel('Amplitude')
ax2.grid(True)

# Layout und Anzeige
plt.tight_layout()
st.pyplot(fig)
