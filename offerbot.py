import discord
from discord import app_commands, app_commands, Interaction, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from firebase_utils import db
import asyncio

from firebase_utils import (
    save_channel, get_channel,
    save_crew_roles, get_crew_roles,
    save_thresholds, get_thresholds,
    save_ticket, get_ticket, delete_ticket,
    increment_accepted_count, get_accepted_count
)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='/offer ', intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")

@bot.hybrid_command(name="offerhelp", description="Show all available OfferBot commands")
async def offer_help(ctx):
    embed = discord.Embed(title="OfferBot Help", description="List of available commands:")
    embed.add_field(name="/setchannel [channel]", value="Set the channel for the bot to monitor", inline=False)
    embed.add_field(name="/vstandard [channel] [number]", value="Set V threshold for a channel", inline=False)
    embed.add_field(name="/xstandard [channel] [number]", value="Set X threshold for a channel", inline=False)
    embed.add_field(name="/setcrew [role]", value="Add a crew role", inline=False)
    embed.add_field(name="/removecrew [role]", value="Remove a crew role", inline=False)
    embed.add_field(name="/accepted", value="Close ticket as accepted (crew only)", inline=False)
    embed.add_field(name="/irrelevant", value="Close ticket as irrelevant (crew only)", inline=False)
    embed.add_field(name="/remove_offerbot", value="Remove the bot and all data from this server (admin only)", inline=False)
    embed.set_footer(text="Use these commands responsibly. For help, contact the bot owner.")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="setchannel", description="Set the channel for the bot to monitor")
@app_commands.describe(channel="The channel to monitor for suggestions")
@commands.has_permissions(administrator=True)
async def set_channel(ctx, channel: discord.TextChannel):
    save_channel(ctx.guild.id, channel.id)
    await ctx.send(f"Bot channel set to {channel.mention}")
    await offer_help(ctx)

@bot.hybrid_command(name="vstandard", description="Set the minimum V reactions needed")
@app_commands.describe(channel="The channel to set threshold for", number="Minimum V reactions required")
@commands.has_permissions(administrator=True)
async def set_v_threshold(ctx, channel: discord.TextChannel, number: int):
    v_map, x_map = get_thresholds(ctx.guild.id)
    v_map[str(channel.id)] = number
    save_thresholds(ctx.guild.id, v_map, x_map)
    await ctx.send(f"V threshold for {channel.mention} set to {number}")

@bot.hybrid_command(name="xstandard", description="Set the maximum X reactions allowed")
@app_commands.describe(channel="The channel to set threshold for", number="Maximum X reactions allowed")
@commands.has_permissions(administrator=True)
async def set_x_threshold(ctx, channel: discord.TextChannel, number: int):
    v_map, x_map = get_thresholds(ctx.guild.id)
    x_map[str(channel.id)] = number
    save_thresholds(ctx.guild.id, v_map, x_map)
    await ctx.send(f"X threshold for {channel.mention} set to {number}")

@bot.hybrid_command(name="setcrew", description="Add a role that can manage suggestions")
@app_commands.describe(role="The role to add as crew")
@commands.has_permissions(administrator=True)
async def add_crew_role(ctx, role: discord.Role):
    roles = get_crew_roles(ctx.guild.id)
    if role.id not in roles:
        roles.append(role.id)
        save_crew_roles(ctx.guild.id, roles)
        await ctx.send(f"{role.mention} added as crew role")
    else:
        await ctx.send(f"{role.mention} is already a crew role")

@bot.hybrid_command(name="removecrew", description="Remove a crew role")
@app_commands.describe(role="The role to remove from crew")
@commands.has_permissions(administrator=True)
async def remove_crew_role(ctx, role: discord.Role):
    roles = get_crew_roles(ctx.guild.id)
    if role.id in roles:
        roles.remove(role.id)
        save_crew_roles(ctx.guild.id, roles)
        await ctx.send(f"{role.mention} removed from crew roles")
    else:
        await ctx.send(f"{role.mention} is not a crew role")

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user or not reaction.message.guild:
        return

    guild_id = reaction.message.guild.id
    monitored = get_channel(guild_id)
    if str(reaction.message.channel.id) != str(monitored):
        return

    v_count = x_count = 0
    for react in reaction.message.reactions:
        if str(react.emoji) in ('✅','V','v'):
            v_count = react.count - 1
        if str(react.emoji) in ('❌','X','x'):
            x_count = react.count - 1

    v_map, x_map = get_thresholds(guild_id)
    vid = str(reaction.message.channel.id)
    if vid in v_map and v_count >= v_map[vid]:
        await handle_v_threshold(reaction.message)
    if vid in x_map and x_count >= x_map[vid]:
        await reaction.message.delete()
        try:
            await reaction.message.author.send("Your suggestion was removed as it reached the X threshold")
        except:
            pass

async def handle_v_threshold(message: discord.Message):
    guild = message.guild
    author = message.author
    roles = get_crew_roles(guild.id)

    category = discord.utils.get(guild.categories, name="הצעות")
    if not category:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        category = await guild.create_category("הצעות", overwrites=overwrites)

    ticket_channel = await category.create_text_channel(
        f"suggestion-{author.display_name}",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True),
            **{guild.get_role(rid): discord.PermissionOverwrite(read_messages=True) for rid in roles}
        }
    )

    ticket_data = {
        "author": author.id,
        "suggestion": message.content,
        "origin_channel": message.channel.id,
        "origin_message_id": message.id
    }
    save_ticket(guild.id, ticket_channel.id, ticket_data)

    mentions = " ".join(f"<@&{rid}>" for rid in roles)
    await ticket_channel.send(f"{mentions}\nNew suggestion from {author.mention}:\n\n{message.content}")
    try:
        await author.send(f"Your suggestion: *{message.content}* passed threshold. A ticket was opened in the server.")
    except:
        pass

@bot.hybrid_command(name="accepted", description="Close a ticket as accepted")
@commands.has_permissions(manage_messages=True)
async def close_accepted(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    ticket = get_ticket(guild_id, ctx.channel.id)
    if not ticket:
        await ctx.send("This is not a valid ticket channel")
        return

    author = ctx.guild.get_member(ticket["author"])
    suggestion = ticket["suggestion"]

    increment_accepted_count(author.id)
    accepted = get_accepted_count(author.id)

    honor_roles = {5:"ממציא",10:"ממציא דגול (10+)",25:"ממציא גאון (25+)",50:"רעיונאי מדרגה ראשונה (50+)"}
    for thr, name in honor_roles.items():
        if accepted >= thr:
            role = discord.utils.get(ctx.guild.roles, name=name)
            if not role:
                role = await ctx.guild.create_role(name=name, mentionable=False, permissions=discord.Permissions.none())
            if role not in author.roles:
                await author.add_roles(role)

    origin = ctx.guild.get_channel(ticket["origin_channel"])
    if origin:
        await origin.send(f"[{author.display_name}] קיבל את הצעתו. ההצעה הייתה: {suggestion}.")

    try:
        await origin.fetch_message(ticket["origin_message_id"]).then(lambda msg: msg.delete())
    except:
        pass

    try:
        await author.send("ההצעה שלך התקבלה! כל הכבוד, המשך להציע 😊.")
    except:
        pass

    await ctx.send("Ticket closed as accepted")
    await ctx.channel.delete()
    delete_ticket(guild_id, ctx.channel.id)

@bot.hybrid_command(name="irrelevant", description="Close a ticket as irrelevant")
@commands.has_permissions(manage_messages=True)
async def close_irrelevant(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    ticket = get_ticket(guild_id, ctx.channel.id)
    if not ticket:
        await ctx.send("This is not a valid ticket channel")
        return

    try:
        origin = ctx.guild.get_channel(ticket["origin_channel"])
        if origin:
            try:
                msg = await origin.fetch_message(ticket["origin_message_id"])
                await msg.delete()
            except Exception:
                pass
    except Exception:
        pass

    try:
        author = ctx.guild.get_member(ticket["author"])
        if author:
            await author.send("ההצעה שלך לא רלוונטית לנו. נשמח שתמשיך לנסות 😊.")
    except:
        pass

    await ctx.send("Ticket closed as irrelevant")
    await ctx.channel.delete()
    delete_ticket(guild_id, ctx.channel.id)


class ConfirmDeleteView(View):
    def __init__(self, interaction: Interaction):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.value = None

    @discord.ui.button(label="Yes, remove bot", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("Only the command invoker can confirm.", ephemeral=True)
            return
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("Only the command invoker can cancel.", ephemeral=True)
            return
        self.value = False
        self.stop()


@app_commands.command(name="remove_offerbot", description="Completely remove the bot and all data from this server.")
@app_commands.checks.has_permissions(administrator=True)
async def remove_bot_command(interaction: Interaction):
    view = ConfirmDeleteView(interaction)
    await interaction.response.send_message(
        "⚠️ Are you sure you want to remove the bot and delete **all data** for this server?",
        view=view,
        ephemeral=True
    )
    await view.wait()

    if view.value is None:
        await interaction.followup.send("⏱️ Timed out. Operation cancelled.", ephemeral=True)
        return

    if view.value is False:
        await interaction.followup.send("❌ Cancelled. Bot not removed.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)

    # מחיקת כל הדאטה של השרת
    guild_ref = db.collection("guilds").document(guild_id)
    tickets = guild_ref.collection("tickets").list_documents()
    thresholds = guild_ref.collection("thresholds").list_documents()
    crew_roles = guild_ref.collection("crew").list_documents()

    for doc in tickets:
        doc.delete()
    for doc in thresholds:
        doc.delete()
    for doc in crew_roles:
        doc.delete()
    guild_ref.delete()

    await interaction.followup.send("✅ All data has been deleted. Leaving the server...", ephemeral=True)
    await interaction.guild.leave()






bot.run(your_token)
