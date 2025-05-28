import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches

# Set the title of the app
st.title("Realistic Birthday Cake Without Candles")

# Function to draw a more realistic birthday cake
def draw_birthday_cake():
    fig, ax = plt.subplots(figsize=(6, 6))

    # Draw the base (cake body - round and flat)
    cake_base = plt.Circle((0.5, 0.4), 0.4, color='brown', ec="black", lw=3)
    ax.add_artist(cake_base)

    # Draw the frosting layer (a bit rounded at the top)
    cake_top_layer = plt.Circle((0.5, 0.65), 0.38, color='peachpuff', ec="black", lw=3)
    ax.add_artist(cake_top_layer)

    # Add detailed chocolate ganache drip effect with wavy pattern
    x = np.linspace(0.1, 0.9, 100)
    y = 0.65 + 0.05 * np.sin(12 * np.pi * x)  # More frequency for a denser drip effect
    ax.fill_between(x, y, 0.68, color='chocolate', lw=2)

    # Add sugar pearls on the frosting (white dots)
    for _ in range(30):
        ax.plot(np.random.uniform(0.35, 0.65), np.random.uniform(0.7, 0.75), 'o', color='white', markersize=8)

    # Add colorful sprinkles on top of the frosting (random colors)
    np.random.seed(0)
    for _ in range(50):
        ax.plot(np.random.uniform(0.35, 0.65), np.random.uniform(0.75, 0.85), 'o', color=np.random.choice(['red', 'green', 'blue', 'yellow', 'pink']), markersize=6)

    # Draw a subtle plate underneath the cake (slightly larger circle)
    plate = plt.Circle((0.5, 0.25), 0.5, color='lightgray', ec="black", lw=2, fill=False)
    ax.add_artist(plate)

    # Remove axes for a cleaner look
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Display the cake
    st.pyplot(fig)

# Draw and display the cake
draw_birthday_cake()
