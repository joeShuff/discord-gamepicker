<div style="position: relative; text-align: center;">
  <img src="/art/cropped_banner.png" alt="Banner" style="width: 100%; display: block;" />
  <img src="/art/icon.png" alt="Icon" style="position: absolute; top: 60%; left: 50%; transform: translate(-50%, -50%); width: 150px;" />
</div>

# Wheel of Games Bot 🎉🎮

## Description
Welcome to the "Wheel of Games" Bot! This bot helps you randomly choose games to play with your friends. The bot spins a virtual wheel and selects a game based on the number of players and a variety of other factors, ensuring a fun and fair game selection experience.

## Features
- Choose a game randomly based on player count.
- Skip or reject games with ease.
- Schedule events for the selected game.
- Mark game sessions as ignored for future selection.

## Commands & Parameters 📋

### `/choosegame`
Choose a game to play!

#### Parameters:
- `player_count`: **Required** – The number of players needed for the game. (e.g., 2, 4, 8)
- `ignore_least_played`: **Optional** – A boolean flag to choose games other than the least played games. (default: `False`)
- `event_day`: **Optional** - Override the day the gaming session will be scheduled for. By default it does *next wednesday*. Formatted dd/MMM (e.g. 13/Sep)
- `force_game`: **Optional** - Force a game to be chosen. Helpful if something goes wrong and you want to spin again. Or for rigging if you decided outside of the wheel and need to add a record that the game was chosen.

#### Functionality
1. The bot will spin a wheel with eligible games based on the player count.
2. You will be asked to confirm the selected game.
3. If the game isn't suitable, you can choose another by rejecting the current selection.
4. Once confirmed, an event will be scheduled for the game.

### `/availabilitypoll`
This command send a Poll in the channel for people to vote on their availability to game on a specific date.

This will create a poll that ends 1 week before the game date (or on the game date if 1 week before is in the past)

The max duration that a Poll can be is 31 days. So if you schedule further than that, the poll will end early.

#### Parameters:
- `event_day`: **Required** The day that the gaming session will happen. Format dd/MMM (e.g 13/Sep)

### `/wipegamememory`
Mark a game log as ignored. This means that this play record won't count toward "times played" for a game.

Games are (by default) selected by their least played count.

#### Parameters:
- `game_name`: **Required** – The name of the game to mark as ignored.
- `memory_date`: **Optional** – The specific date to mark as ignored (formatted as `YYYY-MM-DD`). If None provided, all records are marked as ignored for the specified game.

### `/listgames`
List all available games and their details.

#### Parameters:
- `player_count` **Optional** - The number of players to list games that support that count.

#### Output:
- Displays a list of games, their last played date, the number of times played.

---

## Installation to Run it

### Docker Run

```
docker run -d \
  --name wheel-of-games-bot \
  -e DISCORD_TOKEN="your-bot-token" \
  -v /path/to/your/config/folder:/app/config \
  denizenn:wheel-of-games-bot:latest
```

Replace "your-bot-token" with your actual Discord bot token. This will run the bot as a detached container named wheel-of-games-bot with the specified bot token passed as an environment variable.

Replace "path/to/your/config/folder" with the location you'd like the bot to store its database.

## Local Setup & Installation ⚙️  

### Prerequisites  
- Python 3.9+  
- Docker (if deploying in a container)  
- A Discord bot token  

### Local Setup  
1. Clone the repository:  
   <code>
   git clone https://github.com/your-repo/wheel-of-games-bot.git  
   cd wheel-of-games-bot
   </code>  
2. Install dependencies:  
   <code>
   pip install -r requirements.txt
   </code>  
3. Create a `.env` file:  
   <code>
   DISCORD_TOKEN=your_discord_bot_token
   </code>  
4. Run the bot:  
   <code>
   python bot.py
   </code>  

### Docker Deployment  
1. Build the Docker image:  
   <code>
   docker build -t wheel-of-games-bot .  
   </code>  
2. Run the container:  
   <code>
   docker run -e DISCORD_TOKEN=your_discord_bot_token wheel-of-games-bot  
   </code>  

---

## Contributing 🤝

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -am 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

---

## License 📄

This project is licensed under the AGPL-3.0 License – see the [LICENSE](LICENSE) file for details.

---

## Credits 🏆
- **Creator**: ChatGPT with tweaks by @joeShuff
- **Contributors**: Open for contributions!
