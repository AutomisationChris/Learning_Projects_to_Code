import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# Set the title of the app
st.title("Birthday Cake Without Candles")

# Function to plot a birthday cake
def plot_cake():
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Draw cake base (circle)
    cake_base = plt.Circle((0.5, 0.5), 0.4, color='brown', ec="black", lw=3)
    ax.add_artist(cake_base)
    
    # Draw cake layers (two layers stacked)
    cake_layer_top = plt.Circle((0.5, 0.6), 0.35, color='peachpuff', ec="black", lw=3)
    ax.add_artist(cake_layer_top)
    
    # Add some frosting (a wavy border)
    frosting_x = np.linspace(0.1, 0.9, 100)
    frosting_y = 0.6 + 0.05 * np.sin(10 * np.pi * frosting_x)  # sin wave for frosting effect
    ax.fill_between(frosting_x, frosting_y, 0.65, color='white', lw=2)
    
    # Remove axes
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Display the cake
    st.pyplot(fig)

# Show the cake
plot_cake()
