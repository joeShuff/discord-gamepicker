import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import io

# Wheel parameters
radius = 5  # Radius of the wheel
center = (0, 0)  # Center of the wheel


# Function to create the wheel with a static triangle needle
def create_wheel(games, slice_size, angle_offset=0):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-radius - 1, radius + 1)
    ax.set_ylim(-radius - 1, radius + 1)

    # Create wheel segments (each representing a game)
    for i, game in enumerate(games):
        start_angle = angle_offset + i * slice_size
        end_angle = start_angle + slice_size

        wedge = patches.Wedge(center=center, r=radius, theta1=start_angle, theta2=end_angle,
                              facecolor=plt.cm.tab10(i % 10), edgecolor='black', lw=2)
        ax.add_patch(wedge)

        # Add text in the middle of each wedge
        angle_mid = (start_angle + end_angle) / 2
        ax.text(radius * 0.6 * np.cos(np.radians(angle_mid)),
                radius * 0.6 * np.sin(np.radians(angle_mid)),
                game, ha='center', va='center', fontsize=12, color='white', weight='bold')

    # Draw the static triangle as the arrow needle
    triangle_length = 0.8  # Size of the triangle
    needle_distance = radius + 0.3  # Distance of the triangle from the wheel

    # Coordinates for the triangle vertices
    triangle_coords = [
        [needle_distance - triangle_length, 0],  # Leftmost point of the triangle
        [needle_distance, -0.3],  # Bottom-right of the triangle
        [needle_distance, 0.3],  # Top-right of the triangle
    ]

    # Create the triangle and add it to the plot
    arrow = patches.Polygon(triangle_coords, closed=True, facecolor='black')
    ax.add_patch(arrow)

    ax.set_aspect('equal', 'box')
    ax.axis('off')  # Turn off the axes for a cleaner look
    return fig, ax


def generate_rotations(start_rotation, complete_rotations, end_rotation):
    """
    Generates the rotation values for a spinning wheel with non-linear acceleration
    and deceleration, ensuring it lands at the specified `end_rotation`.
    """
    # Parameters for acceleration and deceleration
    max_speed = 30  # Maximum speed in degrees per frame
    acceleration_frames = 20  # Number of frames for acceleration
    deceleration_frames = 40  # Number of frames for deceleration (non-linear)

    # Total rotation to achieve
    total_rotation = (complete_rotations * 360) + end_rotation - start_rotation

    # Acceleration phase using a quadratic function for non-linear easing
    acceleration_profile = [
        max_speed * (i / acceleration_frames) ** 2 for i in range(acceleration_frames)
    ]
    degrees_in_acceleration = sum(acceleration_profile)

    # Deceleration phase using a quadratic function for non-linear easing
    deceleration_profile = [
        max_speed * (1 - (i / deceleration_frames) ** 2) for i in range(deceleration_frames)
    ]
    degrees_in_deceleration = sum(deceleration_profile)

    # Calculate the degrees for the constant-speed phase
    degrees_in_constant_speed = total_rotation - (degrees_in_acceleration + degrees_in_deceleration)
    if degrees_in_constant_speed < 0:
        raise ValueError("Total rotation is too small for the given acceleration and deceleration phases.")

    constant_speed_frames = int(degrees_in_constant_speed / max_speed)
    constant_speed_profile = [max_speed] * constant_speed_frames

    # Combine the three phases
    speed_profile = acceleration_profile + constant_speed_profile + deceleration_profile

    # Generate cumulative rotation values
    current_rotation = start_rotation
    frame_rotations = []

    for speed in speed_profile:
        current_rotation += speed
        frame_rotations.append(current_rotation)

    # Adjust the final rotation to ensure it lands on end_rotation
    final_rotation_offset = (start_rotation + total_rotation) - frame_rotations[-1]
    frame_rotations[-1] += final_rotation_offset

    return frame_rotations


def generate_wheel_of_games(games, winning_index, file_name):
    start_angle = int(random.uniform(0, 360))

    # minimum amount of times it will rotate fully
    complete_rotations = int(random.uniform(4, 8))

    slice_size = 360 / len(games)

    # + 1 so it's not stopping right on the line
    winning_min_rotation = (winning_index * slice_size) + 1
    # - 2 so it also doesn't stop right on the line
    winning_max_rotation = winning_min_rotation + slice_size - 2

    winning_rotation = int(random.uniform(winning_min_rotation, winning_max_rotation))

    # Create animation frames
    rotations = generate_rotations(start_angle, complete_rotations, winning_rotation)

    # accelerate in from 1 degree per frame to lets say 30
    # hold speed until 1 rotation left
    # decelerate from 30 degrees per frame to 0 degrees per frame

    print(f"starting rot is {start_angle}")
    print(f"winning min is {winning_min_rotation}")
    print(f"winning max is {winning_max_rotation}")
    print(f"winning rot is {winning_rotation}")

    print(f"rotations are {rotations}")

    images = []
    for angle in rotations:
        fig, ax = create_wheel(games=games, slice_size=slice_size, angle_offset=angle)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        images.append(Image.open(buf))
        plt.close(fig)

    # Save the animation as a GIF
    images[0].save(file_name, save_all=True, append_images=images[1:], duration=100, loop=0)


games = ["Game 1", "Game 2", "Game 3", "Game 4", "Game 5"]
generate_wheel_of_games(games=games, winning_index=2, file_name="wheel_of_games.gif")