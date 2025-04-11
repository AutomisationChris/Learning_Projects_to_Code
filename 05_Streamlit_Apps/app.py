import streamlit as st

st.title("Welcome to Learning Projects to Code")
st.header("Live Dashboard")
st.write("This is your Streamlit app setup. Here, you will display data, visualizations, and insights from your projects.")

# Beispiel: Ein einfacher Temperatur-Diagramm-Platzhalter (wird später ersetzt)
import pandas as pd
import matplotlib.pyplot as plt

# Dummy-Daten generieren
data = {'Date': pd.date_range(start='2024-01-01', periods=7, freq='D'),
        'Temperature': [10, 12, 11, 13, 12, 14, 13]}
df = pd.DataFrame(data)

st.subheader("Example Temperature Chart")
fig, ax = plt.subplots()
ax.plot(df['Date'], df['Temperature'], marker='o', color="tab:orange")
ax.set_xlabel("Date")
ax.set_ylabel("Temperature (°C)")
ax.grid(True)
st.pyplot(fig)
