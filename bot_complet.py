import discord
from discord.ui import Button, View, Modal, TextInput
from discord import app_commands
import asyncio
import os

# ─── CONFIGURATION (via variables d'environnement Railway) ────
TOKEN             = os.environ.get("TOKEN",             "")
GUILD_ID          = int(os.environ.get("GUILD_ID",          "1512005220375334923"))
TICKET_CHANNEL_ID = int(os.environ.get("TICKET_CHANNEL_ID", "1512010079711395921"))
STAFF_ROLE_ID     = int(os.environ.get("STAFF_ROLE_ID",     "1512008401322770474"))
# ──────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)


# ════════════════════════════════════════════════════════
#  ARRIVÉE D'UN NOUVEAU MEMBRE
# ════════════════════════════════════════════════════════

@client.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    role_non_verifie = discord.utils.get(guild.roles, name="🔒 Non vérifié")
    if role_non_verifie:
        await member.add_roles(role_non_verifie)

    salon_start = None
    for ch in guild.channels:
        if "start" in ch.name.lower() and isinstance(ch, discord.TextChannel):
            salon_start = ch
            break

    if not salon_start:
        return

    embed = discord.Embed(
        title=f"✈️ Bienvenue sur CHEAP BOOK, {member.display_name} !",
        description=(
            "Bienvenue sur le serveur de réservation d'hébergements **CHEAP BOOK** ! 🏨\n\n"
            "Pour accéder à tous les salons, clique sur le bouton ci-dessous.\n\n"
            "**Ce que tu trouveras ici :**\n"
            "🛎️ Réservation d'hébergements via Booking\n"
            "✈️ Agents d'escale disponibles\n"
            "⭐ Avis clients vérifiés\n"
            "🏆 Classements & récompenses"
        ),
        color=discord.Color.from_rgb(201, 168, 76),
    )
    embed.set_footer(text="CHEAP BOOK · Réservation · Hébergement Premium")
    await salon_start.send(content=member.mention, embed=embed, view=BoutonVerification(member_id=member.id))


# ════════════════════════════════════════════════════════
#  BOUTON DE VÉRIFICATION
# ════════════════════════════════════════════════════════

class BoutonVerification(View):
    def __init__(self, member_id: int):
        super().__init__(timeout=None)
        self.member_id = member_id

    @discord.ui.button(
        label="✅ Je me vérifie et j'accède au serveur",
        style=discord.ButtonStyle.success,
        custom_id="verification",
    )
    async def verifier(self, interaction: discord.Interaction, button: Button):
        guild  = interaction.guild
        member = interaction.user

        role_non_verifie = discord.utils.get(guild.roles, name="🔒 Non vérifié")
        role_verifie     = discord.utils.get(guild.roles, name="✅ Membre vérifié")

        if not role_verifie:
            await interaction.response.send_message("❌ Rôle introuvable. Contacte un admin.", ephemeral=True)
            return

        if role_non_verifie and role_non_verifie in member.roles:
            await member.remove_roles(role_non_verifie)
        await member.add_roles(role_verifie)

        await interaction.response.send_message(
            "✅ Tu es maintenant vérifié ! Bienvenue sur **CHEAP BOOK** 🏨✈️",
            ephemeral=True,
        )


# ════════════════════════════════════════════════════════
#  FORMULAIRE DE RÉSERVATION
# ════════════════════════════════════════════════════════

class FormulaireReservation(Modal, title="🏨 Nouvelle Réservation Booking"):

    nom_hotel = TextInput(label="Nom de l'hôtel", placeholder="Ex : Marriott Paris Champs-Élysées", required=True, max_length=100)
    ville = TextInput(label="Ville de l'hôtel", placeholder="Ex : Paris, Lyon, Barcelone...", required=True, max_length=100)
    date_reservation = TextInput(label="Date de réservation", placeholder="Ex : 15/07/2025 → 20/07/2025", required=True, max_length=100)
    prix = TextInput(label="Prix total (en €)", placeholder="Ex : 350€", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        guild      = interaction.guild
        user       = interaction.user
        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True, read_message_history=True)

        category = None
        for cat in guild.categories:
            if "SUPPORT" in cat.name.upper():
                category = cat
                break

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}", overwrites=overwrites, category=category,
            topic=f"Réservation de {user.display_name} | {self.nom_hotel.value} · {self.ville.value}",
        )

        await interaction.response.send_message(f"✅ Ton ticket a été créé → {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="🏨 Nouvelle demande de réservation",
            description=f"Bonjour {user.mention} ! 👋\nNotre équipe va traiter ta demande très prochainement.",
            color=discord.Color.from_rgb(201, 168, 76),
        )
        embed.add_field(name="🏨 Hôtel",         value=self.nom_hotel.value,        inline=True)
        embed.add_field(name="🌍 Ville",          value=self.ville.value,            inline=True)
        embed.add_field(name="📅 Date de séjour", value=self.date_reservation.value, inline=False)
        embed.add_field(name="💶 Prix total",     value=self.prix.value,             inline=True)
        embed.add_field(name="👤 Client",         value=user.mention,                inline=True)
        embed.set_footer(text="CHEAP BOOK · Réservation Hébergement")

        await ticket_channel.send(
            content=f"{user.mention} {staff_role.mention if staff_role else ''}",
            embed=embed,
            view=BoutonsTicket(user_id=user.id),
        )


# ════════════════════════════════════════════════════════
#  BOUTONS DU TICKET
# ════════════════════════════════════════════════════════

class BoutonsTicket(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="✅ Accepter",   style=discord.ButtonStyle.success,   custom_id="ticket_accept")
    async def accepter(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send(embed=discord.Embed(title="✅ Réservation acceptée", description=f"Acceptée par {interaction.user.mention}.", color=discord.Color.green()))
        await interaction.response.send_message("✅ Acceptée.", ephemeral=True)

    @discord.ui.button(label="⏳ En attente", style=discord.ButtonStyle.secondary, custom_id="ticket_wait")
    async def attente(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send(embed=discord.Embed(title="⏳ En attente", description=f"Mise en attente par {interaction.user.mention}.", color=discord.Color.orange()))
        await interaction.response.send_message("⏳ Mise en attente.", ephemeral=True)

    @discord.ui.button(label="❌ Refuser",    style=discord.ButtonStyle.danger,    custom_id="ticket_refuse")
    async def refuser(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(MotifRefus())

    @discord.ui.button(label="🔒 Fermer",     style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def fermer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🎯 Terminé",    style=discord.ButtonStyle.primary,   custom_id="ticket_done")
    async def termine(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send(embed=discord.Embed(title="🎯 Réservation terminée", description=f"Terminée par {interaction.user.mention}. Merci ! ✈️", color=discord.Color.from_rgb(201, 168, 76)))
        await interaction.response.send_message("🎯 Terminée.", ephemeral=True)


# ════════════════════════════════════════════════════════
#  MOTIF DE REFUS
# ════════════════════════════════════════════════════════

class MotifRefus(Modal, title="❌ Motif du refus"):
    motif = TextInput(label="Raison du refus", placeholder="Ex : Hôtel non disponible à ces dates...", style=discord.TextStyle.paragraph, required=True, max_length=500)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=discord.Embed(title="❌ Réservation refusée", description=f"**Motif :** {self.motif.value}\n\nRefusé par {interaction.user.mention}.", color=discord.Color.red()))
        await interaction.response.send_message("❌ Refus envoyé.", ephemeral=True)


# ════════════════════════════════════════════════════════
#  PANNEAU TICKET
# ════════════════════════════════════════════════════════

class PanneauTicket(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛎️ Créer une réservation", style=discord.ButtonStyle.primary, custom_id="ouvrir_ticket")
    async def ouvrir_ticket(self, interaction: discord.Interaction, button: Button):
        for ch in interaction.guild.channels:
            if isinstance(ch, discord.TextChannel) and ch.name == f"ticket-{interaction.user.name}":
                await interaction.response.send_message(f"❌ Tu as déjà un ticket ouvert → {ch.mention}", ephemeral=True)
                return
        await interaction.response.send_modal(FormulaireReservation())


# ════════════════════════════════════════════════════════
#  COMMANDES SLASH
# ════════════════════════════════════════════════════════

@tree.command(name="setup-tickets", description="Envoie le panneau de tickets dans le salon ticket", guild=discord.Object(id=GUILD_ID))
async def setup_tickets(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return
    channel = interaction.guild.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
        return
    embed = discord.Embed(
        title="✈️ CHEAP BOOK · Réservation Hébergement",
        description="Bienvenue sur **CHEAP BOOK** ! 🏨\n\nClique ci-dessous pour ouvrir un ticket.\n\n**Tu auras besoin de :**\n🏨 Nom de l'hôtel\n🌍 Ville\n📅 Dates de séjour\n💶 Prix total\n\n*Traitement sous 24h.*",
        color=discord.Color.from_rgb(201, 168, 76),
    )
    embed.set_footer(text="CHEAP BOOK · Réservation · Hébergement Premium")
    await channel.send(embed=embed, view=PanneauTicket())
    await interaction.response.send_message(f"✅ Panneau envoyé dans {channel.mention} !", ephemeral=True)


@tree.command(name="setup-verification", description="Envoie le panneau de verification dans start", guild=discord.Object(id=GUILD_ID))
async def setup_verification(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Réservé aux administrateurs.", ephemeral=True)
        return
    salon_start = None
    for ch in interaction.guild.channels:
        if "start" in ch.name.lower() and isinstance(ch, discord.TextChannel):
            salon_start = ch
            break
    if not salon_start:
        await interaction.response.send_message("❌ Salon start introuvable.", ephemeral=True)
        return
    embed = discord.Embed(
        title="✈️ Bienvenue sur CHEAP BOOK !",
        description="Pour accéder à tous les salons, clique sur le bouton ci-dessous.\n\n**Ce que tu trouveras ici :**\n🛎️ Réservation d'hébergements\n✈️ Agents d'escale disponibles\n⭐ Avis clients vérifiés\n🏆 Classements & récompenses\n\n*La vérification est instantanée et gratuite.*",
        color=discord.Color.from_rgb(201, 168, 76),
    )
    embed.set_footer(text="CHEAP BOOK · Réservation · Hébergement Premium")
    await salon_start.send(embed=embed, view=BoutonVerification(member_id=0))
    await interaction.response.send_message(f"✅ Panneau envoyé dans {salon_start.mention} !", ephemeral=True)


@tree.command(name="donner-role", description="Donner manuellement un role a un membre", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(membre="Le membre", role="Le role a donner")
async def donner_role(interaction: discord.Interaction, membre: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        return
    await membre.add_roles(role)
    await interaction.response.send_message(f"✅ Rôle **{role.name}** donné à {membre.mention} !", ephemeral=True)


# ════════════════════════════════════════════════════════
#  DÉMARRAGE
# ════════════════════════════════════════════════════════

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅  Bot connecté : {client.user}")
    print("    Commandes : /setup-tickets · /setup-verification · /donner-role")
    print("━" * 40)


client.run(TOKEN)
