import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# Set the title of the Streamlit app
st.title("Happy Birthday Cake")

# Function to draw the birthday cake
def draw_birthday_cake():
    # Set up the figure and axis
    fig, ax = plt.subplots(figsize=(6, 6))

    # Draw the cake base (circle)
    cake_base = plt.Circle((0.5, 0.3), 0.4, color='brown', ec="black", lw=3)
    ax.add_artist(cake_base)

    # Draw the top layer of the cake (frosting)
    top_layer = plt.Circle((0.5, 0.5), 0.38, color='peachpuff', ec="black", lw=3)
    ax.add_artist(top_layer)

    # Draw the frosting on top (wavy effect)
    x = np.linspace(0.1, 0.9, 100)
    y = 0.5 + 0.04 * np.sin(10 * np.pi * x)  # Sinusoidal for wavy frosting
    ax.fill_between(x, y, 0.55, color='white', lw=2)

    # Draw candles (colored)
    candle_positions = [-0.1, 0, 0.1]
    candle_colors = ['red', 'green', 'blue']

    for i, pos in enumerate(candle_positions):
        ax.plot([0.5 + pos, 0.5 + pos], [0.55, 0.75], color=candle_colors[i], lw=5)

    # Add the flame on top of each candle (yellow circles)
    for i, pos in enumerate(candle_positions):
        ax.plot(0.5 + pos, 0.75, 'o', color='yellow', markersize=8)

    # Draw sprinkles on top of the cake (colored dots)
    colors = ['red', 'yellow', 'green', 'blue', 'purple']
    for _ in range(30):
        ax.plot(np.random.uniform(0.35, 0.65), np.random.uniform(0.6, 0.7), 'o', color=np.random.choice(colors), markersize=6)

    # Add a plate underneath the cake
    plate = plt.Circle((0.5, 0.2), 0.5, color='lightgray', ec="black", lw=2, fill=False)
    ax.add_artist(plate)

    # Set axis limits and aspect ratio
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Return the figure object
    return fig

# Draw and display the cake in Streamlit
fig = draw_birthday_cake()
st.pyplot(fig)
