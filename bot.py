import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
import logging
import config 
from sheets.client import get_client
from sheets import actions
from wordle import wordle_actions
import datetime
from zoneinfo import ZoneInfo

# 1. Setup Intents 
intents = discord.Intents.default()
intents.message_content = True # Allows bot to read commands

# 2. Startup Event
class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print('Bot is ready to process sheets!')
        
        # Start the quest loops
        if not daily_quest_loop.is_running():
            daily_quest_loop.start()
            print("Daily quest loop started.")
        if not update_master_cache.is_running():
            update_master_cache.start()
        try:
            # Syncing commands to the specific guild for instant updates
            guild = discord.Object(id=config.GUILD_ID) 
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {config.GUILD_ID}")
        except Exception as e:
            print(f"Errors syncing commands: {e}")

bot = Client(command_prefix="!", intents=intents)
GUILD_ID = discord.Object(id = config.GUILD_ID)
# 3. Commands:

# Processing Events
@bot.tree.command(name="process_event", description="Adds attendance sheet url for certain event (only officers)", guild=GUILD_ID)
@app_commands.default_permissions()
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def process_event(interaction: discord.Interaction, sheet_url: str, xp_amount: int):

    await interaction.response.send_message(f"🔄 Processing event sheet... this might take a moment.")

    # Get the google sheet client
    client = get_client()

    # Run the logic from actions.py using SHEET_ID from config.py
    result_message = actions.process_event_data(
        client = client,
        master_sheet_id = config.SHEET_ID,
        event_sheet_url = sheet_url,
        xp_amount = xp_amount
    )

    await interaction.followup.send(result_message)

# Join
@bot.tree.command(name="join", description="Joins the JSA Battle Pass!", guild=GUILD_ID)
async def join(interaction: discord.Interaction, email: str):

    client = get_client()

    result = actions.get_join(
        client,
        config.SHEET_ID,
        email,
        str(interaction.user.id),
        interaction.user.display_name,
    )

    await interaction.response.send_message(result)

# Leaderboard
@bot.tree.command(name="leaderboard", description="Prints out the leaderboard", guild=GUILD_ID)
@app_commands.describe(type="Choose between Regular or Board members")
@app_commands.choices(type=[
    app_commands.Choice(name="Regular Members", value="regular"),
    app_commands.Choice(name="Board Members", value="board"),
    app_commands.Choice(name="All Members", value = "all")
])
async def leaderboard(interaction: discord.Interaction, type: str = "regular", top: int = 10):
    await interaction.response.defer()

    client = get_client()

    result = actions.get_leaderboard(client, config.SHEET_ID, top, mode=type)
    place = 0
    shown = 0
    leaderboardentries = ""
    lastxp = -1
    s = "\u3164"
    def makeentry(name,xp,rank_name,isboard,place,type):
        placement_text = ""
        nametext = name
        if(type == "all" and isboard == True):
            nametext = "**[Board]** " + nametext
        #placement_text += f"{name} — {xp} ({rank_name})\n"
        medal = "🥇" if place == 1 else "🥈" if place == 2 else "🥉" if place == 3 else "⭐"
        suffix = "st" if place == 1 else "nd" if place == 2 else "rd" if place == 3 else ")"

        if place <= 3:
            placement_text += f"{s*6} {medal} {place}{suffix} | {nametext}\n"
            placement_text += f"{s*8} ★ {xp} XP ★\n"
            placement_text += f"{s*6} {rank_name} (ง•̀o•́)ง \n\n"
        else:
            placement_text += f"{s*2} {medal} {place}) {nametext} ★ {xp} XP ★\n"
        return placement_text
    def checkNextIndexes(currentxp, currentstring, currentindex,maxindex,place):
            recursiveentry = result[currentindex]
            recursivename = recursiveentry[0]
            recursivexp = recursiveentry[1]
            recursiverank = recursiveentry[2]
            recursiveboard = recursiveentry[3]
            newstring = makeentry(recursivename,recursivexp,recursiverank,recursiveboard,place,type)

            #96 free characters to not hit the limit might be excessive but needing 4000 characters in the first place is excessive
            if(len(currentstring+newstring)>4000):
                recursivenextentry = result[currentindex+1]
                recursivenextxp = recursivenextentry[1]
                if(recursivenextxp == recursivexp):
                    return f"\n{s*3} ... and more tied with {xp} XP ...\n"
                else:
                    return ""
            if(currentindex == maxindex):
                return newstring
            if(currentxp != recursivexp):
                return ""
            return newstring + checkNextIndexes(recursivexp,currentstring+newstring,currentindex+1,maxindex,place)
    for index, (name, xp, rank_name,is_board) in enumerate(result):
        if xp != lastxp:
            place = index + 1
            lastxp = xp
        entry = result[index]
        name = entry[0]
        xp = entry[1]
        rank = entry[2]
        isboard = entry[3]

        thismessage = makeentry(name,xp,rank,isboard,place,type)
        #this is an immediate check to see if we've somehow already hit that limit without going into tie strings which might somehow potentially be a problem later on if someone searches for like top 100
        if(len(leaderboardentries+thismessage)>4000):
            break
        #this is the recursive check to see how many we can do next after we've already hit a huge string of ties
        if shown >= top:
            leaderboardentries += checkNextIndexes(xp,leaderboardentries+thismessage,index,len(result),place)
            break
        leaderboardentries += thismessage
        shown +=1
    leaderboardentries += f"\n**╰━━━━━━ {s*7} 🏯 {s*7} ━━━━━━╯**"
    leaderboard_embed = discord.Embed(title=f"╭━━━ {s*2} ⚔️ **JSA LEADERBOARD** ⚔️ {s*2} ━━━╮\n\n",description=leaderboardentries)
    await interaction.followup.send(embed=leaderboard_embed)

# XP
@bot.tree.command(name="xp", description="Prints out your total XP!", guild=GUILD_ID)
async def xp(interaction: discord.Interaction):

    client = get_client()

    result = actions.get_xp(client, config.SHEET_ID, str(interaction.user.id))

    await interaction.response.send_message(result)

# Quests
# Helper function to format the Quest into a nice Discord Embed
def format_quest_embed(quest, category_name):
    is_weekly = category_name == "Weekly_Quests"
    xp = config.WEEKLY_XP if is_weekly else config.DAILY_XP

    embed = discord.Embed(
        title=f"🏯 {quest['Quest Name']}",
        description=quest['Description'],
        color=discord.Color.gold() if is_weekly else discord.Color.blue()
    )
    embed.add_field(name="⚔️ Objective", value=quest['Objective'], inline=False)
    embed.add_field(name="📜 Verification", value=quest['Verification Method'], inline=False)
    embed.add_field(name="✨ Reward", value=f"{xp} XP", inline=True)
    embed.set_footer(text=f"Frequency: {'Weekly' if is_weekly else 'Daily'}")
    return embed

# Task for Daily Quests (Runs every 24 hours)
@tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=ZoneInfo('America/New_York')))
async def daily_quest_loop():
    channel = bot.get_channel(config.QUEST_CHANNEL_ID)
    if channel:
        client = get_client()
        quest = actions.get_random_quest(client, config.SHEET_ID, "Daily_Quests")
        if quest:
            await channel.send("☀️ **Today's Daily Quest is live!**", embed=format_quest_embed(quest, "Daily_Quests"))
        #after the daily we check weekly
        day_of_week = datetime.datetime.weekday(datetime.date.today())
        #days are 0(monday)-6(sunday)
        if(day_of_week == 0):
            quest = actions.get_random_quest(client, config.SHEET_ID, "Weekly_Quests")
            if quest:
                await channel.send("🔥 **A new Weekly Quest has appeared!**", embed=format_quest_embed(quest, "Weekly_Quests"))
#Task for updating master cache (Runs every 5 mins)
@tasks.loop(minutes=5)
async def update_master_cache():
    client = get_client()
    actions.update_master_cache(client,config.SHEET_ID)

# The /test_quest command
@bot.tree.command(name="test_quest", description="Test a quest announcement", guild=GUILD_ID)
@app_commands.describe(type="Choose Daily or Weekly")
@app_commands.choices(type=[
    app_commands.Choice(name="Daily", value="Daily_Quests"),
    app_commands.Choice(name="Weekly", value="Weekly_Quests")
])
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def test_quest(interaction: discord.Interaction, type: str):
    await interaction.response.defer(ephemeral=True)
    client = get_client()
    quest = actions.get_random_quest(client, config.SHEET_ID, type) #

    if quest:
        embed = format_quest_embed(quest, type)
        channel = bot.get_channel(config.QUEST_CHANNEL_ID)
        if channel:
            await channel.send(content=f"🧪 **Test Announcement:**", embed=embed)
            await interaction.followup.send(f"✅ Posted to <#{config.QUEST_CHANNEL_ID}>")
        else:
            await interaction.followup.send("❌ Channel not found.")
    else:
        await interaction.followup.send("❌ Could not fetch quest.")

# The /refresh_quest command
@bot.tree.command(name="refresh_quest", description="Force a new quest announcement", guild=GUILD_ID)
@app_commands.describe(type="Choose Daily or Weekly")
@app_commands.choices(type=[
    app_commands.Choice(name="Daily", value="Daily_Quests"),
    app_commands.Choice(name="Weekly", value="Weekly_Quests")
])
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def refresh_quest(interaction: discord.Interaction, type: str):
    await interaction.response.defer(ephemeral=True)
    client = get_client()
    quest = actions.get_random_quest(client, config.SHEET_ID, type) #

    if quest:
        channel = bot.get_channel(config.QUEST_CHANNEL_ID)
        if channel:
            # Matches the exact wording from the automatic loops
            announcement_text = "☀️ **Today's Daily Quest is live!**" if type == "Daily_Quests" else "🔥 **A new Weekly Quest has appeared!**"
            embed = format_quest_embed(quest, type)
            await channel.send(content=announcement_text, embed=embed)
            await interaction.followup.send(f"✅ Refreshed {type}!")

# The /post_specific_quest
@bot.tree.command(name="post_specific_quest", description="Manually select and post a specific quest", guild=GUILD_ID)
@app_commands.describe(type="Choose Daily or Weekly", name="Exactly match the Quest Name from the sheet")
@app_commands.choices(type=[
    app_commands.Choice(name="Daily", value="Daily_Quests"),
    app_commands.Choice(name="Weekly", value="Weekly_Quests")
])
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def post_specific_quest(interaction: discord.Interaction, type: str, name: str):
    await interaction.response.defer(ephemeral=True)

    client = get_client()
    quest = actions.get_specific_quest(client, config.SHEET_ID, type, name)

    if quest:
        channel = bot.get_channel(config.QUEST_CHANNEL_ID)
        if channel:
            # Matches the exact wording from the automatic loops
            announcement_text = "☀️ **Today's Daily Quest is live!**" if type == "Daily_Quests" else "🔥 **A new Weekly Quest has appeared!**"

            embed = format_quest_embed(quest, type)
            await channel.send(content=announcement_text, embed=embed)
            await interaction.followup.send(f"✅ Successfully posted '{name}' as the official quest.")
        else:
            await interaction.followup.send("❌ Quests channel not found.")
    else:
        await interaction.followup.send(f"❌ Error: Could not find a quest named '{name}' in the {type} sheet.")

# Store the message ID for the access message
ACCESS_MESSAGE_ID = 1465869081210261770 # Replace with your message ID after posting

@bot.event
async def on_raw_reaction_add(payload):
    # Check if it's the access message
    if payload.message_id == ACCESS_MESSAGE_ID and str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        if member and not member.bot:
            role = guild.get_role(config.BATTLE_PASS_ROLE_ID)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                    try:
                        await member.send("🎉 You now have access to the JSA Battle Pass channels!")
                    except:
                        pass  # Can't DM, that's okay
                except Exception as e:
                    print(f"Error assigning role: {e}")
        return

    quest_channels = {
        config.DAILY_SUBMISSION_ID: ("Daily Quest Approval", config.DAILY_XP),
        config.WEEKLY_SUBMISSION_ID: ("Weekly Quest Approval", config.WEEKLY_XP)
    }

    if payload.channel_id not in quest_channels or str(payload.emoji) != config.APPROVE_EMOJI:
        return

    # Gets the member who reacted (the officer)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)

    # Verifies the officer role
    if not any(role.name == config.OFFICER_ROLE for role in member.roles):
        return # If not an officer, ignore reaction

    # Process the Quest
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    if message.author.bot:
        return

    # Get quest type and XP amount
    reason, xp_to_give = quest_channels[payload.channel_id]

    # Awards XP with audit logging (prevents double-dipping)
    client = get_client()
    result = actions.award_quest_xp(
        client=client,
        master_sheet_id=config.SHEET_ID,
        discord_id=str(message.author.id),
        xp_amount=xp_to_give,
        officer_id=str(payload.user_id),
        message_id=str(payload.message_id),
        reason=reason
    )

    # Check if this was a duplicate approval
    if "Already Approved" in result:
        # Silently ignore duplicate approvals (don't spam the channel)
        return

    response_message = (
        f"⚔️ **Quest Accomplished!** 🏯\n"
        f"Hello {message.author.mention}! An officer has verified your submission.\n"
        f"✨ **{result}**"
    )

    await channel.send(response_message)

# Automatically give new members access to JSA Battle Pass
@bot.event
async def on_member_join(member):
    """Automatically give new members access to JSA Battle Pass"""
    if member.bot:
        return

    guild = member.guild
    role = guild.get_role(config.BATTLE_PASS_ROLE_ID)

    if role:
        try:
            await member.add_roles(role)
            print(f"Auto-assigned Battle Pass role to {member.name}")
        except Exception as e:
            print(f"Error auto-assigning role to {member.name}: {e}")

# Handles permission errors
@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRole):
        await interaction.response.send_message("❌ **Access Denied:** You do not have the 'Officer' role required to use this command.", ephemeral=True)
    else:
        # Log other errors to the terminal
        print(f"Error: {error}")

class SocialsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="INSTAGRAM", style = discord.ButtonStyle.blurple, url=config.INSTAGRAM))
        self.add_item(discord.ui.Button(label="LINKTREE", style=discord.ButtonStyle.red, url=config.LINKTREE))
        self.add_item(discord.ui.Button(label="JSA CALENDAR", style=discord.ButtonStyle.green, url=config.CALENDAR))

# Socials
@bot.tree.command(name="socials", description="This is a link to all of JSA's socials", guild=GUILD_ID)
async def socials(interaction: discord.Interaction):
    embed = discord.Embed(
        title = "JSA Socials",
        description="Tap a button to open a link",
    )
    await interaction.response.send_message(embed=embed, view=SocialsView())

# Shota
@bot.tree.command(name="shota", description="This is a dedication to JSA's Founder Shota Konno!", guild=GUILD_ID)
async def shota(interaction: discord.Interaction):
    response_message = "In winter of 2021, Shota Konno (c.o. 2025) founded the UF Japanese Student Association " \
    "along with Taise Miyazumi (c.o. 2024), Annika Joy Cruz (c.o. 2025), and Ellie Uchida-Prebor (c.o. 2025). " \
    "Shota served as president for three years, during which he oversaw JSA's first AASA participation, " \
    "two Undokai events, several banquets, and many other events. His biggest hope is for JSA to grow and continue to " \
    "follow its mission to provide a safe space for anyone and everyone to learn about Japanese culture!"
    await interaction.response.send_message(response_message)
# Help
@bot.tree.command(name="help", description="Shows help info and lists bot commands.", guild=GUILD_ID)
async def help(interaction: discord.Interaction):
    descriptiontext ="JSA Battle Pass is a way for you to earn XP for participating in JSA Events.\n\n"\
                                            "**Getting Started**: Use the `/join` command with your email in <#1465396884624380109>.\n"\
                                            "### Important Commands\n"\
                                            "`/xp`: Use this in <#1465396884624380109> to display your current xp.\n"\
                                            "`/leaderboard`: Use this in <#1465396691636191407> to see the leaderboard of xp for board/regular members.\n"\
                                            "`/claim_wordle`: Use this in <#1465413621382123662> to submit daily wordle for xp by pasting wordle result into the command.\n"\
                                            "`/socials`: Lists JSA's socials.\n"\
                                            "`/shota`: Dedication to JSA's Founder Shota Konno.\n"\
                                            "### Quests\n"\
                                            f"Daily/Weekly quests are posted in <#{config.QUEST_CHANNEL_ID}>.\n"\
                                            f"Dailies can be submitted in <#{config.DAILY_SUBMISSION_ID}>.\n"\
                                            f"Weeklies can be submitted in <#{config.WEEKLY_SUBMISSION_ID}>.\n"\
                                            "Officers will manually check submissions and approve them with a :white_check_mark:."
    isofficer = any(role.id == config.OFFICER_ROLE_ID for role in interaction.user.roles)
    if(isofficer):
        descriptiontext +=  "\n"\
                            "### Officer Commands\n"\
                            "`/process_event`: Adds attendance sheet url for event"
    descriptiontext += "\n\n"
    descriptiontext+="For any questions feel free to reach out to an officer."
    my_embed = discord.Embed(title="Battle Pass Help",
                                            description=descriptiontext)
    await interaction.response.send_message(ephemeral = True,embed=my_embed)
# Claim_Wordle
@bot.tree.command(name="claim_wordle", description="Claim XP for completing Wordle (paste the Wordle share text).", guild=GUILD_ID)
async def claim_wordle(interaction: discord.Interaction, share_text: str):

    try: 
        # ACK immediately so we don't hit the 3s timeout 
        await interaction.response.defer(ephemeral = True)

        # parse the share text
        parsed = wordle_actions.parse_wordle_share(share_text)

        if not parsed:
            await interaction.followup.send(
            "I couldn't find a valid header. Paste the line that looks like: 'Wordle 1674 3/6' plus the grid.", ephemeral=True)
            return
        
        # convert the parsed text to puzzle num and number of attempts
        puzzle, attempts = parsed

        # Wordle must be completed
        if attempts is None: 
            await interaction.followup.send("Looks like this was X/6 (not completed). No XP rewarded.", ephemeral = True) 
            return
        
        client = get_client()
        
        # Prevents double claim error for the same puzzle
        if actions.wordle_claim_exists(client, config.SHEET_ID, puzzle, interaction.user.id):
            await interaction.followup.send("You already claimed this Wordle.", ephemeral=True)
            return

        # Log first so we don't double award if an error occurs
        actions.log_wordle_claim(client, config.SHEET_ID, puzzle, interaction.user.id)

        # Reward the user with WORDLE_XP XP
        result = actions.award_quest_xp(client, config.SHEET_ID, interaction.user.id, config.WORDLE_XP)
        
        # Send the message that the XP has been rewarded
        await interaction.followup.send(f"✅ Wordle {puzzle} completed. +{config.WORDLE_XP} XP\n{result}")

    except Exception as e: 
        # If something crashes after defer, you still need to followup 
        try:
            await interaction.followup.send(f"❌ Error while processing Wordle claim {e}", ephemeral=True)
        except:
            pass
        raise 

@bot.tree.command(name = "award_xp", description = "Manually grant xp to a user.",guild=GUILD_ID)
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def award_xp(interaction: discord.Interaction, user_mention: str, xp_amount: int, reason: str):
    #print(user_id[2:-1])
    client = get_client()
    result = actions.grant_manual_xp(client,config.SHEET_ID,user_mention[2:-1],xp_amount,reason.title(),interaction.user.id)
    await interaction.response.send_message(result)
# command to add whether certain members are board members 
@bot.tree.command(name="sync_board_members", description = "Sync the board member bool on master roster", guild=GUILD_ID)
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def sync_board_members(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    client = get_client()
    actions.check_if_board_member(client, config.SHEET_ID)

    await interaction.followup.send("🔄 Board member statuses synced.")

# Grant Battle Pass access to all members (one-time use)
@bot.tree.command(name="grant_access_all", description="Grant Battle Pass access to all existing members (officer only)", guild=GUILD_ID)
@app_commands.checks.has_role(config.OFFICER_ROLE_ID)
async def grant_access_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    role = guild.get_role(config.BATTLE_PASS_ROLE_ID)
    
    if not role:
        await interaction.followup.send("❌ Error: Battle Pass role not found. Check BATTLE_PASS_ROLE_ID in config.py", ephemeral=True)
        return
    
    count = 0
    errors = 0
    
    for member in guild.members:
        # Skip bots and members who already have the role
        if member.bot or role in member.roles:
            continue
        
        try:
            await member.add_roles(role)
            count += 1
        except Exception as e:
            errors += 1
            print(f"Error assigning role to {member.name}: {e}")
    
    await interaction.followup.send(
        f"✅ **Access Granted!**\n"
        f"Successfully granted access to **{count}** members.\n"
        f"{f'⚠️ {errors} errors occurred.' if errors > 0 else ''}",
        ephemeral=True
    )

# 4. Run the Bot
bot.run(config.DISCORD_TOKEN)