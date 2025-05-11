import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import firwin, lfilter

# Signalparameter
fs = 500.0  # Abtastrate (Hz)
nyquist = fs / 2  # Nyquist-Frequenz
t = np.arange(0, 1.0, 1.0/fs)  # Zeitvektor

# Erzeugung eines Signals (Rauschen + Sinuswelle)
f_sin = 5  # Frequenz der Sinuswelle (Hz)
x = np.sin(2 * np.pi * f_sin * t) + np.random.normal(0, 0.5, t.shape)

# Filterdesign: FIR-Tiefpassfilter mit einer Grenzfrequenz von 10 Hz
cutoff = 10.0  # Grenzfrequenz (Hz)
numtaps = 29  # Anzahl der Filterkoeffizienten
b = firwin(numtaps, cutoff/nyquist)

# Anwenden des Filters auf das Signal
y = lfilter(b, 1.0, x)

# Plotten der Ergebnisse
plt.figure(figsize=(10, 6))
plt.subplot(2, 1, 1)
plt.plot(t, x, label='Original Signal')
plt.title('Original Signal (Rauschen + Sinus)')
plt.xlabel('Zeit [s]')
plt.ylabel('Amplitude')
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(t, y, label='Gefiltertes Signal', color='orange')
plt.title('Gefiltertes Signal (Tiefpassfilter angewendet)')
plt.xlabel('Zeit [s]')
plt.ylabel('Amplitude')
plt.grid(True)

plt.tight_layout()
plt.show()
