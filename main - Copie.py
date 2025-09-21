import discord
from discord.ext import commands
import datetime

# === INITIALISATION DU BOT ===
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === CONFIG À CHANGER ===
ROLE_MEMBER = 1416913292655460453  # rôle des membres
ROLE_VIP = 1380036343228272781  # rôle des VIP
ROLE_STAFF = 1379496441361338408 # rôle du staff qui gère les tickets
PANEL_CHANNEL = 1417117989974573128 # crée un salon "demande-vip" et mets son ID ici
TICKET_CATEGORY = 1416917195321245708  # crée une catégorie "Tickets" et mets son ID ici
LOG_CHANNEL = 1379493291816652881  # crée un salon "logs-tickets" et mets son ID


@bot.event
async def on_ready():
    print(f"{bot.user} est connecté ✅")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")

# === PANEL DE DEMANDE ===
class VIPSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        role_vip = guild.get_role(ROLE_VIP)
        options = [
            discord.SelectOption(label=vip.display_name, value=str(vip.id))
            for vip in role_vip.members if not vip.bot
        ]

        super().__init__(
            placeholder="Choisis ton VIP...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="choose_vip"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        chosen_vip = guild.get_member(int(self.values[0]))

        # Vérif membre
        if ROLE_MEMBER not in [role.id for role in member.roles]:
            return await interaction.response.send_message(
                "❌ Tu dois être membre pour utiliser ce panel.",
                ephemeral=True
            )

        # Créer ticket privé
        category = guild.get_channel(TICKET_CATEGORY)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(ROLE_STAFF): discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(ROLE_VIP): discord.PermissionOverwrite(view_channel=False),  # cache les autres VIP
            chosen_vip: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {member} avec {chosen_vip}"
        )

        await ticket_channel.send(
            f"🎟️ Ticket ouvert pour {member.mention} avec {chosen_vip.mention}.\n"
            f"Un membre du staff {guild.get_role(ROLE_STAFF).mention} pourra superviser.",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ton ticket avec {chosen_vip.mention} a été ouvert : {ticket_channel.mention}",
            ephemeral=True
        )


class PanelView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.add_item(VIPSelect(guild))


# === FERMETURE DE TICKET ===
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="❌ Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        # Log du ticket
        log_channel = guild.get_channel(LOG_CHANNEL)
        if log_channel:
            messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
            log_text = "\n".join([f"[{m.created_at}] {m.author}: {m.content}" for m in messages if m.content])

            if len(log_text) > 1900:  # éviter la limite Discord
                log_text = log_text[:1900] + "\n... (tronqué)"

            embed = discord.Embed(
                title=f"📑 Logs du ticket #{channel.name}",
                description=f"Fermé par {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await log_channel.send(embed=embed)
            await log_channel.send(f"```{log_text}```")

        await interaction.response.send_message("⏳ Fermeture du ticket...", ephemeral=True)
        await channel.delete()


# === COMMANDE POUR CRÉER LE PANEL ===
@bot.command()
@commands.has_role(ROLE_STAFF)
async def setup_panel(ctx):
    embed = discord.Embed(
        title="🎟️ Panel de demande VIP",
        description="Choisis ton VIP dans le menu ci-dessous pour ouvrir un ticket.",
        color=discord.Color.purple()
    )
    view = PanelView(ctx.guild)
    await ctx.send(embed=embed, view=view)


# === LANCEMENT ===

bot.run("token du bot")  # ⚠️ garde ton token secret
