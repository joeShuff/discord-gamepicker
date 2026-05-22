from wheel_generator_2 import generate_wheel_of_games, calculate_gif_duration

games = ["Minecraft", "Among Us", "Rocket League", "Stardew Valley",
         "Overwatch", "Hades", "Deep Rock Galactic", "It Takes Two"]

winning_index = 3
generate_wheel_of_games(games, winning_index=winning_index, file_name="test_wheel.gif")
duration = calculate_gif_duration("test_wheel.gif")
print(f"Generated test_wheel.gif — winner: '{games[winning_index]}', duration: {duration:.1f}s")

