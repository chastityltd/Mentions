import disnake
from disnake import Embed
from disnake import OptionType
from disnake.ext import commands
from disnake.ui import Button, View
import sqlite3
import re  # Import regular expressions module
import random
from collections import defaultdict
intents = disnake.Intents.default()
intents.messages = True
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

@client.slash_command(
    name="invite",
    description="Get an invite link for the bot",
)
async def invite(ctx: disnake.ApplicationCommandInteraction):
    permissions = 68608
    invite_link = f"https://discord.com/oauth2/authorize?client_id={client.user.id}&permissions={permissions}&scope=bot%20applications.commands"
    await ctx.send(f"Invite the bot to your server using this link: {invite_link}")

@client.slash_command(
    name="remove",
    description="Remove a registered word or phrase",
    options=[
        disnake.Option(
            name="word_or_phrase",
            description="Enter the word or phrase to remove",
            type=disnake.OptionType.string,
            required=True
        )
    ]
)
@commands.guild_only()
async def remove_registered(ctx: disnake.ApplicationCommandInteraction, word_or_phrase: str):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Use parameterized query to avoid SQL injection
    db_cursor.execute("DELETE FROM mentions WHERE user_id=? AND word_or_phrase=?", (ctx.author.id, word_or_phrase))

    db_connection.commit()
    db_connection.close()

    await ctx.send(f"The word/phrase '{word_or_phrase}' has been removed.")

@client.slash_command(
    name="list",
    description="List all registered words or phrases",
)
@commands.guild_only()
async def list_registered(ctx: disnake.ApplicationCommandInteraction):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Use parameterized query to avoid SQL injection
    db_cursor.execute("SELECT word_or_phrase FROM mentions WHERE user_id=?", (ctx.author.id,))
    registered_mentions = db_cursor.fetchall()

    db_connection.close()

    if not registered_mentions:
        await ctx.send("You have not registered any words or phrases.")
    else:
        mentions_list = "\n- ".join([mention[0] for mention in registered_mentions])
        response = f"Registered words or phrases:\n- {mentions_list}"
        await ctx.send(response)


@client.slash_command(
    name="register",
    description="Register a word or phrase",
    options=[
        disnake.Option(
            name="word_or_phrase",
            description="Enter the word or phrase to register",
            type=OptionType.string,
            required=True
        )
    ]
)
@commands.guild_only()
async def register(ctx: disnake.ApplicationCommandInteraction, word_or_phrase: str):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Use parameterized query to avoid SQL injection
    db_cursor.execute("INSERT INTO mentions (user_id, word_or_phrase) VALUES (?, ?)", (ctx.author.id, word_or_phrase))

    db_connection.commit()
    db_connection.close()

    await ctx.send(f"The word/phrase '{word_or_phrase}' has been registered.")



@client.slash_command(
    name="set_autoreply",
    description="Set an autoreply for a word or phrase in the server",
    options=[
        disnake.Option(
            name="word_or_phrase",
            description="Enter the word or phrase to set an autoreply for",
            type=OptionType.string,
            required=True
        ),
        disnake.Option(
            name="autoreply",
            description="Enter the autoreply to send when the word or phrase is mentioned",
            type=OptionType.string,
            required=True
        )
    ]
)
@commands.has_permissions(manage_messages=True)
@commands.guild_only()  # This command can only be used within a guild
async def set_autoreply(ctx: disnake.ApplicationCommandInteraction, word_or_phrase: str, autoreply: str):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Use parameterized query to avoid SQL injection
    db_cursor.execute(
        "INSERT INTO autoreplies (guild_id, word_or_phrase, autoreply) VALUES (?, ?, ?)",
        (ctx.guild.id, word_or_phrase, autoreply)
    )

    db_connection.commit()
    db_connection.close()


    await ctx.send(f"An autoreply for the word/phrase '{word_or_phrase}' has been set in this server.")
@client.slash_command(
    name="list_autoreplies",
    description="List all registered autoreplies",
)
async def list_autoreplies(ctx: disnake.ApplicationCommandInteraction):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    db_cursor.execute("SELECT word_or_phrase, autoreply FROM autoreplies WHERE guild_id=?", (ctx.guild.id,))
    registered_autoreplies = db_cursor.fetchall()

    db_connection.close()

    if not registered_autoreplies:
        await ctx.send("There are no registered autoreplies in this server.")
    else:
        autoreplies_list = [f"Word/Phrase: '{ar[0]}', Autoreply: '{ar[1]}'" for ar in registered_autoreplies]

        # Split into chunks of 25 and send in separate embeds
        for i in range(0, len(autoreplies_list), 25):
            chunk = autoreplies_list[i:i+25]

            # Create and send embed
            embed = Embed(title="Registered Autoreplies", color=0x00FF00)  # Adjust the color as needed
            embed.description = "\n".join(chunk)
            await ctx.send(embed=embed)


@client.slash_command(
    name="remove_autoreply",
    description="Remove a registered autoreply word or phrase from the server",
    options=[
        disnake.Option(
            name="word_or_phrase",
            description="Enter the autoreply word or phrase to remove",
            type=disnake.OptionType.string,
            required=True
        )
    ]
)
@commands.has_permissions(manage_messages=True)
@commands.guild_only()  # This command can only be used within a guild
async def remove_autoreply(ctx: disnake.ApplicationCommandInteraction, word_or_phrase: str):
    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Use parameterized query to avoid SQL injection
    db_cursor.execute(
        "DELETE FROM autoreplies WHERE guild_id=? AND word_or_phrase=?",
        (ctx.guild.id, word_or_phrase)
    )

    db_connection.commit()
    db_connection.close()

    await ctx.send(f"The autoreply for the word/phrase '{word_or_phrase}' has been removed from this server.")


import random  # Import random module

async def send_mention_notification(user_id, word_or_phrase, message):
    user = await client.fetch_user(user_id)

    server_name = message.guild.name if message.guild else "Direct Message"
    channel_mention = message.channel.mention if message.guild else "N/A"
    mention_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

    embed = disnake.Embed(
        title="Mention Notification",
        description=f"You were mentioned in a message with the registered word/phrase: '{word_or_phrase}'",
        color=disnake.Color.blue()
    )
    embed.add_field(name="Server", value=server_name, inline=True)
    embed.add_field(name="Channel", value=channel_mention, inline=True)
    embed.add_field(name=" ", value=" ", inline=False)
    embed.add_field(name="Mentioned by", value=message.author.mention, inline=True)
    embed.add_field(name="Message Content", value=message.content, inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    button = disnake.ui.Button(
        label=f"Jump to Message",
        style=disnake.ButtonStyle.link,
        url=mention_link
    )

    view = disnake.ui.View()
    view.add_item(button)

    await user.send(embed=embed, view=view)

@client.event
async def on_message(message: disnake.Message):
    if message.author.bot:
        return

    db_connection = sqlite3.connect("config.sqlite3")
    db_cursor = db_connection.cursor()

    # Process mentions
    db_cursor.execute("SELECT user_id, word_or_phrase FROM mentions")
    registered_mentions = db_cursor.fetchall()

    for user_id, word_or_phrase in registered_mentions:
        if re.search(rf'\b{word_or_phrase}\b', message.content, re.IGNORECASE):
            await send_mention_notification(user_id, word_or_phrase, message)

    # Process autoreplies
    if message.guild:  # Only process autoreplies in guild channels, not DMs
        db_cursor.execute("SELECT word_or_phrase, autoreply FROM autoreplies WHERE guild_id=?", (message.guild.id,))
        registered_autoreplies = db_cursor.fetchall()

        matching_autoreplies = []

        for word_or_phrase, autoreply in registered_autoreplies:
            if re.search(rf'\b{word_or_phrase}\b', message.content, re.IGNORECASE):
                matching_autoreplies.append(autoreply)

        if matching_autoreplies:  # If there are any matching autoreplies
            chosen_autoreply = random.choice(matching_autoreplies)
            await message.channel.send(chosen_autoreply)

    db_connection.close()
    await client.process_commands(message)



client.run(db_cursor.execute("SELECT Token FROM configData").fetchone)
