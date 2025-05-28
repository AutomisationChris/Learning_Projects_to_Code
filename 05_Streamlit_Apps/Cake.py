import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# Set the title of the app
st.title("Drawn Birthday Cake Without Candles")

# Function to draw the birthday cake
def draw_birthday_cake():
    fig, ax = plt.subplots(figsize=(6, 6))

    # Draw the base (circle for the cake)
    cake_base = plt.Circle((0.5, 0.5), 0.4, color='brown', ec="black", lw=3)
    ax.add_artist(cake_base)

    # Draw the pink frosting (top layer)
    cake_top_layer = plt.Circle((0.5, 0.6), 0.35, color='peachpuff', ec="black", lw=3)
    ax.add_artist(cake_top_layer)

    # Draw the chocolate ganache drip
    x = np.linspace(0.1, 0.9, 100)
    y = 0.6 + 0.05 * np.sin(10 * np.pi * x)  # Sinusoidal drip effect
    ax.fill_between(x, y, 0.65, color='chocolate', lw=2)

    # Add some colorful sprinkles on top
    np.random.seed(0)
    for _ in range(15):
        ax.plot(np.random.uniform(0.35, 0.65), np.random.uniform(0.8, 1.0), 'o', color=np.random.choice(['red', 'green', 'blue', 'yellow', 'pink']))

    # Remove axes for a cleaner look
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Display the cake
    st.pyplot(fig)

# Draw and display the cake
draw_birthday_cake()
