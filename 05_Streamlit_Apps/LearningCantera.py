import cantera as ct
import numpy as np
import streamlit as st

gas1 = ct.Solution('gri30.yaml')
gas1()


# Streamlit Interface
st.title('Cantera Gas Simulation in Streamlit')

st.write(gas1())
st.write("Cantera Output:")
st.write(gas1)
