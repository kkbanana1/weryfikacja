import discord
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import View, Button, Modal, TextInput
import aiohttp
from flask import Flask, request
import threading
import json
import asyncio
import random
import os
import nest_asyncio

nest_asyncio.apply()

# Konfiguracja
TOKEN = "MTM5OTUyNDQzNDA4MzMxOTk1MQ.G0VTbf.bqJchSayuQtszkIb9y9eSVgzwliFxj-zRJJ_pg"
CLIENT_ID = "1399524434083319951"
CLIENT_SECRET = "uRpXgi-eTDPXqL_2cPma4ZuBPBmCQhGP"
REDIRECT_URI = "https://express-production-41d2.up.railway.app/callback"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)

GUILD_ID = 1293639358569512970  # zmień na swój serwer do /test

# ----------------------
# EMBEDY i przyciski
# ----------------------

class AuthView(View):
    def __init__(self):
        super().__init__(timeout=None)
        url = (
            f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
        )
        self.add_item(Button(label="Zweryfikuj się", url=url))

class AddMembersModal(Modal):
    def __init__(self):
        super().__init__(title="Dodaj członków")
        self.liczba = TextInput(label="Liczba osób", required=True)
        self.serwer_id = TextInput(label="ID serwera", required=True)
        self.add_item(self.liczba)
        self.add_item(self.serwer_id)

    async def on_submit(self, interaction: Interaction):
        liczba = int(self.liczba.value)
        target_guild_id = int(self.serwer_id.value)

        try:
            with open("ludzie.json", "r", encoding="utf-8") as f:
                ludzie = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            ludzie = []

        random.shuffle(ludzie)
        wybrani = ludzie[:liczba]

        for user_data in wybrani:
            access_token = user_data["access_token"]
            user_id = user_data["id"]

            async with aiohttp.ClientSession() as session:
                url = f"https://discord.com/api/guilds/{target_guild_id}/members/{user_id}"
                headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
                json_data = {"access_token": access_token}

                async with session.put(url, headers=headers, json=json_data) as resp:
                    print(f"Dodano {user_id}: status {resp.status}")

        await interaction.response.send_message(f"Dodano {liczba} osób na serwer {target_guild_id}!", ephemeral=True)

class AddMembersView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="➕ Dodaj członków", style=discord.ButtonStyle.green)
    async def button_callback(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddMembersModal())

# ----------------------
# EVENT BOT READY
# ----------------------

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")

    channel1 = bot.get_channel(1399744704760909906)
    if channel1:
        embed1 = discord.Embed(title="🔑 Autoryzuj bota", description="Kliknij przycisk poniżej, aby się autoryzować.")
        await channel1.send(embed=embed1, view=AuthView())

    channel2 = bot.get_channel(1399744729914019901)
    if channel2:
        embed2 = discord.Embed(title="➕ Dodaj członków", description="Kliknij, aby dodać osoby na inny serwer.")
        await channel2.send(embed=embed2, view=AddMembersView())

# ----------------------
# KOMENDA TEST
# ----------------------

@bot.tree.command(name="test", description="Komenda testowa")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("To jest testowa komenda!")

# ----------------------
# FLASK: callback
# ----------------------

@app.route("/callback")
def callback():
    code = request.args.get('code')
    if not code:
        return "Brak kodu!"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(handle_callback(code))
    loop.close()
    return result

async def handle_callback(code):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with aiohttp.ClientSession() as session:
        async with session.post("https://discord.com/api/oauth2/token", data=data, headers=headers) as resp:
            token_data = await resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return "Nie udało się uzyskać tokenu!"

    headers = {"Authorization": f"Bearer {access_token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/users/@me", headers=headers) as resp:
            user = await resp.json()

    try:
        with open("ludzie.json", "r", encoding="utf-8") as f:
            ludzie = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ludzie = []

    ludzie.append({"id": user["id"], "access_token": access_token})

    with open("ludzie.json", "w", encoding="utf-8") as f:
        json.dump(ludzie, f, ensure_ascii=False, indent=2)

    return "Autoryzacja zakończona, dzięki!"

# ----------------------
# START
# ----------------------

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
