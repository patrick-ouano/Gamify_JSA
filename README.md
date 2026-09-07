<!-- Badges -->
<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://discordpy.readthedocs.io/"><img src="https://img.shields.io/badge/Discord.py-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord.py" /></a>
  <a href="https://developers.google.com/sheets/api"><img src="https://img.shields.io/badge/Google%20Sheets-34A853?style=for-the-badge&logo=googlesheets&logoColor=white" alt="Google Sheets" /></a>
  <a href="https://gspread.readthedocs.io/"><img src="https://img.shields.io/badge/gspread-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="gspread" /></a>
  <a href="https://www.heroku.com/"><img src="https://img.shields.io/badge/Heroku-430098?style=for-the-badge&logo=heroku&logoColor=white" alt="Heroku" /></a>
</p>

---

<h1 align="center">🏯 Gamify JSA</h1>

<p align="center">
  <strong>Level up your JSA experience.</strong>
</p>

<p align="center">
  A Discord bot that gamifies participation for the UF Japanese Student Association with an XP-based progression system, quests, leaderboards, and more.
</p>

<!-- TODO: Add screenshot or demo GIF here -->
<!-- <p align="center">
  <img src="./demo.gif" alt="Gamify JSA Demo" width="600" />
</p> -->

---

## Overview

**Gamify JSA** transforms club participation into an engaging RPG-like experience. Members earn XP by attending events, completing daily and weekly quests, and even playing Wordle. As they accumulate XP, they progress through ranks — from humble **Newcomer** all the way to **Honorary JSA Board**.

Officers can easily process event attendance through Google Sheets integration, and the bot automatically awards XP and updates member ranks. The quest system keeps members engaged between events with fun challenges verified by the officer team.

Google Sheets is the source of truth (no separate database). The bot runs as a long-lived **Heroku worker** dyno.

---

## How It Works

1. **Join the System** — Members use `/join` with their email to link their Discord account to the XP roster.
2. **Attend Events** — Officers process attendance sheets, and XP is automatically awarded to all attendees.
3. **Complete Quests** — Daily and weekly quests are posted automatically. Submit proof and get officer approval for XP.
4. **Play Wordle** — Paste your Wordle results with `/claim_wordle` to earn bonus XP.
5. **Climb the Ranks** — Check your progress with `/xp` and compete on the `/leaderboard`.

---

## Rank Progression

<p align="center">

| XP Required | Rank |
|:-----------:|:-----|
| 0 | 🌱 Newcomer |
| 50 | 📚 Daiyo's Classmate |
| 150 | 🤝 Daiyo's Friend |
| 300 | 🐕 Daiyo's Pet |
| 500 | ⭐ JSA Regular |
| 750 | 🎌 JSA Otaku |
| 1050 | 👑 Honorary JSA Board |

</p>

---

## Key Features

- **XP & Rank System** — Earn XP from events, quests, and Wordle. Automatically rank up as you progress.
- **Event Processing** — Officers paste a Google Sheets attendance URL and XP is awarded to all attendees instantly.
- **Daily & Weekly Quests** — Posted on a schedule (daily at 8:00 AM Eastern; weekly on Mondays). Officer-verified submissions via ✅.
- **Quest Cooldowns** — Recent quests are deprioritized so the same quest doesn’t spam the channel.
- **Wordle Integration** — Claim XP daily by sharing your Wordle results.
- **Dual Leaderboards** — Separate rankings for regular members and board members.
- **Auto-Enrollment** — New event attendees are automatically added to the roster.
- **Duplicate Protection** — Prevents double-processing of events and double-claiming of Wordle puzzles.

---

## Tech Stack

### Bot Framework
- **Python 3.12+** (local may differ; Heroku uses `runtime.txt`)
- **Discord.py** — Discord API wrapper with slash commands
- **python-dotenv** — Local environment variable management

### Data Storage
- **Google Sheets API** — Cloud-based data storage for rosters, quests, and logs
- **gspread** — Python client for Google Sheets
- **google-auth** — Service account authentication (`credentials.json` locally, or `GOOGLE_CREDS` on Heroku)

### Deployment
- **Heroku** — Hosting via a **worker** dyno (`Procfile`: `worker: python bot.py`)
- **Heroku Config Vars** — Secrets and IDs (no committed `.env` / `credentials.json` on the server)

---

## Getting Started

### Prerequisites

- Python 3.8+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Google Cloud Service Account with Sheets API enabled
- Google Sheet set up with required worksheets
- (For deploy) [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and a Heroku account

### Installation (local)

1. Clone the repository:

   ```bash
   git clone https://github.com/patrick-ouano/Gamify_JSA.git
   cd Gamify_JSA
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:

   Create a `.env` file in the root directory:

   ```env
   DISCORD_TOKEN=your_discord_bot_token
   GOOGLE_SHEET_ID=your_google_sheet_id
   GUILD_NUM=your_discord_server_id
   ```

5. Add your Google Cloud service account credentials as `credentials.json` in the root directory.

   Locally, `sheets/client.py` loads this file. On Heroku, set the same JSON as the `GOOGLE_CREDS` config var instead (see Deployment).

6. Update channel and role IDs in `config.py` for the Discord server you’re using (test or production).

7. Set up your Google Sheet with these worksheets:

   | Worksheet | Purpose |
   |-----------|---------|
   | `Master_Roster` | Member data (Name, Email, Year, Discord_ID, Total_XP, Rank, Board_Member) |
   | `Attendance_Logs` | Tracks processed event sheets (Event_ID, Timestamp, XP_Amount) |
   | `Audit_Logs` | Quest approvals and manual XP (Message_ID, Timestamp, Officer_ID, Recipient_ID, XP_Amount, Reason) |
   | `Daily_Quests` | Quest Name, Description, Objective, Verification Method, Last_Used |
   | `Weekly_Quests` | Same structure as Daily_Quests |
   | `Wordle_Claims` | Puzzle number, Discord_ID, Timestamp — prevents double claims |
   | `Board_Roster` | List of board member emails (used by `sync_board_members`) |

8. Share the sheet with the service account `client_email` as **Editor**.

9. Run the bot:

   ```bash
   python bot.py
   ```

**Note:** `.env` and `credentials.json` are gitignored. Save them to disk before running — an unsaved editor buffer will look filled in but the bot will still see an empty file.

---

## Commands

### Member Commands

| Command | Description |
|---------|-------------|
| `/join <email>` | Register your Discord account with the JSA XP system |
| `/xp` | Check your current XP and rank |
| `/leaderboard [type] [top]` | View the leaderboard (regular, board, or all members) |
| `/claim_wordle <share_text>` | Claim XP for completing Wordle (paste share text) |
| `/socials` | Get links to JSA social media (Instagram, Linktree, Calendar) |
| `/shota` | Learn about JSA's founder |
| `/help` | Show help info and list commands (officers see extra officer commands) |

### Officer Commands

| Command | Description |
|---------|-------------|
| `/process_event <sheet_url> <xp_amount>` | Process an attendance sheet and award XP to attendees |
| `/test_quest <type>` | Post a test quest announcement to the quest channel |
| `/refresh_quest <type>` | Force a new daily or weekly quest announcement |
| `/post_specific_quest <type> <name>` | Post a specific quest by exact name from the sheet |
| `/award_xp <user> <xp_amount> <reason>` | Manually grant XP to a user (logged to Audit_Logs) |
| `/sync_board_members` | Sync Board_Member column from Board_Roster |
| `/grant_access_all` | Grant Battle Pass role to all current members (one-time use) |

---

## Project Structure

```
Gamify_JSA/
├── bot.py                # Main Discord bot: commands, quest loops, reaction handlers
├── config.py             # Configuration and environment variables
├── requirements.txt      # Python dependencies
├── Procfile              # Heroku process type (worker)
├── runtime.txt           # Heroku Python version
├── credentials.json      # Google Cloud service account (not in repo; local only)
├── .env                  # Environment variables (not in repo; local only)
├── sheets/
│   ├── client.py         # Google Sheets auth (GOOGLE_CREDS or credentials.json)
│   └── actions.py        # Sheet operations (see below)
└── wordle/
    └── wordle_actions.py # Wordle share text parsing
```

### Sheet operations (`sheets/actions.py`)

| Function | Purpose |
|----------|---------|
| `calculate_rank`, `get_next_rank_info`, `generate_progress_bar` | Rank and XP progress display |
| `get_id_from_url`, `find_email_column`, `find_name_column` | Event sheet parsing |
| `is_event_processed`, `log_event_completion` | Event processing idempotency |
| `is_quest_processed`, `log_quest_approval`, `is_manual_xp_given` | Audit and duplicate prevention |
| `process_event_data` | Process attendance sheet, award XP, auto-enroll new attendees |
| `get_join`, `get_leaderboard`, `get_xp` | Member lookup and display |
| `award_quest_xp`, `grant_manual_xp` | Award XP (quest approval and manual) |
| `get_random_quest`, `get_specific_quest` | Quest selection from Daily_Quests / Weekly_Quests |
| `wordle_claim_exists`, `log_wordle_claim` | Wordle claim tracking |
| `check_if_board_member` | Sync Board_Member from Board_Roster |

---

## Configuration

### Environment variables

| Variable | Where | Description |
|----------|--------|-------------|
| `DISCORD_TOKEN` | `.env` / Heroku | Discord bot token |
| `GOOGLE_SHEET_ID` | `.env` / Heroku | Master spreadsheet ID |
| `GUILD_NUM` | `.env` / Heroku | Discord server (guild) ID |
| `GOOGLE_CREDS` | Heroku only | Full service-account JSON as a string (used instead of `credentials.json`) |

### `config.py` settings

| Setting | Description |
|---------|-------------|
| `DAILY_XP` / `WEEKLY_XP` / `WORDLE_XP` | XP rewards for different activities |
| `DAILY_QUEST_COOLDOWN` / `WEEKLY_QUEST_COOLDOWN` | How many recently used quests to avoid when picking the next one |
| `QUEST_CHANNEL_ID` | Channel for quest announcements |
| `DAILY_SUBMISSION_ID` / `WEEKLY_SUBMISSION_ID` | Channels for quest submissions |
| `OFFICER_ROLE` / `OFFICER_ROLE_ID` | Role required for admin commands |
| `BATTLE_PASS_ROLE_ID` | Role granted for Battle Pass channel access |
| `APPROVE_EMOJI` | Emoji used to approve quest submissions (default: ✅) |
| `RANK_THRESHOLDS` | XP required for each rank |

Channel and role IDs must match the Discord server you deploy against (test vs production).

---

## Deployment (Heroku)

The bot is hosted on **Heroku** as a **worker** dyno (not `web`). Discord bots need an always-on process; use a Basic (or similar) worker so the dyno does not sleep.

### Deploy files

- `Procfile` → `worker: python bot.py`
- `runtime.txt` → pinned Python version for builds

### One-time setup

```bash
# From the project root (Heroku CLI installed, heroku login done)
heroku create your-app-name

heroku config:set DISCORD_TOKEN="your_token"
heroku config:set GOOGLE_SHEET_ID="your_sheet_id"
heroku config:set GUILD_NUM="your_guild_id"
heroku config:set GOOGLE_CREDS="$(cat credentials.json)"

git push heroku main

heroku ps:scale worker=1
heroku ps
```

If your default branch is not `main`, push with `git push heroku master:main` (or your branch name).

There is no `web` process in this app. Scale only the worker:

```bash
heroku ps:scale worker=1
```

### Useful commands

| Command | Description |
|---------|-------------|
| `heroku ps` | Show dyno status (worker should be `up`) |
| `heroku logs --tail` | Live logs |
| `heroku restart` | Restart the worker |
| `heroku config` | List config vars (secrets redacted in UI; values show in CLI) |
| `heroku ps:scale worker=0` | Stop the bot |

### Updating the bot

```bash
git push heroku main
# Heroku rebuilds and restarts the worker after a successful deploy
```

### Switching from a test server to production

1. Update channel/role IDs in `config.py` (and `ACCESS_MESSAGE_ID` in `bot.py` if used).
2. Set production config vars (`DISCORD_TOKEN`, `GOOGLE_SHEET_ID`, `GUILD_NUM`, and `GOOGLE_CREDS` if needed).
3. `git push heroku main`.
4. Confirm with `heroku logs --tail` and a Discord smoke test.

Only run **one** instance of the same bot token at a time (don’t leave a local or old host running the production token).

---

## Credits

- **[Discord.py](https://discordpy.readthedocs.io/)** — Discord API wrapper
- **[gspread](https://gspread.readthedocs.io/)** — Google Sheets Python client
- **[Heroku](https://www.heroku.com/)** — Cloud hosting
- **Cursor** — AI-powered IDE

---

## Future Roadmap

### Features
- [ ] Quest streak tracking with bonus XP
- [ ] `/profile` command with detailed stats
- [ ] Celebratory message for ranking up
- [ ] GitHub Actions for automated deployment

### Things to improve
- [ ] **Unit tests** — Add pytest tests for `sheets/actions.py` (rank/progress helpers, `get_id_from_url`, quest selection with mocks) and optionally CI (e.g. GitHub Actions) to run them.

---

<p align="center">
  Made with ❤️ for the UF Japanese Student Association
</p>
