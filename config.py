import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GUILD_ID = int(os.getenv("GUILD_NUM"))

# Quest Channels
DAILY_SUBMISSION_ID = 1465397069047922811  # JSLAY ID: 1465397069047922811
WEEKLY_SUBMISSION_ID = 1465397106520101191 # JSLAY ID: 1465397106520101191
QUEST_CHANNEL_ID = 1465396954711326937 # JSLAY ID: 1465396954711326937

DAILY_XP = 4
WEEKLY_XP = 18
WORDLE_XP = 1

DAILY_QUEST_COOLDOWN = 7
WEEKLY_QUEST_COOLDOWN = 4

OFFICER_ROLE = "Officer"
OFFICER_ROLE_ID = 1465439193261150230 # JSLAY ID: 1465439193261150230
BATTLE_PASS_ROLE_ID = 963918779249737748 # JSLAY ID: 963918779249737748
APPROVE_EMOJI = "✅"

INSTAGRAM = "https://www.instagram.com/uf_jsa/"
LINKTREE = "https://linktr.ee/uf.jsa?utm_source=ig&utm_medium=social&utm_content=link_in_bio"
CALENDAR = "https://calendar.google.com/calendar/u/0?cid=YmViZDVhYTNhYzFiMTEwOTIzZWUyZGM1NTkwZDg4ZjA1NTI2Njk1NDA3YzA0Yjk4YmIxMzU4YWIzZmEwYmYwZkBncm91cC5jYWxlbmRhci5nb29nbGUuY29t"

# --- RANK CONFIGURATION ---
RANK_THRESHOLDS = {
    0: "Newcomer",
    50: "Daiyo's Classmate",
    150: "Daiyo's Friend",
    300: "Daiyo's Pet",
    500: "JSA Regular",
    750: "JSA Otaku",
    1050: "Honorary JSA Board"
}