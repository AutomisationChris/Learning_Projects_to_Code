import streamlit as st
import cantera as ct
import matplotlib.pyplot as plt

def calculate_thermo_properties(temperature, pressure):
    gas = ct.Solution('gri30.yaml')
    gas.TPX = temperature, pressure * ct.one_atm, 'CH4:1, O2:2'
    enthalpy = gas.enthalpy_mass
    entropy = gas.entropy_mass
    return enthalpy, entropy

# Streamlit widgets
st.title('Cantera Thermodynamic Calculator')

temperature = st.slider('Select Temperature (K)', 300, 3000, 1500)
pressure = st.slider('Select Pressure (atm)', 1, 100, 1)

# Run the calculation when the user clicks the button
if st.button('Calculate Thermo Properties'):
    enthalpy, entropy = calculate_thermo_properties(temperature, pressure)
    st.write(f'Enthalpy: {enthalpy} J/kg')
    st.write(f'Entropy: {entropy} J/kg.K')

    # Plot results
    time = [0, 1, 2, 3, 4]
    temperature_data = [300, 400, 500, 600, 700]
    fig, ax = plt.subplots()
    ax.plot(time, temperature_data, label='Temperature vs Time')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Temperature (K)')
    ax.legend()

    st.pyplot(fig)
