import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import io

import logging
logger = logging.getLogger(__name__)

# Wheel parameters
radius = 5  # Radius of the wheel
center = (0, 0)  # Center of the wheel


def calculate_gif_duration(file_name):
    """
    Calculate the total duration of a GIF by summing up the durations of all frames.
    """
    with Image.open(file_name) as gif:
        return sum(frame.info.get("duration", 0) for frame in iter_frames(gif)) / 1000  # Convert ms to seconds


def iter_frames(image):
    """
    Generator to iterate through all frames of a GIF.
    """
    try:
        while True:
            yield image.copy()
            image.seek(image.tell() + 1)
    except EOFError:
        pass


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

        # Add text along the radius, flipped to read outward
        angle_mid = (start_angle + end_angle) / 2  # Middle angle of the slice
        text_radius = radius - 0.5  # Place the text slightly inward from the circumference

        # Add text along the radius, flipped to read outward
        angle_mid = (start_angle + end_angle) / 2  # Middle angle of the slice
        text_radius = radius * 0.6  # Adjust text position closer to the center

        # Calculate text position
        x_pos = text_radius * np.cos(np.radians(angle_mid))
        y_pos = text_radius * np.sin(np.radians(angle_mid))

        # Determine the correct rotation angle for outward-facing text
        if 90 < angle_mid <= 270:
            rotation = angle_mid + 180  # Flip text outward
        else:
            rotation = angle_mid

        ax.text(x_pos, y_pos, game, ha='center', va='center', fontsize=10, color='white',
                weight='bold', rotation_mode='anchor', rotation=rotation)  # Rotate text outward

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
    and deceleration, ensuring it lands at the specified `end_rotation` smoothly,
    and rotates clockwise.
    """
    # Parameters for acceleration and deceleration
    max_speed = 30  # Maximum speed in degrees per frame
    acceleration_frames = 20  # Number of frames for acceleration
    deceleration_frames = 80  # Number of frames for deceleration

    # Total rotation to achieve (negative for clockwise)
    total_rotation = (complete_rotations * 360) + (360 - end_rotation) + start_rotation

    # Acceleration phase using a quadratic function for non-linear easing
    acceleration_profile = [
        round(max_speed * (i / acceleration_frames) ** 2) for i in range(acceleration_frames)
    ]
    degrees_in_acceleration = sum(acceleration_profile)

    # Deceleration phase using a quadratic function for non-linear easing
    deceleration_profile = [
        round(max_speed * (1 - (i / deceleration_frames) ** 2)) for i in range(deceleration_frames)
    ]
    degrees_in_deceleration = sum(deceleration_profile)

    # Calculate the degrees for the constant-speed phase
    degrees_left = total_rotation - (degrees_in_acceleration + degrees_in_deceleration)
    if degrees_left < 0:
        logger.debug("Total rotation is too small for the given acceleration and deceleration phases.")
        return generate_rotations(start_rotation, complete_rotations + 2, end_rotation)

    constant_speed_frames = int(degrees_left / max_speed)
    degrees_in_constant_speed = constant_speed_frames * max_speed
    constant_speed_profile = [max_speed] * constant_speed_frames

    # Combine the three phases
    speed_profile = acceleration_profile + constant_speed_profile + deceleration_profile

    # Generate cumulative rotation values (subtracting speeds for clockwise rotation)
    frame_rotations = []
    current_rotation = start_rotation

    for speed in speed_profile:
        current_rotation -= speed  # Subtract for clockwise rotation
        frame_rotations.append(current_rotation)

    # Smooth correction over the deceleration phase
    correction_needed = total_rotation - degrees_in_deceleration - degrees_in_acceleration - degrees_in_constant_speed
    deceleration_start_index = len(frame_rotations) - len(deceleration_profile)

    for i in range(len(deceleration_profile)):
        # Gradually distribute the correction across the deceleration phase
        adjustment_ratio = (i + 1) / len(deceleration_profile)
        frame_rotations[deceleration_start_index + i] -= correction_needed * adjustment_ratio

    return frame_rotations


def generate_wheel_of_games(games, winning_index, file_name):
    start_angle = int(random.uniform(0, 360))

    # minimum amount of times it will rotate fully
    complete_rotations = int(random.uniform(4, 8))

    slice_size = 360 / len(games)

    # + 1 so it's not stopping right on the line
    winning_max_rotation = 360 - ((winning_index * slice_size) + 1)
    # - 2 so it also doesn't stop right on the line
    winning_min_rotation = winning_max_rotation - slice_size

    winning_rotation = int(random.uniform(winning_min_rotation, winning_max_rotation))

    # Create animation frames
    rotations = generate_rotations(start_angle, complete_rotations, winning_rotation)

    # accelerate in from 1 degree per frame to 30
    # hold speed until 1 rotation left
    # decelerate from 30 degrees per frame to 0 degrees per frame

    logger.debug(f"starting rot is {start_angle}")
    logger.debug(f"total rotations is {complete_rotations}")
    logger.debug(f"winning min is {winning_min_rotation}")
    logger.debug(f"winning max is {winning_max_rotation}")
    logger.debug(f"winning rot is {winning_rotation}")

    logger.debug(f"rotations are {rotations}")

    images = []
    for angle in rotations:
        fig, ax = create_wheel(games=games, slice_size=slice_size, angle_offset=angle)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        images.append(Image.open(buf))
        plt.close(fig)

    # Duplicate the last frame for 20 more frames
    for _ in range(20):
        images.append(images[-1])

    # Save the animation as a GIF
    images[0].save(file_name, save_all=True, append_images=images[1:], duration=100, loop=0)