# WordleBot

A Discord bot for tracking and sharing your Wordle stats directly from your server. WordleBot automatically records your game results, displays personal stats, and generates leaderboards so you can compare your performance with friends.

## Features

- **Automatic Wordle Submission:** Submit your Wordle results by simply posting in a designated channel.
- **Personal Stats:** View total games played, win percentage, average score, current and longest streaks.
- **Leaderboards:** Check daily, weekly, monthly, yearly, or global leaderboards to see where you stand.
- **Wordle Lookup:** Easily look up a specific Wordle by its ID or date.
- **Admin Tools:** Set custom command prefixes and designate specific channels for Wordle submissions.
- **Manual Review:** Request a manual review if your submission needs further attention.

## Add WordleBot to Your Server

Click the link below to invite WordleBot to your Discord server:

[Add WordleBot to your server](https://discord.com/oauth2/authorize?client_id=1336936974661058580)

## Commands Overview

- `!stats [@user]`  
  Display your Wordle stats (or mention another user to view theirs).

- `!leaderboard [daily|weekly|monthly|yearly|all time]`  
  Show the server leaderboard for a specific period (defaults to all time).

- `!gleaderboard [daily|weekly|monthly|yearly|all time]`  
  Display the global leaderboard.

- `!lookup <wordle_id|date>`  
  Look up a specific Wordle submission. Use a date (MM/DD/YY) or Wordle ID.

- `!update`  
  Update your Discord username and avatar in the bot’s database.

- **Admin Commands:**
  - `!setprefix <new_prefix>`  
    Set a new command prefix (max 5 characters).
  - `!setchannel`  
    Designate the Wordle submission channel.

For a complete list of commands, use the `!help` command in Discord.
