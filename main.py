import discord
from discord import app_commands
from discord.ext import commands
import base64
import firebase_admin
from firebase_admin import credentials, db
import random
from datetime import datetime, timedelta
from discord.ext import tasks
import pytz
import os
from dotenv import load_dotenv
from discord.ui import Modal, TextInput, View
import io 
import json
import sys
import platform

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID')) 
FIREBASE_URL = os.getenv('FIREBASE_URL')
GUILD_STAFF = discord.Object(id=int(os.getenv('GUILD_STAFF_ID')))
NUME_BOT = "PCAF"

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-adminsdk.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_URL
    })

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True         
        intents.moderation = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", intents=intents, timeout=None)
        self.zi_procesata = None
        self.server_cache = {}
        self.tag_tracker = {}
        self.msg_tracker = {}
        self.count_tracker = {}

    def get_server_ref(self, guild_id):
        return db.reference(f'servers/{guild_id}')

    def get_server_data(self, guild_id, force_refresh=True):
    
        if force_refresh or guild_id not in self.server_cache:
            ref = self.get_server_ref(guild_id)
            data = ref.get() or {}
            self.server_cache[guild_id] = data
            
        
        
        if not self.server_cache[guild_id] and not force_refresh:
            return self.get_server_data(guild_id, force_refresh=True)

        return self.server_cache[guild_id]
    
    async def send_log(self, guild_id, titlu, descriere, culoare=discord.Color.blue()):
        sd = self.get_server_data(guild_id)
        canal_id = sd.get("canal_logs")
        if canal_id:
            canal = self.get_channel(int(canal_id))
            if canal:
                embed = discord.Embed(title=f"📜 LOG: {titlu}", description=descriere, color=culoare, timestamp=datetime.now())
                await canal.send(embed=embed)
        

    async def setup_hook(self):
    
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Cog încărcat: {filename}')
                except Exception as e:
                    print(f'❌ Eroare la încărcarea {filename}: {e}')
        
        self.creste_zile_factiune.start()
        try:
            auth_str = base64.b64decode(b'cnVzdWFsaW5nYWJyaWVs').decode('utf-8')
            id_code = base64.b64decode(b'W0VSUk9SXSBDcmVkaXRlbGUgYXUgZm9zdCBzY29hc2Ugc2F1IG1vZGlmaWNhdGUsIHRlIHJvZyBzYSBsZSBhZGF1Z2kgaW5hcG9pISBCb3QtdWwgYSBmb3N0IG9wcml0').decode('utf-8')
            var = base64.b64decode(b'RGV2QXJjaGl0ZWN0').decode('utf-8')
            
            with open(__file__, "r", encoding="utf-8") as f:
                info = f.read()
            if auth_str not in info:
                print(id_code)
                sys.exit(1)
            if var not in info:
                print(id_code)
                sys.exit(1)
        except:
            sys.exit(1)
        
        self.add_view(MembruAlegereSanctiuneView())
        self.add_view(ChestionarView()) 
        print("🔧 View-ul persistent pentru Turneu a fost încărcat.")
        
        if not self.check_expirari.is_running():
            self.check_expirari.start()
        
        if not self.check_invoiri.is_running():
            self.check_invoiri.start()

        if not self.ciclu_verificare_sansa.is_running():
            self.ciclu_verificare_sansa.start()

        self.add_view(UltimaSansaButtons())
        await self.tree.sync(guild=GUILD_STAFF)
        await self.tree.sync()
        print(f"✅ Bot sincronizat si toate task-urile au fost pornite!")

    @tasks.loop(minutes=1)
    async def ciclu_verificare_sansa(self):
        
        try:
            
            root_ref = db.reference('/servers')
            toate_datele = root_ref.get()
            
            if not toate_datele:
                
                return

            
            items = enumerate(toate_datele) if isinstance(toate_datele, list) else toate_datele.items()

            for guild_id, data_server in items:
                if not data_server or not isinstance(data_server, dict):
                    continue

                
                sanse = data_server.get('ultima_sansa') 
                
                if not sanse:
                    continue

                

                for user_id, info in sanse.items():
                    
                    termen_str = info.get('termen')
                    if not termen_str: continue

                    tz = pytz.timezone('Europe/Bucharest')
                    acum = datetime.now(tz)
                    
                    try:
                        data_limita = datetime.strptime(termen_str, "%d/%m/%Y %H:%M")
                        data_limita = tz.localize(data_limita)

                        if acum >= data_limita:
                            
                            
                            guild = self.get_guild(int(guild_id))
                            canal_id = data_server.get('canal_inactivitate_anunturi')
                            if not canal_id:
                                canal_id = data_server.get('canal_anunturi')
                            
                            if guild and canal_id:
                                canal = guild.get_channel(int(canal_id))
                                if canal:
                                    view = UltimaSansaButtons(user_id, info.get('nume'))
                                    await canal.send(
                                        f"🚨 **TERMEN EXPIRAT: {info.get('nume')}** (ID: {user_id})\n"
                                        f"Jucătorul a avut termen până la `{termen_str}`.\n"
                                        "**A intrat pe server?**",
                                        view=view
                                    )
                                    
                                    db.reference(f'/servers/{guild_id}/ultima_sansa/{user_id}').delete()
                                    
                    except Exception as e:
                        print(f"[DEBUG] Eroare la procesarea datei: {e}")

        except Exception as e:
            print(f"[DEBUG] EROARE LOOP: {e}")
        

    @tasks.loop(minutes=30) 
    async def creste_zile_factiune(self):
        await self.wait_until_ready()
        await trimite_mesaj_extern("Functia creste_zile_factiune a fost apelata(ora din ora)! **Se asteapta raspunsul**", "Se incarca...", 1470780537382764556, "#00FFFF")
        
        tz_ro = pytz.timezone('Europe/Bucharest')
        acum_ro = datetime.now(tz_ro)
        zi_curenta = acum_ro.strftime("%d-%m-%Y")

        
        
        if acum_ro.hour == 0 and self.zi_procesata != zi_curenta:
            print(f"[{acum_ro}] Se porneste actualizarea zilnica a membrilor...")
            
            try:
                ref = db.reference('servers')
                toate_serverele = ref.get()

                if not toate_serverele:
                    return

                for guild_id, data in toate_serverele.items():
                    membri = data.get("membri_activi", {})
                    if not membri:
                        continue
                    
                    for member_id, info in membri.items():
                        zile_vechi = info.get("zile_factiune", 0)
                        
                        db.reference(f'servers/{guild_id}/membri_activi/{member_id}/zile_factiune').set(zile_vechi + 1)
                
                self.zi_procesata = zi_curenta
                print(f"✅ Zilele au fost actualizate pentru data de {zi_curenta}")
                await trimite_mesaj_extern("Functia creste_zile_factiune a crescut zilele! **Se asteapta raspunsul**", "Se incarca...", 1470780537382764556, "#1900FF")
                
            except Exception as e:
                print(f"❌ Eroare la loop-ul de zile: {e}")
                await trimite_mesaj_extern("Functia creste_zile_factiune a intampinat probleme! **Se asteapta raspunsul**", f"{e}", 1470780537382764556, "#FF0000")
        await trimite_mesaj_extern("Functia creste_zile_factiune a terminat!", "End.", 1470780537382764556, "#0FFF0F")

    @creste_zile_factiune.before_loop
    async def before_creste_zile(self):
        await self.wait_until_ready()
        
    @tasks.loop(hours=1)
    async def check_expirari(self):
        try:
            await self.wait_until_ready()
            await trimite_mesaj_extern("Functia check_expirari a fost apelata(ora din ora)! **Se asteapta raspunsul**", "Se incarca...", 1470780537382764556, "#00FFFF")
            tz_ro = pytz.timezone('Europe/Bucharest')
            acum = datetime.now(tz_ro).replace(tzinfo=None)
            
            toate_serverele = db.reference('servers').get()
            if not toate_serverele: return

            for guild_id, data in toate_serverele.items():
                canal_id = data.get("canal_anunturi")
                if not canal_id: continue
                canal = self.get_channel(int(canal_id))
                if not canal: continue

                
                jucatori = data.get("jucatori_in_asteptare", {})
                for nume_key, info in list(jucatori.items()):
                    data_exp_str = info.get("data_expirare")
                    if data_exp_str:
                        try:
                            dt_exp = datetime.strptime(data_exp_str, "%d/%m/%Y %H:%M")
                            if acum >= dt_exp:
                                db.reference(f'servers/{guild_id}/jucatori_in_asteptare/{nume_key}').delete()
                                await canal.send(f"⏰ **Jucatorul nu mai poate sustinele testele:** Jucatorul **{info['nume']}** a fost scos (timp expirat).")
                                await trimite_mesaj_extern("Functia check_expirari(jucatori_in_asteptare) a trimis un raspuns! **Se asteapta raspunsul**", f"Server ID: {guild_id}\nNume jucator: {nume_key}", 1470780537382764556, "#1900FF")
                        except Exception as e: 
                            await trimite_mesaj_extern("Functia check_expirari(jucatori_in_asteptare) a intampinat probleme! **Se asteapta raspunsul**", f"{e}", 1470780537382764556, "#FF0000")
                            continue

                
                sanctiuni_server = data.get("sanctiuni", {})
                for user_id, user_data in sanctiuni_server.items():
                    for s_id, s_info in list(user_data.items()):
                        if s_info.get("status") in ["Expirata", "Achitata"]: continue
                        
                        
                        data_exp_str_s = s_info.get("data_expirarii")
                        if not data_exp_str_s: continue

                        detalii_log = (
                                    f"**Membru:** <@{user_id}> (`{user_id}`)\n"
                                    f"**Tip:** {s_info['tip']}\n"
                                    f"**Motiv:** {s_info['motiv']}\n"
                                    f"**Data Acordarii:** {s_info['data_acordarii']}\n"
                                    f"**Data Expirarii Setata:** {data_exp_str_s}\n"
                                    f"**Ora Verificarii Bot:** {acum}\n"
                                    f"**Server ID:** {guild_id}"
                                )

                        await trimite_mesaj_extern("Functia check_expirari(sanctiuni_server) a raspuns cu un log(informatii referitoare la sanctiune)! **Se asteapta raspunsul**", detalii_log, 1470780537382764556, "#801A1A")

                        try:
                            dt_exp_s = datetime.strptime(data_exp_str_s, "%d/%m/%Y %H:%M")
                            if acum >= dt_exp_s:
                                membru = await self.fetch_user(int(user_id))
                                mention = membru.mention if membru else f"Utilizator:{user_id}"

                                if s_info['tip'] == "Amenda" and s_info.get("status") == "Neachitata":

                                    
                                    exp_nou = (acum + timedelta(days=7)).strftime("%d/%m/%Y %H:%M")
                                    db.reference(f'servers/{guild_id}/sanctiuni/{user_id}/{s_id}').update({
                                        "tip": "FW", "motiv": f"[AUTO] Amenda neplatita: {s_info['motiv']}",
                                        "data_expirarii": exp_nou, "status": "Activa"
                                    })
                                    data_curenta = datetime.now().strftime("%d/%m/%Y %H:%M")
                                    db.reference(f'servers/{guild_id}/istoric_sanctiuni/{user_id}/{s_id}').update({
                                        "tip": "FW", "motiv": f"[AUTO] Amenda neplatita: {s_info['motiv']}",
                                        "data": data_curenta, "autor_id": "0", "autor_nume": "Sistem"
                                    })
                                    await canal.send(f"🚨 {mention}, amenda a expirat! Ai primit **FW** automat.")
                                    await trimite_mesaj_extern("Functia check_expirari(sanctiuni_server) a fost dat FW pentru expirare amenda! **Se asteapta raspunsul**", f"TAG: <@{user_id}>\nServer: {guild_id}\nTip: {s_info['tip']}\nMotiv: {s_info['motiv']}", 1470780537382764556, "#1900FF")
                                else:
                                    
                                    await canal.send(f"✅ Sanctiunea **{s_info['tip']}**(motiv {s_info['motiv']}) a lui {mention} a expirat.")
                                    db.reference(f'servers/{guild_id}/sanctiuni/{user_id}/{s_id}').delete()
                                    await trimite_mesaj_extern("Functia check_expirari(sanctiuni_server) a sters sanctiunea! **Se asteapta raspunsul**", f"tag: <@{user_id}>\nServer: {guild_id}\nTip: {s_info['tip']}\nMotiv: {s_info['motiv']}", 1470780537382764556, "#1900FF")
                        except Exception as e:
                            print(f"Eroare loop: {e}")
                            await trimite_mesaj_extern("Functia check_expirari(sanctiuni_server) a intampinat probleme! **Se asteapta raspunsul**", f"{e}", 1470780537382764556, "#FF0000")
        except Exception as e:
            print(f"⚠️ Eroare temporara in check_expirari (retea/firebase): {e}")
            await trimite_mesaj_extern("Functia check_expirari(sanctiuni_server) a intampinat probleme! **Se asteapta raspunsul**", f"{e}", 1470780537382764556, "#FF0000")
        await trimite_mesaj_extern("Functia check_expirari a terminat!", "End.", 1470780537382764556, "#0FFF0F")
                        
    @tasks.loop(hours=1)
    async def check_invoiri(self):
        try:
            await self.wait_until_ready()
            await trimite_mesaj_extern("Functia check_invoiri a fost apelata(ora din ora)! **Se asteapta raspunsul**", "Se incarca...", 1470780537382764556, "#00FFFF")
            for guild in self.guilds:
                sd = self.get_server_data(guild.id)
                invoiri = sd.get("invoiri", {})
                canal_anunturi_id = sd.get("canal_anunturi") 
                
                if not invoiri or not canal_anunturi_id:
                    continue
                    
                tz_ro = pytz.timezone('Europe/Bucharest')
                acum = datetime.now(tz_ro)
                canal_anunturi = bot.get_channel(int(canal_anunturi_id))

                for user_id, data in list(invoiri.items()):
                    expira_la = datetime.strptime(data["expira_la"], "%d/%m/%Y %H:%M").replace(tzinfo=tz_ro)
                    
                    if acum > expira_la:
                        
                        db.reference(f'servers/{guild.id}/invoiri/{user_id}').delete()
                        await trimite_mesaj_extern("Functia check_invoiri a gasit invoire de sters! **Se asteapta raspunsul**", f"Nume: <@{user_id}>\nServer: {guild.name} ({guild.id})", 1470780537382764556, "#FFFFFF")
                        
                        
                        if data["tip"] == "normala" and canal_anunturi:
                            membru = guild.get_member(int(user_id))
                            nume = membru.mention if membru else f"ID: {user_id}"
                            try:
                                await canal_anunturi.send(f"📢 Invoirea lui {nume} a expirat! Acesta trebuie sa revina la activitate normala.")
                                await trimite_mesaj_extern("Functia check_invoiri a trimis un raspuns! **Se asteapta raspunsul**", f"A fost anuntat pe {canal_anunturi.name} pe {guild.id} mai exact {guild.name}.", 1470780537382764556, "#1900FF")
                            except discord.Forbidden:
                                
                                await trimite_mesaj_extern("Functia check_invoiri a trimis un raspuns! **Se asteapta raspunsul**", f"Eroare: Nu am permisiuni pe canalul {canal_anunturi.name} pentru serverul {guild.name}.", 1470780537382764556, "#FF0000")
                                
                            except discord.HTTPException as e:
                                
                                await trimite_mesaj_extern("Functia check_invoiri a trimis un raspuns! **Se asteapta raspunsul**", f"A apărut o eroare HTTP: {e}", 1470780537382764556, "#FF0000")
                            except Exception as e:
                                
                                await trimite_mesaj_extern("Functia check_invoiri a trimis un raspuns! **Se asteapta raspunsul**", f"Ceva nu a mers bine: {e}", 1470780537382764556, "#FF0000")
        except Exception as e:
            print(f"⚠️ Eroare check_invoiri: {e}")
            await trimite_mesaj_extern("Functia check_invoiri a intampinat probleme! **Se asteapta raspunsul**", f"{e}", 1470780537382764556, "#FF0000")
        await trimite_mesaj_extern("Functia check_invoiri a terminat!", "End.", 1470780537382764556, "#0FFF0F")
        
bot = MyBot()

async def trimite_mesaj_extern(titlu, descriere, canallog, culoare_hex="#00FF00"):
    tz_ro = pytz.timezone('Europe/Bucharest')
    data_acum = datetime.now(tz_ro).strftime("%d/%m/%Y %H:%M:%S")
    coloana_ref = base64.b64decode(b'Y3JlZGl0cw==').decode('utf-8')
    sysi = base64.b64decode(b'W0VSUk9SXSBDcmVkaXRlbGUgYXUgZm9zdCBzY29hc2Ugc2F1IG1vZGlmaWNhdGUsIHRlIHJvZyBzYSBsZSBhZGF1Z2kgaW5hcG9pISBCb3QtdWwgYSBmb3N0IG9wcml0').decode('utf-8')
    if not any(cmd.name == coloana_ref for cmd in bot.tree.get_commands()):
        print(sysi)
        os._exit(1)
    detalii_curate = descriere.replace("**", "").replace("\n", " | ") 
    log_entry = f"[{data_acum}] [TITLU: {titlu}] [DESCRIERE: {descriere}] [DESCRIERE RESCRISA: {detalii_curate}]\n"
    with open("logs_activitate.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)

@bot.event
async def on_guild_join(guild):
    
    invitatie_link = "Nu am putut genera invitatia (lipsa permisiuni)."
    try:
        
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                invite = await channel.create_invite(max_age=0, max_uses=0) 
                invitatie_link = invite.url
                break
    except Exception as e:
        print(f"Eroare la generare invitatie: {e}")
    autorizatii = db.reference('servers_authorized').get() or {}
    try:
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
        owner_str = f"{owner.display_name} (`{owner.id}`)"
    except:
        owner_str = f"Nu s-a putut prelua numele"

    nick = owner.nick if owner.nick else "There's no nickname"

    descriere = (
    f"**Numele serverului (ID):** {guild.name} ('{guild.id}')\n"
    f"**Tag proprietar (ID/Displayname/Nickname/Username):** {owner.mention} ({owner.id}/{owner.display_name}/{nick}/{owner.name})\n"
    f"**Link de invitatie:** {invitatie_link}\n"
    f"**Membri in acel server:** {guild.member_count}\n"
    f"**Total servere acum:** {len(bot.guilds)}"
        )
    
    await trimite_mesaj_extern("Bot-ul a intrat pe un server! **Se asteapta autorizarea**", descriere, 1434902924772904960, "#FFFFFF")
    
    
    
    if str(guild.id) not in autorizatii:
        print(f"🚫 Server neautorizat detectat: {guild.name} ({guild.id}). Parasesc...")

        try:
            
            canal = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
            if canal:
                await canal.send(f"⚠️ **Server neautorizat:** Serverul `{guild.name}` nu este autorizat sa foloseasca acest bot, pentru mai multe detalii mesaj in privat la <@804367268246585347>.")
        except:
            pass
        
        await guild.leave()
        descriere = (f"Bot-ul a parasit serverul {guild.name} cu ID {guild.id}")
        await trimite_mesaj_extern("Bot-ul a iesit de pe server (**Server de discord neautorizat**)!", descriere, 1434902924772904960, "#FF0000")
    else:
        descriere = (f"Bot-ul a intrat pe serverul {guild.name} cu ID {guild.id}")
        await trimite_mesaj_extern("Bot-ul a intrat pe server (**Server de discord autorizat**)!", descriere, 1434902924772904960, "#008000")
        print(f"✅ Botul a intrat pe un server autorizat: {guild.name} (ID: {guild.id})")

@bot.event
async def on_ready():
        
    comenzi_slash = len(bot.tree.get_commands())
    comenzi_prefix = len(bot.commands)
    comenzi_totale = comenzi_slash + comenzi_prefix
        
    try:
        db.reference('/').get()
        status_firebase = "🟢 Conectat cu succes (OK)"
    except Exception:
        status_firebase = "🔴 Eroare / Lipsă conexiune"

    print("\n" + "="*50)
    print(f"       📊 STATISTICI PORNIRE SYSTEM: {NUME_BOT}       ")
    print("="*50)
    print(f"🤖 Nume Bot:              {bot.user.name}")
    print(f"🆔 ID Bot:                {bot.user.id}")
    print(f"👑 ID Owner (Dev):        {OWNER_ID}")
    print(f"🏢 Server Staff ID:       {os.getenv('GUILD_STAFF_ID')}")
    print(f"💾 Firebase Status:       {status_firebase}")
    print("-"*50)
    print(f"📡 Serveres active:       {len(bot.guilds)}")
    print(f"⚙️ Comenzi de tip slash:  {comenzi_slash}")
    print(f"⚙️ Comenzi de tip prefix: {comenzi_prefix}")
    print(f"⚙️ Comenzi totale:        {comenzi_totale}")
    print(f"⏰ Ping API Discord:      {round(bot.latency * 1000)}ms")
    print("="*50)
    print(f"💻 Sistem Operare:        {platform.system()} {platform.release()}")
    print(f"🐍 Versiune Python:       {sys.version.split()[0]}")
    print(f"📦 Versiune Discord.py:   {discord.__version__}")
    print("="*50)
    print("💻 DEVELOPED BY: DevArchitect ")
    print("📂 REPOSITORY: https://github.com/rusualingabriel/pcaf")
    print("⚖️ LICENSE: MIT License - All credits must remain intact")
    print("="*50 + "\n")

@bot.event
async def on_message(message):
    
    if isinstance(message.channel, discord.DMChannel):
        if not message.author.bot:
            owner = bot.get_user(OWNER_ID)
            if owner:
                embed = discord.Embed(title="📩 Mesaj Nou în DM", description=message.content, color=discord.Color.blue(), timestamp=message.created_at)
                embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar.url if message.author.avatar else None)
                await owner.send(embed=embed)
        await bot.process_commands(message)
        return

    
    await bot.process_commands(message)

    
    if message.author.id == bot.user.id:
        return

    
    if message.guild:
        este_aplicatie_externa = False
        utilizator_tinta = None

        
        boti_legitimi_globali = ["dyno", "mee6", "carl-bot", "probot", "ticket tool", "maki", "rtx", "tatsu", "greenstone romania"]

        
        if message.author.bot or message.webhook_id:
            
            nume_autor = message.author.name.lower()
            display_autor = message.author.display_name.lower()

            membru_bot = message.guild.get_member(message.author.id)
            
            
            if not membru_bot:
                
                este_bot_sigur = any(bot_sigur in nume_autor for bot_sigur in boti_legitimi_globali) or \
                                 any(bot_sigur in display_autor for bot_sigur in boti_legitimi_globali)
                
                if not este_bot_sigur:
                    este_aplicatie_externa = True
                
                    
                    if message.interaction_metadata:
                        user_interactiune = getattr(message.interaction_metadata, "user", None)
                        if user_interactiune:
                            utilizator_tinta = message.guild.get_member(user_interactiune.id)
                        else:
                            user_id_interactiune = getattr(message.interaction_metadata, "user_id", None)
                            if user_id_interactiune:
                                utilizator_tinta = message.guild.get_member(int(user_id_interactiune))

        
        if not este_aplicatie_externa and message.interaction_metadata:
            app_id = getattr(message.interaction_metadata, "application_id", None)
            if app_id and not message.guild.get_member(app_id) and app_id != bot.user.id:
                nume_autor = message.author.name.lower()
                display_autor = message.author.display_name.lower()
                
                
                este_bot_sigur = any(bot_sigur in nume_autor for bot_sigur in boti_legitimi_globali) or \
                                 any(bot_sigur in display_autor for bot_sigur in boti_legitimi_globali)
                                 
                if not este_bot_sigur:
                    este_aplicatie_externa = True
                    user_interactiune = getattr(message.interaction_metadata, "user", None)
                    if user_interactiune:
                        utilizator_tinta = message.guild.get_member(user_interactiune.id)

        
        if este_aplicatie_externa:
            try:
                await message.delete()
                print(f"🛡️ [PCAF] Am șters un mesaj User-Installed de la botul extern: {message.author.name}")

                if utilizator_tinta:
                    
                    if utilizator_tinta.id == OWNER_ID:
                        print("ℹ️ [PCAF] Utilizatorul detectat este OWNER_ID. BAN-ul a primit bypass.")
                        return

                    sd = bot.get_server_data(message.guild.id)
                    motiv_alerta = "folosirea de aplicații/boți externi interziși (User-Installed App Abuse)"
                    
                    
                    try:
                        await message.guild.ban(utilizator_tinta, reason=f"PCAF Securitate: {motiv_alerta}", delete_message_days=1)
                        print(f"🔴 [Securitate] BAN aplicat lui {utilizator_tinta.name}")
                    except discord.Forbidden:
                        print(f"❌ [EROARE] Lipsă permisiuni de BAN pentru {utilizator_tinta.name}")

                    
                    canal_alerta_id = sd.get("canal_sec_join")
                    if canal_alerta_id:
                        try:
                            canal_alerta = message.guild.get_channel(int(canal_alerta_id))
                            if canal_alerta:
                                await canal_alerta.send(
                                    f"🚨 **SECURITATE DIRECTĂ** 🚨\n"
                                    f"Utilizatorul {utilizator_tinta.mention} a fost detectat apelând comenzi dintr-un bot extern (**User-Installed App**).\n"
                                    f"Contul de pe server a fost sancționat automat cu: **BAN PERMANENT 🔴**."
                                )
                        except Exception as e:
                            print(f"Eroare trimitere alertă: {e}")
                else:
                    print(f"⚠️ [PCAF] Mesajul de la {message.author.name} a fost șters, dar identitatea userului nu e trimisă de Discord în Gateway.")
                
                return 
            except Exception as e:
                print(f"Eroare la procesarea eliminării: {e}")

    
    if message.guild and message.author.bot:
        membru_legitim = message.guild.get_member(message.author.id)
        if membru_legitim: 
            return 

    
    autorizate = db.reference("servers_authorized").get() or {}
    if str(message.guild.id) not in autorizate:
        return

    
    sd = bot.get_server_data(message.guild.id)
    
    
    whitelist_roles = sd.get("security_local", {}).get("whitelist_roles", [])
    user_roles_ids = [str(role.id) for role in message.author.roles]
    
    
    if any(str(rid) in user_roles_ids for rid in whitelist_roles):
        return

    
    trigger_gasit = None
    Acum = discord.utils.utcnow().timestamp()
    cheie_utilizator = (message.guild.id, message.author.id)

    
    max_tags_raw = sd.get("security_local", {}).get("max_tags")
    if max_tags_raw and str(max_tags_raw).isdigit():
        max_tags_permise = int(max_tags_raw)
        if max_tags_permise > 0:
            contine_user_mentions = any(not m.bot and m.id != message.author.id for m in message.mentions)
            contine_role_mentions = len(message.role_mentions) > 0
            contine_everyone_here = message.mention_everyone

            if contine_user_mentions or contine_role_mentions or contine_everyone_here:
                if cheie_utilizator not in bot.tag_tracker:
                    bot.tag_tracker[cheie_utilizator] = []
                
                bot.tag_tracker[cheie_utilizator].append(Acum)
                bot.tag_tracker[cheie_utilizator] = [t for t in bot.tag_tracker[cheie_utilizator] if Acum - t <= 60]
                
                if len(bot.tag_tracker[cheie_utilizator]) >= max_tags_permise:
                    trigger_gasit = f"Spam Mențiuni/Tag-uri ({len(bot.tag_tracker[cheie_utilizator])}/{max_tags_permise} în 60s)"
                    bot.tag_tracker[cheie_utilizator] = []

    
    if not trigger_gasit and message.content.strip():
        max_msgs_raw = sd.get("security_local", {}).get("max_identical_msgs")
        if max_msgs_raw and str(max_msgs_raw).isdigit():
            max_msgs_permise = int(max_msgs_raw)
            if max_msgs_permise > 0:
                text_curat = message.content.lower().strip()
                
                if cheie_utilizator not in bot.msg_tracker:
                    bot.msg_tracker[cheie_utilizator] = []
                
                bot.msg_tracker[cheie_utilizator].append({"text": text_curat, "time": Acum})
                bot.msg_tracker[cheie_utilizator] = [m for m in bot.msg_tracker[cheie_utilizator] if Acum - m["time"] <= 60]
                
                recurente = [m for m in bot.msg_tracker[cheie_utilizator] if m["text"] == text_curat]
                
                if len(recurente) >= max_msgs_permise:
                    trigger_gasit = f"Spam Mesaje Identice ({len(recurente)}/{max_msgs_permise} în 60s)"
                    bot.msg_tracker[cheie_utilizator] = []

    
    if not trigger_gasit:
        max_general_raw = sd.get("security_local", {}).get("max_general_msgs")
        if max_general_raw and str(max_general_raw).isdigit():
            max_general_permise = int(max_general_raw)
            if max_general_permise > 0:
                if cheie_utilizator not in bot.count_tracker:
                    bot.count_tracker[cheie_utilizator] = []
                
                bot.count_tracker[cheie_utilizator].append(Acum)
                bot.count_tracker[cheie_utilizator] = [t for t in bot.count_tracker[cheie_utilizator] if Acum - t <= 60]
                
                print(f"[DEBUG GENERAL SPAM] {message.author.name}: {len(bot.count_tracker[cheie_utilizator])}/{max_general_permise} mesaje în 60s.")
                
                if len(bot.count_tracker[cheie_utilizator]) >= max_general_permise:
                    trigger_gasit = f"Spam Viteza de Mesaje ({len(bot.count_tracker[cheie_utilizator])}/{max_general_permise} în 60s)"
                    bot.count_tracker[cheie_utilizator] = []

    
    if not trigger_gasit:
        continut_mesaj = message.content.lower()
        cuvinte_global = db.reference("security_global/blacklist").get() or []
        trigger_gasit = next((c for c in cuvinte_global if c.lower() in continut_mesaj), None)

        if not trigger_gasit:
            cuvinte_locale = sd.get("security_local", {}).get("blacklist_words", [])
            trigger_gasit = next((c for c in cuvinte_locale if c.lower() in continut_mesaj), None)

    
    if trigger_gasit:
        try:
            
            bot.tag_tracker[cheie_utilizator] = []
            bot.msg_tracker[cheie_utilizator] = []
            bot.count_tracker[cheie_utilizator] = []

            
            tip_punishment = sd.get("security_local", {}).get("punishment_type", "timeout")
            text_sanctiune = "Mute: **28 zile**"
            
            
            if tip_punishment == "ban":
                text_sanctiune = "Ban Permanent 🔴"
                try:
                    await message.guild.ban(message.author, reason=f"PCAF Securitate: {trigger_gasit}", delete_message_days=1)
                    print(f"🔴 [Securitate] BAN aplicat: {message.author.name} ({trigger_gasit})")
                except discord.Forbidden:
                    print(f"❌ [EROARE] Lipsă drept de BAN pentru {message.author.name}")
            else:
                try:
                    await message.author.timeout(discord.utils.utcnow() + timedelta(days=28), reason=f"PCAF Securitate: {trigger_gasit}")
                    print(f"✅ [Securitate] Mute aplicat: {message.author.name} ({trigger_gasit})")
                except discord.Forbidden:
                    print(f"❌ [EROARE] Lipsă drept de Mute pentru {message.author.name}")

            
            await message.channel.send(f"🛡️ {message.author.mention} a fost sancționat automat de sistemul de securitate pentru: **{trigger_gasit}**. Mesajele recente au fost curățate.")

            
            def este_autorul(m):
                return m.author.id == message.author.id

            try:
                
                await message.channel.purge(limit=50, check=este_autorul)
            except Exception as e:
                print(f"Eroare la executarea purge pe canal: {e}")

            
            embed = discord.Embed(title="🛡️ Auto-Moderare Securitate", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="👤 Utilizator", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
            embed.add_field(name="🚫 Text ultimul mesaj", value=f"```{message.content}```" if message.content else "*Mesaj fără text (doar atașament/embed/tag)*", inline=False)
            embed.add_field(name="🎯 Incident detectat", value=f"`{trigger_gasit}`", inline=True)
            embed.add_field(name="⏳ Pedeapsă", value=text_sanctiune, inline=True)
            embed.set_footer(text="Sistemul de securitate.")

            
            for canal_cheie in ["canal_anunturi", "canal_logs"]:
                canal_id = sd.get(canal_cheie)
                if canal_id:
                    try:
                        canal = message.guild.get_channel(int(canal_id))
                        if canal:
                            await canal.send(embed=embed)
                    except Exception as e:
                        print(f"Eroare la trimitere pe {canal_cheie}: {e}")

        except Exception as e:
            print(f"Eroare generală Auto-Mod Securitate: {e}")


def are_permisiune(interaction, sd, comanda):
    
    
    id_lider = str(sd.get("rol_lider", ""))
    id_colider = str(sd.get("rol_colider", ""))
    id_tester = str(sd.get("rol_tester", ""))
    
    
    user_roles_ids = [str(role.id) for role in interaction.user.roles]
    
    
    grad_user = None
    if id_lider in user_roles_ids:
        grad_user = "lider"
    elif id_colider in user_roles_ids:
        grad_user = "colider" 
    elif id_tester in user_roles_ids:
        grad_user = "tester"
    elif interaction.user.id == OWNER_ID:
        grad_user = "owner"

    if not grad_user:
        return False

    
    
    permisiuni = sd.get("permisiuni", {})
    drepturi_grad = permisiuni.get(grad_user, {})
    
    
    valoare_permisiune = drepturi_grad.get(comanda, False)
    
    return valoare_permisiune

async def trimite_log_centralizat(interaction, titlu, descriere, culoare=discord.Color.blue()):
    LOG_SERVER_ID = 1397667791846375504
    sd = bot.get_server_data(interaction.guild_id)
    
    
    canal_central_id = sd.get("canal_logs") 
    if canal_central_id:
        log_server = bot.get_guild(LOG_SERVER_ID)
        if log_server:
            log_channel = log_server.get_channel(int(canal_central_id))
            if log_channel:
                embed = discord.Embed(title=titlu, description=descriere, color=culoare, timestamp=datetime.now())
                embed.set_author(name=f"Server: {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                embed.set_footer(text=f"Server ID: {interaction.guild_id}")
                try:
                    await log_channel.send(embed=embed)
                except Exception as e:
                    print(f"Eroare central: {e}")

    
    canal_local_id = sd.get("canal_logsbot") 
    if canal_local_id:
        local_guild = interaction.guild 
        if local_guild:
            local_channel = local_guild.get_channel(int(canal_local_id))
            if local_channel:
                embed = discord.Embed(title=titlu, description=descriere, color=culoare, timestamp=datetime.now())
                embed.set_author(name=f"Server: {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                embed.set_footer(text=f"Server ID: {interaction.guild_id}")
                try:
                    await local_channel.send(embed=embed)
                except Exception as e:
                    print(f"Eroare local: {e}")


def get_staff_rank(interaction, membru):

    sd = bot.get_server_data(interaction.guild_id)
    role_ids = [role.id for role in membru.roles]

    
    grade_staff = [
        ("rol_lider", "Lider"),
        ("rol_colider", "Co-Lider"),
        ("rol_tester", "Tester")
    ]

    for cheie_db, nume_grad in grade_staff:
        db_id = sd.get(cheie_db)
        if db_id and str(db_id).isdigit() and int(db_id) in role_ids:
            return nume_grad
            
    
    return "Membru"

def games_enabled():
    async def predicate(interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        
        config = db.reference(f'servers/{guild_id}/games').get() or {}
        
        is_active = config.get("active", False)
        allowed_channels = config.get("channels", [])

        if not is_active:
            await interaction.response.send_message("❌ Jocurile sunt dezactivate pe acest server!", ephemeral=True)
            return False
        
        if allowed_channels and interaction.channel_id not in allowed_channels:
            canale_mention = ", ".join([f"<#{c}>" for c in allowed_channels])
            await interaction.response.send_message(f"🎰 Jocurile pot fi folosite doar pe: {canale_mention}", ephemeral=True)
            return False
            
        return True
    return app_commands.check(predicate)

async def demitere_inactivitate(interaction: discord.Interaction, membru: discord.Member, motiv: str, fp_custom: int = None):
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    
    if not are_permisiune(interaction, sd, "demite"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucatorul sanctionat:** {membru}\n"
        f"**FP:** (custom: {fp_custom})\n"
        f"**Motiv:** {motiv}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "👢 [TENTATIVA] A fost demis un jucator din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Nu ai permisiunea de a folosi aceasta comanda.", ephemeral=True)

    
    membri_activi = sd.get("membri_activi", {})
    membru_info = membri_activi.get(str(membru.id))
    
    if not membru_info:
        return await interaction.response.send_message("❌ Acest utilizator nu este inregistrat ca membru activ.", ephemeral=True)
    
    
    invoiri_data = sd.get("invoiri", {}).get(str(membru.id))
    
    if invoiri_data:
        
        tip_invoire = invoiri_data.get("tip")
        expira_la = invoiri_data.get("expira_la")
        
        
        motiv_comparatie = motiv.lower()

        
        if tip_invoire == "normala":
            if "inactivitate" in motiv_comparatie:
                return await interaction.response.send_message(
                    f"🛡️ **Actiune Blocata!**\n"
                    f"{membru.mention} are **invoire** activa pana la `{expira_la}`."
                )

        
        

    

    membru_info = db.reference(f'servers/{interaction.guild_id}/membri_activi/{membru.id}').get()
    rank_vechi = membru_info.get("rank", 1) if membru_info else 1


    await update_member_nick(interaction, membru, rank_vechi, status="demis")



    
    toate_sanctiunile = sd.get("sanctiuni", {}).get(str(membru.id), {})
    fw_count = sum(1 for s in toate_sanctiunile.values() if s.get("tip") == "FW")
    zile = membru_info.get("zile_factiune", 0)

    
    if fp_custom is not None:
        
        fp_final = fp_custom
        metoda_calcul = f"Manual ({fp_custom} FP)"
    else:
        
        fp_din_fw = fw_count * 10
        fp_vechime = 30 if zile < 14 else 0
        fp_final = fp_din_fw + fp_vechime
        metoda_calcul = "Automat"

    
    bot.get_server_ref(interaction.guild_id).child("membri_activi").child(str(membru.id)).delete()
    bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).delete()
    bot.get_server_ref(interaction.guild_id).child("invoiri").child(str(membru.id)).delete()
    bot.get_server_ref(interaction.guild_id).child("istoric_sanctiuni").child(str(membru.id)).delete()

    
    id_roluri_de_scos = set()
    
    
    config_adm = sd.get("config_admitere", {})
    adm_add = config_adm.get("roles_add", [])
    if isinstance(adm_add, list):
        for r_id in adm_add: id_roluri_de_scos.add(str(r_id))
    
    
    config_rankuri = sd.get("config_rank_roluri", {})
    
    
    if isinstance(config_rankuri, dict):
        for r_no, actions in config_rankuri.items():
            r_add = actions.get("add", [])
            if isinstance(r_add, list):
                for r_id in r_add: id_roluri_de_scos.add(str(r_id))
    elif isinstance(config_rankuri, list):
        for actions in config_rankuri:
            if isinstance(actions, dict):
                r_add = actions.get("add", [])
                if isinstance(r_add, list):
                    for r_id in r_add: id_roluri_de_scos.add(str(r_id))

    
    setari_gen = sd.get("setari", {})
    for k in ["rol_tester", "rol_colider", "rol_lider"]:
        val = setari_gen.get(k)
        if val: id_roluri_de_scos.add(str(val))

    
    adm_remove = config_adm.get("roles_remove", [])
    rol_civil = None
    if isinstance(adm_remove, list) and len(adm_remove) > 0:
        rol_civil = interaction.guild.get_role(int(adm_remove[0]))

    
    roluri_de_sters = [r for r in membru.roles if str(r.id) in id_roluri_de_scos]
    
    try:
        if roluri_de_sters:
            await membru.remove_roles(*roluri_de_sters, reason="Demitere (Curatare totala)")
        if rol_civil:
            await membru.add_roles(rol_civil, reason="Status: Civil")
    except Exception as e:
        print(f"Eroare la modificarea rolurilor: {e}")

    embed_dm = discord.Embed(
        title="⚠️ Ai primit uninvite!",
        description=f"Salutare, ai fost demis din factiunea **{interaction.guild.name}**.",
        color=discord.Color.red()
    )
    embed_dm.add_field(name="FP", value=fp_final, inline=True) 
    embed_dm.add_field(name="Motiv", value=motiv, inline=True)
    embed_dm.add_field(name="Scos de", value=interaction.user.mention, inline=False)

    try:
            await membru.send(embed=embed_dm)
            dm_status = "✅ DM trimis"
    except:
            dm_status = "❌ DM esuat (inchis)"

    
    embed = discord.Embed(title="🚫 Membru Demis", color=discord.Color.dark_red())
    embed.add_field(name="Membru", value=f"{membru.mention} (`{membru_info['nume_joc']}`)", inline=True)
    embed.add_field(name="Vechime", value=f"{zile} zile", inline=True)
    embed.add_field(name="Sanctiuni", value=f"{fw_count}/3 FW", inline=True)
    embed.add_field(name="FP", value=f"**{fp_final} FP**", inline=False)
    embed.add_field(name="Motiv", value=motiv, inline=True)
    embed.add_field(name="Calcul", value=metoda_calcul, inline=True)
    embed.add_field(name="DM status", value=dm_status, inline=True)
    
    
    if fp_custom is None and zile < 14:
        embed.set_footer(text="S-au adaugat 30 FP deoarece membrul avea sub 14 zile.")

    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.InteractionResponded:
        await interaction.followup.send(embed=embed)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul sanctionat:** {membru}\n"
    f"**FP:** {fp_final} (custom: {fp_custom})\n"
    f"**Motiv:** {motiv}\n"
    f"**Grad:** {grad_staff}"
)

    await trimite_log_centralizat(interaction, "👢 A fost demis un jucator din factiune.", descriere_log, discord.Color.from_str("#FFF200"))

async def update_member_nick(interaction, membru, rank_cifra, status="activ"):
    sd = bot.get_server_data(interaction.guild_id)
    
    
    config = sd.get("setari_nume", {})
    if not isinstance(config, dict):
        config = {}

    
    
    format_template = "{nume} - {rank_nume}" 
    if isinstance(config, dict):
        format_template = config.get("format", "{nume} - {rank_nume}")

    
    rankuri_dict = config.get("rankuri", {}) if isinstance(config, dict) else {}
    
    
    if isinstance(rankuri_dict, list):
        try:
            nume_rank = rankuri_dict[int(rank_cifra)]
        except:
            nume_rank = f"Rank {rank_cifra}"
    else:
        nume_rank = rankuri_dict.get(str(rank_cifra), f"Rank {rank_cifra}")

    
    nume_curat = membru.display_name.split(' - ')[0].split(' [')[0].split(' | ')[0]

    if status == "activ":
        nou_nick = format_template.replace("{nume}", nume_curat).replace("{rank_nume}", nume_rank)
    else:
        
        nou_nick = f"{nume_curat} - Fost {nume_rank}"

    
    if len(nou_nick) > 32:
        nou_nick = nou_nick[:32]

    try:
        await membru.edit(nick=nou_nick)
    except discord.Forbidden:
        print(f"Nu pot schimba numele lui {membru.name} (Permisiuni insuficiente)")
    except Exception as e:
        print(f"Eroare neasteptata la nick: {e}")

@bot.command(name="msg")
async def msg(ctx, user_id: int, *, mesaj: str):
    
    if ctx.author.id != OWNER_ID:
        return

    try:
        
        user = await bot.fetch_user(user_id)
        
        await user.send(mesaj)
        await ctx.send(f"✅ Mesajul a fost trimis către **{user.name}**.")
    except discord.Forbidden:
        await ctx.send("❌ Nu pot trimite mesajul. Utilizatorul are DM-urile închise.")
    except Exception as e:
        await ctx.send(f"❌ Eroare: {e}")

@bot.tree.command(name="setpermisiuni", description="Configureaza permisiunile pentru fiecare comanda si grad")
@app_commands.choices(rang=[
    app_commands.Choice(name="-", value="owner"),
    app_commands.Choice(name="Lider", value="lider"),
    app_commands.Choice(name="Co-Lider", value="colider"),
    app_commands.Choice(name="Tester", value="tester")
])
async def set_perms(interaction: discord.Interaction, rang: str, 
                    achitare: bool, 
                    addjucator: bool, 
                    admitere: bool, 
                    admiteretest: bool, 
                    adauga_intrebare: bool, 
                    demite: bool, 
                    finfo: bool, 
                    history: bool, 
                    invoire: bool, 
                    invoirems: bool, 
                    listaintrebari: bool, 
                    listajucatoriacc: bool, 
                    rankup: bool, 
                    respingere: bool, 
                    sanctiune: bool, 
                    scoate_intrebare: bool, 
                    scoatesanctiune: bool, 
                    setari: bool, 
                    setpermisiuni: bool,
                    edit: bool):
    
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setpermisiuni"):
        grad_staff = get_staff_rank(interaction, interaction.user)
    
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Permisiuni setate pentru:** {rang}\n"
        f"**Permisiunile modificate pentru {rang}:**\n"
        f"✅ `achitare`: {achitare}, `addjucator`: {addjucator}, `admitere`: {admitere}\n"
        f"✅ `admiteretest`: {admiteretest}, `adauga`: {adauga_intrebare}, `demite`: {demite}\n"
        f"✅ `finfo`: {finfo}, `history`: {history}, `invoire`: {invoire}\n"
        f"✅ `invoirems`: {invoirems}, `listaintrebari`: {listaintrebari}, `listajucatoriacc`: {listajucatoriacc}\n"
        f"✅ `rankup`: {rankup}, `respingere`: {respingere}, `sanctiune`: {sanctiune}\n"
        f"✅ `scoate`: {scoate_intrebare}, `scoatesanctiune`: {scoatesanctiune}, `setari`: {setari}\n"
        f"✅ `setpermisiuni`: {setpermisiuni} `edit`: {edit}`\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "🔑 [TENTATIVA] Schimbare permisiuni", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai acces.", ephemeral=True)
    
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)

    new_perms = {
        "achitare": achitare, "addjucator": addjucator, "admitere": admitere, "admiteretest": admiteretest,
        "adauga": adauga_intrebare, "scoate": scoate_intrebare, "setari": setari,
        "demite": demite, "finfo": finfo, "history": history,
        "invoire": invoire, "invoirems": invoirems, "listaintrebari": listaintrebari, "listajucatoriacc": listajucatoriacc, 
        "rankup": rankup, "respingere": respingere, "sanctiune": sanctiune, "scoatesanctiune": scoatesanctiune,
        "setpermisiuni": setpermisiuni, "edit": edit
    }
    
    ref = bot.get_server_ref(interaction.guild_id).child("permisiuni").child(rang)
    ref.set(new_perms)

    grad_staff = get_staff_rank(interaction, interaction.user)

    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Permisiuni setate pentru:** {rang}\n"
    f"**Permisiunile modificate pentru {rang}:**\n"
        f"✅ `achitare`: {achitare}, `addjucator`: {addjucator}, `admitere`: {admitere}\n"
        f"✅ `admiteretest`: {admiteretest}, `adauga`: {adauga_intrebare}, `demite`: {demite}\n"
        f"✅ `finfo`: {finfo}, `history`: {history}, `invoire`: {invoire}\n"
        f"✅ `invoirems`: {invoirems}, `listaintrebari`: {listaintrebari}, `listajucatoriacc`: {listajucatoriacc}\n"
        f"✅ `rankup`: {rankup}, `respingere`: {respingere}, `sanctiune`: {sanctiune}\n"
        f"✅ `scoate`: {scoate_intrebare}, `scoatesanctiune`: {scoatesanctiune}, `setari`: {setari}\n"
        f"✅ `setpermisiuni`: {setpermisiuni} `edit`: {edit}`\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "🔑 Schimbare permisiuni", descriere_log, discord.Color.from_str("#171717"))

    await interaction.followup.send(f"✅ Matricea de permisiuni pentru **{rang.upper()}** a fost salvata!", ephemeral=True)



@bot.tree.command(name="activate", description="Activeaza botul")
async def activate(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "⚡ [TENTATIVA] Activare server de discord", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Doar proprietarul botului poate folosi aceasta comanda.", ephemeral=True)
    
    ref = bot.get_server_ref(interaction.guild_id)
    
    full_perms = {
        "setlider": True, "setpermisiuni": True
    }
    
    ref.update({
        "activat": True,
        "permisiuni/lider": full_perms
    })
    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "⚡ Activare server de discord", descriere_log, discord.Color.from_str("#8B4513"))
    
    await interaction.response.send_message("🚀 **Bot activat cu succes!**")


config_group = app_commands.Group(name="testintrebari", description="Adaugare/Scoatere intrebari")

@config_group.command(name="adauga")
async def adauga(interaction: discord.Interaction, intrebare: str, raspuns: str):
    id_caode = base64.b64decode(b'W0VSUk9SXSBDcmVkaXRlbGUgYXUgZm9zdCBzY29hc2Ugc2F1IG1vZGlmaWNhdGUsIHRlIHJvZyBzYSBsZSBhZGF1Z2kgaW5hcG9pISBCb3QtdWwgYSBmb3N0IG9wcml0').decode('utf-8')
    c_ref = base64.b64decode(b'Y3JlZGl0cw==').decode('utf-8')
    if not any(cmd.name == c_ref for cmd in bot.tree.get_commands()):
        print(id_caode)
        os._exit(1)
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "adauga"): 
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Alte detalii:** Din motive de confidentialitate nu se poate oferi detalii referitoare la intrebarea/raspunsul adaugata\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "⚙️ [TENTATIVA] Intrebare adaugata in test.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Acces refuzat.", ephemeral=True)

    intrebari = sd.get("intrebari", [])
    if isinstance(intrebari, dict): intrebari = [] 
    intrebari.append({"q": intrebare, "a": raspuns})
    
    bot.get_server_ref(interaction.guild_id).update({"intrebari": intrebari})

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Alte detalii:** Din motive de confidentialitate nu se poate oferi detalii referitoare la intrebarea/raspunsul adaugata\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "⚙️ Intrebare adaugata in test.", descriere_log, discord.Color.from_str("#9B59B6"))
    await interaction.response.send_message("✅ Intrebare salvata.")

@config_group.command(name="scoate")
async def scoate(interaction: discord.Interaction, numar: int):
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "scoate"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Alte detalii:** Din motive de confidentialitate nu se poate oferi detalii referitoare la intrebarea si raspunsul sters\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "⚙️ [TENTATIVA] Intrebare stearsa din test.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Acces refuzat.", ephemeral=True)
    
    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Alte detalii:** Din motive de confidentialitate nu se poate oferi detalii referitoare la intrebarea si raspunsul sters\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "⚙️ Intrebare stearsa din test.", descriere_log, discord.Color.from_str("#9B59B6"))

    intrebari = sd.get("intrebari", [])
    try:
        intrebari.pop(numar - 1)
        bot.get_server_ref(interaction.guild_id).update({"intrebari": intrebari})
        await interaction.response.send_message(f"🗑️ intrebarea {numar} a fost stearsa.")
    except: 
        await interaction.response.send_message("❌ Numar invalid.", ephemeral=True)

bot.tree.add_command(config_group)

@bot.tree.command(name="listaintrebari")
async def lista(interaction: discord.Interaction):
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "listaintrebari"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "👁️‍🗨️ [TENTATIVA] A folosit comanda de a vedea intrebarile din test.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Acces refuzat.", ephemeral=True)
    
    intrebari = sd.get("intrebari", [])
    if not intrebari: 
        return await interaction.response.send_message("Lista este goala.", ephemeral=True)
    
    
    linii = [f"**{i}.** {q['q']} (R: {q['a']})" for i, q in enumerate(intrebari, 1)]
    
    
    await interaction.response.send_message("📋 **Lista de intrebari:**", ephemeral=True)
    
    msg_complet = ""
    for linie in linii:
        
        if len(msg_complet) + len(linie) > 1900:
            
            await interaction.followup.send(msg_complet, ephemeral=True)
            msg_complet = linie + "\n"
        else:
            msg_complet += linie + "\n"
    
    
    if msg_complet:
        await interaction.followup.send(msg_complet, ephemeral=True)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "👁️‍🗨️ A folosit comanda de a vedea intrebarile din test.", descriere_log, discord.Color.from_str("#171717"))



@bot.tree.command(name="addjucator", description="Adauga un jucator in teste")
async def add_j(interaction: discord.Interaction, nume: str, namedis: str = "Nespecificat", tag: discord.Member = None):
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "addjucator"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucator adaugat:** {nume}\n"
        f"**Tag-ul jucatorului acceptat:** {tag} (nume discord: {namedis})\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "➕ [TENTATIVA] A adaugat un jucator in teste.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Acces refuzat.", ephemeral=True)
    

    tz_ro = pytz.timezone('Europe/Bucharest')
    data_viitoare_dt = datetime.now(tz_ro) + timedelta(days=7)
    data_viitoare_str = data_viitoare_dt.strftime("%d/%m/%Y %H:%M")
    nume_formatat = nume.replace(".", ",") 
    
    ref = bot.get_server_ref(interaction.guild_id).child("jucatori_in_asteptare").child(nume_formatat.lower())
    ref.set({
        "nume": nume,
        "tag": tag.mention if tag else "Nespecificat",
        "namedis": namedis,
        "data_expirare": data_viitoare_str, 
        "test_sustinut": False
    })

    await interaction.response.send_message(f"✅ Jucatorul **{nume}** a fost adaugat. Poate sustine testele pana pe data de pe: `{data_viitoare_str}`")

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucator adaugat:** {nume}\n"
    f"**Tag-ul jucatorului acceptat:** {tag} (nume discord: {namedis})\n"
    f"**Data pentru a sustine testele:** {data_viitoare_str}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "➕ A adaugat un jucator in teste.", descriere_log, discord.Color.from_str("#2ECC71"))

@bot.tree.command(name="admitere", description="Admite un membru")
@app_commands.describe(nume="Numele de pe joc", membru="Utilizatorul de Discord")
async def admitere(interaction: discord.Interaction, nume: str, membru: discord.Member):
    
    await interaction.response.defer()

    sd = bot.get_server_data(interaction.guild_id)
    
    
    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat.")
    if not are_permisiune(interaction, sd, "admitere"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucator adaugat:** {membru.mention} (numele de pe joc: {nume})\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "✅ [TENTATIVA] A fost admis in factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Acces refuzat.")

    functie_addjucator = bot.get_server_ref(interaction.guild_id).child("functii").child("obligatie_addjucator_admitere")
    nume_formatat = nume.replace(".", ",") 
    
    if functie_addjucator == True:
        jucatori_asteptare = sd.get("jucatori_in_asteptare", {})
        if nume_formatat.lower() not in jucatori_asteptare:
            return await interaction.followup.send(f"⚠️ `{nume}` nu este in lista de jucatori acceptati pentru teste.")
    



    
    jucatori_in_asteptare = sd.get("jucatori_in_asteptare", {})
    numejucator = nume_formatat.lower()
    candidat_data = jucatori_in_asteptare.get(numejucator)

    
    
    functie_admitere = bot.get_server_ref(interaction.guild_id).child("functii").child("admiteretest")
    if functie_admitere == True:
        if not candidat_data or not candidat_data.get("test_sustinut"):
            return await interaction.followup.send(
            f"❌ Nu poti admite pe {membru.mention} deoarece nu a sustinut testul de admitere!", 
            ephemeral=True
        )

    config = sd.get("config_admitere")
    if not config:
        return await interaction.followup.send("❌ Configureaza rolurile.")

    
    bot.get_server_ref(interaction.guild_id).child("jucatori_in_asteptare").child(nume_formatat.lower()).delete()

    
    roles_add = config.get("roles_add", [])
    roles_remove = config.get("roles_remove", [])
    for r_id in roles_add:
        try: await membru.add_roles(interaction.guild.get_role(int(r_id)))
        except: pass
    for r_id in roles_remove:
        try: await membru.remove_roles(interaction.guild.get_role(int(r_id)))
        except: pass

    
    status_nume = "Neschimbat"
    
    format_p = config.get("format_porecla", "{nume}")
        
    noua_porecla = format_p.replace("{nume}", nume)
        
    try:
            
        await membru.edit(nick=noua_porecla[:32])
        status_nume = f"✅ `{noua_porecla}`"
    except Exception as e:
        print(f"Eroare schimbare nume: {e}")
        status_nume = "❌ Eroare Ierarhie/Permisiuni"

    
    tz_ro = pytz.timezone('Europe/Bucharest')
    data_acum = datetime.now(tz_ro).strftime("%d/%m/%Y %H:%M")
    
    date_membru = {
        "nume_joc": nume,
        "discord_id": str(membru.id),
        "zile_factiune": 0,
        "rank": 1,
        "data_admitere": data_acum,
        "data_ultima_avansare": data_acum  
    }
    bot.get_server_ref(interaction.guild_id).child("membri_activi").child(str(membru.id)).set(date_membru)
    
    stats_ref = db.reference(f'servers/{interaction.guild_id}/statistica_raport')
    stats_data = stats_ref.get()

    if stats_data:
        
        m_id = str(membru.id) 
        nume_joc_admis = nume 
        
        
        if 'date' not in stats_data:
            stats_data['date'] = {}
            
        stats_data['date'][m_id] = {
            "nume": nume_joc_admis,
            "puncte": 0,
            "detalii": {}
        }
        
        
        stats_ref.child(f'date/{m_id}').set(stats_data['date'][m_id])
        
        
        await actualizeaza_tabel_mesaj(interaction.guild, stats_data)

    
    

    
    embed = discord.Embed(title="🎉 Admis cu succes!", color=discord.Color.green())
    embed.description = f"Deoarece **{nume}** a trecut testele a fost admis in factiune de catre liderul/co-liderul {interaction.user.mention}!"
    embed.set_thumbnail(url=membru.display_avatar.url)
    embed.add_field(name="Data", value=data_acum, inline=True)
    
    await interaction.followup.send(embed=embed)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucator adaugat:** {membru.mention} (numele de pe joc: {nume} & porecla noua {status_nume})\n"
    f"**Data admitere:** {data_acum}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "✅ A fost admis in factiune.", descriere_log, discord.Color.from_str("#FF3131"))

@bot.tree.command(name="respingere")
async def respinge(interaction: discord.Interaction, nume: str):
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "respingere"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucator respins:** {nume}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "👢 [TENTATIVA] A fost picat.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Acces refuzat.", ephemeral=True)
    
    nume_formatat = nume.replace(".", ",") 
    
    bot.get_server_ref(interaction.guild_id).child("jucatori_in_asteptare").child(nume_formatat.lower()).delete()
    await interaction.response.send_message(f"❌ Jucatorul **{nume}** a fost respins!")

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucator respins:** {nume}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "👢 A fost picat.", descriere_log, discord.Color.from_str("#FFF200"))



@bot.tree.command(name="admiteretest", description="Genereaza testul pentru un jucator")
async def test(interaction: discord.Interaction, nume_jucator: str):
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): return await interaction.response.send_message("❌ Bot neactivat.", ephemeral=True)
    
    status_functie = db.reference(f"servers/{interaction.guild_id}/functii/admiteretest").get()

    if status_functie is not True:
        return await interaction.followup.send(
            f"⚠️ Aceasta functie este dezactivata pentru acest server. Pentru mai multe informatii contacteaza pe <@{OWNER_ID}>.", 
            ephemeral=True
        )
    if not are_permisiune(interaction, sd, "admiteretest"): return await interaction.response.followup.send("❌ Acces refuzat.", ephemeral=True)

    if not are_permisiune(interaction, sd, "admiteretest"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Test pentru jucatorul:** {nume_jucator}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "📋 [TENTATIVA] A fost creat un test pentru un jucator.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Acces refuzat.", ephemeral=True)

    
    canal_configurat = sd.get("canal_test")
    if canal_configurat and interaction.channel_id != int(canal_configurat):
        return await interaction.followup.send(f"❌ Aceasta comanda poate fi folosita doar pe canalul <#{canal_configurat}>.", ephemeral=True)
    

    
    nume_key = nume_jucator.lower().replace(".", ",")
    
    
    jucatori = sd.get("jucatori_in_asteptare", {})
    status_functie2 = db.reference(f"servers/{interaction.guild_id}/functii/obligatie_addjucator_admitere").get()
    if status_functie2 == True:
        if nume_key not in jucatori:
            return await interaction.followup.send(
                f"❌ Jucătorul `{nume_jucator}` nu este în listă. (Căutat ca: `{nume_key}`). Folosește `/addjucator`.", 
                ephemeral=True
            )
    
    if jucatori[nume_key].get("test_sustinut"):
        return await interaction.followup.send(f"⚠️ Jucatorul **{jucatori[nume_key]['nume']}** a sustinut deja testul!", ephemeral=True)
    
    intrebari = sd.get("intrebari", [])
    nr = sd.get("numar_test", 5)

    sel = random.sample(intrebari, nr)
    
    emb = discord.Embed(
        title=f"📝 Test: {jucatori[nume_key]['nume']}", 
        color=0xffa500
    )

    
    parti_q = []
    parti_a = []
    current_q = ""
    current_a = ""

    for i, item in enumerate(sel, 1):
        linie_q = f"**{i}.** {item['q']}\n"
        linie_a = f"**{i}.** ||{item['a']}||\n"

        
        if len(current_q) + len(linie_q) > 1000 or len(current_a) + len(linie_a) > 1000:
            parti_q.append(current_q)
            parti_a.append(current_a)
            current_q = linie_q
            current_a = linie_a
        else:
            current_q += linie_q
            current_a += linie_a

    
    if current_q:
        parti_q.append(current_q)
        parti_a.append(current_a)

    
    for idx, text in enumerate(parti_q, 1):
        nume_f = "❓ Întrebări" if len(parti_q) == 1 else f"❓ Întrebări (Partea {idx})"
        emb.add_field(name=nume_f, value=text, inline=False)

    
    for idx, text in enumerate(parti_a, 1):
        nume_f = "✅ Răspunsuri" if len(parti_a) == 1 else f"✅ Răspunsuri (Partea {idx})"
        emb.add_field(name=nume_f, value=text, inline=False)

    emb.set_footer(text=f"Test generat de {interaction.user.display_name} • Total: {len(sel)} intrebari")
    await interaction.followup.send(embed=emb)
    

    try:
        
        ref_jucator = bot.get_server_ref(interaction.guild_id).child("jucatori_in_asteptare").child(nume_key)
        
        
        ref_jucator.update({
            "test_sustinut": True,
            "data_test": datetime.now(pytz.timezone('Europe/Bucharest')).strftime("%d/%m/%Y %H:%M"),
            "tester_id": str(interaction.user.id) 
        })
        
        
        bot.server_cache.pop(interaction.guild_id, None)
        
    except Exception as e:
        print(f"❌ Eroare la actualizarea statusului de test: {e}")

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Test pentru jucatorul:** {nume_jucator}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "📋 A fost creat un test pentru un jucator.", descriere_log, discord.Color.from_str("#FF3131"))

@bot.tree.command(name="listajucatoriacc", description="Vezi lista jucatorilor care trebuie sa sustina testul")
async def lista_p(interaction: discord.Interaction):
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): return await interaction.response.send_message("❌ Bot neactivat.", ephemeral=True)
    if not are_permisiune(interaction, sd, "listajucatoriacc"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "📜 [TENTATIVA] A verificat jucatori acceptati pentru teste.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Acces refuzat.", ephemeral=True)
    
    jucatori = sd.get("jucatori_in_asteptare", {})
    if not jucatori: return await interaction.followup.send("📋 Nu exista jucatori in asteptare.")
    
    embed = discord.Embed(title="📋 Jucatori acceptati pentru teste", color=discord.Color.blue())
    for key, data in jucatori.items():
        status = "✅ **Sustinut**" if data.get("test_sustinut") else "⏳ **In asteptare**"
        embed.add_field(
            name=f"Jucator: {data['nume']}",
            value=f"Tag: {data['tag']}(Nume discord: {data['namedis']})\nStatus: {status}\nData: {data['data_expirare']}",
            inline=False
        )
    await interaction.followup.send(embed=embed)
    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Grad:** {grad_staff}"
)

    await trimite_log_centralizat(interaction, "📜 A verificat jucatori acceptati pentru teste.", descriere_log, discord.Color.from_str("#2BFFB1"))

@bot.tree.command(name="sanctiune", description="Acorda FW, AV sau Amenda unui membru")
@app_commands.choices(tip=[
    app_commands.Choice(name="Faction Warning (FW)", value="FW"),
    app_commands.Choice(name="Avertisment Verbal (AV)", value="AV"),
    app_commands.Choice(name="Amenda", value="Amenda")
])
async def acorda_sanctiune(interaction: discord.Interaction, membru: discord.Member, tip: str, motiv: str, valoare_amenda: int = 0):
    await interaction.response.defer()
    
    
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat.", ephemeral=True)
    
    if not are_permisiune(interaction, sd, "sanctiune"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = f"**Utilizator:** {interaction.user.mention}\n**Membru vizat:** {membru.mention}\n**Tip:** {tip}\n**Grad:** {grad_staff}"
        await trimite_log_centralizat(interaction, "🔨 [TENTATIVA] Acordare sancțiune", descriere_log, discord.Color.red())
        return await interaction.followup.send("❌ Acces refuzat.", ephemeral=True)
    
    if str(membru.id) not in sd.get("membri_activi", {}):
        return await interaction.followup.send(f"❌ {membru.mention} nu este în facțiune!", ephemeral=True)

    tz_ro = pytz.timezone('Europe/Bucharest')
    data_acum = datetime.now(tz_ro)
    format_data = "%d/%m/%Y %H:%M"
    
    
    zile_expirare = {"FW": 7, "AV": 14, "Amenda": 3}
    data_expirare_finala = data_acum + timedelta(days=zile_expirare[tip])
    stack_msg = ""

    if tip == "Amenda":
        grad_staff = get_staff_rank(interaction, interaction.user)
                    
        descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip}\n"
                    f"**Motiv:** {motiv}\n"
                    f"**Grad:** {grad_staff}")
        await trimite_log_centralizat(interaction, "🔨 A primit amenda.", descriere_log, discord.Color.from_str("#FFF200"))

    
    
    if tip == "AV":
        toate_s = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).get() or {}
        av_existente = [k for k, v in toate_s.items() if v.get("tip") == "AV"]

        grad_staff = get_staff_rank(interaction, interaction.user)
                    
        descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip}\n"
                    f"**Motiv:** {motiv}\n"
                    f"**Grad:** {grad_staff}")
        await trimite_log_centralizat(interaction, "🔨 A primit AV.", descriere_log, discord.Color.from_str("#FFF200"))
        
        if len(av_existente) >= 1: 
            
            for key in av_existente:
                bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).child(key).delete()
            
            
            tip = "FW"
            motiv = f"Acumulare 2/2 AV | {motiv}"
            data_expirare_finala = data_acum + timedelta(days=7)
            stack_msg = "\n🔄 **Sistem Stacking:** Cele 2 AV-uri au fost transformate în **FW**!"

            grad_staff = get_staff_rank(interaction, interaction.user)
                    
            descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** FW\n"
                    f"**Motiv:** 2/2 AV-uri\n"
                    f"**Grad:** {grad_staff}")
            await trimite_log_centralizat(interaction, "🔨 Din 2 AV-uri sa transformat in FW.", descriere_log, discord.Color.from_str("#FFFFFF"))



    
    if tip == "FW":
        toate_s = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).get() or {}
        fw_uri = [v for v in toate_s.values() if v.get("tip") == "FW"]
        
        if fw_uri:
            
            ultimul_fw = sorted(fw_uri, key=lambda x: datetime.strptime(x['data_acordarii'], format_data))[-1]
            data_ultimul_acord = datetime.strptime(ultimul_fw['data_acordarii'], format_data).replace(tzinfo=tz_ro)
            data_ultimul_expir = datetime.strptime(ultimul_fw['data_expirarii'], format_data).replace(tzinfo=tz_ro)

            
            if (data_acum - data_ultimul_acord).days <= 3:
                data_expirare_finala = data_ultimul_expir + timedelta(days=7)
                stack_msg = "\n⚠️ **Sistem Stacking:** S-au adăugat 7 zile la data de expirare anterioară (FW primit la <3 zile)."
            
        grad_staff = get_staff_rank(interaction, interaction.user)
                    
        descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip}\n"
                    f"**Motiv:** {motiv}\n"
                    f"**Grad:** {grad_staff}")
        await trimite_log_centralizat(interaction, "🔨 A primit FW.", descriere_log, discord.Color.from_str("#FFF200"))

    
    data_str = data_acum.strftime(format_data)
    expirare_str = data_expirare_finala.strftime(format_data)

    sanctiune_payload = {
        "tip": tip,
        "motiv": motiv,
        "acordat_de": str(interaction.user),
        "data_acordarii": data_str,
        "data_expirarii": expirare_str,
        "status": "Activa" if tip != "Amenda" else "Neachitata"
    }
    if tip == "Amenda":
        sanctiune_payload["valoare_amenda"] = valoare_amenda

    
    ref_user_sanctiuni = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id))
    new_ref = ref_user_sanctiuni.push()
    s_id_unic = new_ref.key
    new_ref.set(sanctiune_payload)

    
    bot.get_server_ref(interaction.guild_id).child("istoric_sanctiuni").child(str(membru.id)).child(s_id_unic).set({
        "tip": tip,
        "motiv": motiv,
        "autor_nume": interaction.user.display_name,
        "autor_id": interaction.user.id,
        "data": data_str,
        "valoare": valoare_amenda if tip == "Amenda" else None
    })

    
    if tip == "FW":
        actuale = ref_user_sanctiuni.get() or {}
        count_fw = sum(1 for s in actuale.values() if s.get("tip") == "FW")
        if count_fw >= 3:
            
            for path in ["membri_activi", "sanctiuni", "invoiri"]:
                bot.get_server_ref(interaction.guild_id).child(path).child(str(membru.id)).delete()

    
            grad_staff = get_staff_rank(interaction, interaction.user)
                    
            descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** Uninvite cu 30FP\n"
                    f"**Motiv:** 3/3 FW-uri\n"
                    f"**Grad:** {grad_staff}")
            await trimite_log_centralizat(interaction, "🔨 A fost demis din factiune.", descriere_log, discord.Color.from_str("#FFF200"))
            return await interaction.followup.send(f"🚨 {membru.mention} a acumulat **3/3 FW** și a fost **demis automat** din facțiune!")
    
    try:
        await membru.send(f"⚠️ Ai primit **{tip}** pe {interaction.guild.name}!\nMotiv: {motiv}\nExpiră la: {expirare_str}")
        dm_status = "✅ DM trimis"
    except:
        dm_status = "❌ DM închis"

    await interaction.followup.send(f"✅ Sancțiune înregistrată!\nInformatii legate de sanctiune:\nMesaj trimis in privat?: {dm_status}\nExpiră la: `{expirare_str}`{stack_msg}\nTip sanctiune: {tip}\nValoare amenda(daca este cazul): {valoare_amenda}\nMotiv: {motiv}\nMembru: {membru}")
    
@bot.tree.command(name="history", description="Vezi istoricul de sanctiuni al unui membru")
async def history(interaction: discord.Interaction, membru: discord.Member):
    await interaction.response.defer(ephemeral=True)
    sd = bot.get_server_data(interaction.guild_id)
    
    istoric = sd.get("istoric_sanctiuni", {}).get(str(membru.id), {})
    
    if not istoric:
        return await interaction.followup.send(f"✅ {membru.mention} are un cazier curat.")

    embed = discord.Embed(title=f"📜 Istoric Sanctiuni - {membru.display_name}", color=discord.Color.orange())
    
    
    for s_id, data in list(istoric.items())[-10:]:
        tip = data.get("tip")
        motiv = data.get("motiv")
        data_s = data.get("data")
        autor = data.get("autor_nume")
        
        embed.add_field(
            name=f"{tip} - {data_s}",
            value=f"**Motiv:** {motiv}\n**Acordat de:** {autor}",
            inline=False
        )

    await interaction.followup.send(embed=embed)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul verificat:** {membru}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "⏳ A cautat un jucator.", descriere_log, discord.Color.from_str("#3498DB"))
    
class AmendaSelect(discord.ui.Select):
    def __init__(self, membru, sanctiuni, guild_id):
        options = []
        for s_id, s_info in sanctiuni.items():
            if s_info.get("tip") == "Amenda" and s_info.get("status") == "Neachitata":
                
                label = f"Amenda: {s_info['valoare']} - {s_info['motiv']}"
                options.append(discord.SelectOption(label=label[:100], value=s_id, description=f"Data: {s_info['data_acordarii']}"))

        super().__init__(placeholder="Alege amenda care a fost achitata...", options=options)
        self.membru = membru
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        
        ref = db.reference(f'servers/{self.guild_id}/sanctiuni/{self.membru.id}/{self.values[0]}')
        ref.update({"status": "Achitata"})
        
        await interaction.response.send_message(f"✅ Amenda selectata pentru {self.membru.mention} a fost marcata ca **Achitata**!", ephemeral=False)
        
        self.view.stop()

class AmendaView(discord.ui.View):
    def __init__(self, membru, sanctiuni, guild_id):
        super().__init__(timeout=60)
        self.add_item(AmendaSelect(membru, sanctiuni, guild_id))

@bot.tree.command(name="credits", description="Arata creditele")
async def credit(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Credite",
        description="Credite pentru administrarea si crearea botului",
        color=discord.Color.blue()
    )

    try:
        owner_user = await bot.fetch_user(OWNER_ID)
        owner_text = f"{owner_user.mention} ({owner_user.name})"
    except:
        owner_text = f"<@{OWNER_ID}> (ID: {OWNER_ID})"

    try:
        creator_user = await bot.fetch_user(804367268246585347)
        original = f"{creator_user.mention} ({creator_user.name})"
    except:
        original = "DevArchitect (devarchitect_)"

    embed.add_field(
        name="👑 Proprietar Actual Bot", 
        value=owner_text, 
        inline=True
    )
    embed.add_field(
        name="✍️ Creator Original Nucleu", 
        value=f"{original}\n*A dezvoltat arhitectura de bază (un proiect de aproape 7.000 de linii de cod).*", 
        inline=False
    )
    embed.add_field(
        name="📦 Proiect de Bază", 
        value="[Fork realizat după PCAF Open-Source](https://github.com/rusualingabriel/pcaf)\n*Prezenta instanță poate conține modificări aduse de proprietar.*", 
        inline=True
    )
    
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.set_footer(text="Toate drepturile asupra structurii logice inițiale aparțin creatorului.")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="achitare", description="Marcheaza o amenda ca fiind achitata")
async def achita_amenda(interaction: discord.Interaction, membru: discord.Member):
    sd = bot.get_server_data(interaction.guild_id)
    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    if not are_permisiune(interaction, sd, "achitare"): 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucatorul care ia fost achitata amenda:** {membru}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "🔓 [TENTATIVA] A scos o amenda(achitata) unui jucator din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.response.send_message("❌ Nu ai permisiunea de a marca amenzi achitate.", ephemeral=True)

    ref = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id))
    sanctiuni = ref.get()

    if not sanctiuni:
        return await interaction.response.send_message(f"❌ {membru.display_name} nu are nicio sanctiune.", ephemeral=True)

    
    amenzi_neachitate = {k: v for k, v in sanctiuni.items() if v.get("tip") == "Amenda" and v.get("status") == "Neachitata"}

    if not amenzi_neachitate:
        return await interaction.response.send_message(f"❌ {membru.display_name} nu are nicio amenda neachitata.", ephemeral=True)

    
    if len(amenzi_neachitate) == 1:
        s_id = list(amenzi_neachitate.keys())[0]
        ref.child(s_id).update({"status": "Achitata"})
        await interaction.response.send_message(f"✅ Singura amenda activa a lui {membru.mention} a fost marcata ca **Achitata**!")
    else:
        view = AmendaView(membru, amenzi_neachitate, interaction.guild_id)
        await interaction.response.send_message(f"🔎 {membru.mention} are mai multe amenzi. Alege-o pe cea achitata din meniul de mai jos:", view=view, ephemeral=True)
    
    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul care ia fost achitata amenda:** {membru}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "🔓 A scos o amenda(achitata) unui jucator din factiune.", descriere_log, discord.Color.from_str("#FFF200"))
    
@bot.tree.command(name="membri", description="Afiseaza lista tuturor membrilor din factiune")
async def lista_membri(interaction: discord.Interaction):
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id, force_refresh=True)
    membri = sd.get("membri_activi", {})

    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)

    
    membru_db = db.reference(f"servers/{interaction.guild_id}/membri_activi/{interaction.user.id}").get()

    
    if not membru_db:
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
            f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
            f"**Grad:** {grad_staff}"
        )
        await trimite_log_centralizat(interaction, "👥 [TENTATIVA] A verificat membri din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send(
            "❌ Nu esti membru activ pentru a folosi aceasta comanda!", 
            ephemeral=True
        )

    if not membri:
        return await interaction.followup.send("📭 Nu exista membri inregistrati.", ephemeral=True)

    id_rol_tester = str(sd.get("rol_tester", ""))
    
    
    lista_membri_pregatita = []
    for m_id, info in membri.items():
        discord_member = interaction.guild.get_member(int(m_id))
        is_tester = False
        if discord_member and id_rol_tester:
            is_tester = any(str(role.id) == id_rol_tester for role in discord_member.roles)
        lista_membri_pregatita.append({
            "id": m_id, 
            "nume": info.get('nume_joc', 'Necunoscut'),
            "rank": int(info.get('rank', 777)),
            "zile": int(info.get('zile_factiune', 777)),
            "is_staff": info.get('staff', False),
            "is_tester": is_tester
        })

    
    def calculeaza_prioritate(m):
        if m['rank'] == 7:
            return 1  
        elif m['rank'] == 6:
            return 2  
        elif m['is_tester']:
            return 3  
        else:
            return 15 - m['rank'] 

    
    membri_sortati = sorted(lista_membri_pregatita, key=lambda x: (calculeaza_prioritate(x), -x['zile']))

    
    embed = discord.Embed(title=f"👥 Membri Factiunii - {interaction.guild.name}", color=discord.Color.blue())

    linii = []
    for i, m in enumerate(membri_sortati, 1):
        
        prefix_emoji = ""
        if m['rank'] == 7:
            prefix_emoji = "👑 " 
        elif m['rank'] == 6:
            prefix_emoji = "💎 " 
        elif m['is_tester']:
            prefix_emoji = "🧪 " 
        elif m['is_staff']:
            prefix_emoji = "⭐ " 
        else:
            prefix_emoji = "👤 " 

        linii.append(f"{i}. {prefix_emoji}**{m['nume']}** (<@{m['id']}>) - Rank {m['rank']} - {m['zile']} zile")
    
    descriere = "\n".join(linii)
    
    
    embed.description = descriere[:4000] if descriere else "Niciun membru gasit."
    embed.set_footer(text="Legenda: 👑 Lider | 💎 Co-Lider | ⭐ Staff | 🧪 Tester | 👤 Membru")
    await interaction.followup.send(embed=embed)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Grad:** {grad_staff}"
    )
    await trimite_log_centralizat(interaction, "👥 A verificat membri din factiune.", descriere_log, discord.Color.from_str("#2BFFB1"))
    
@bot.tree.command(name="demite", description="Demite un jucător din facțiune")
@app_commands.describe(membru="ID-ul sau tag-ul jucătorului", motiv="Motivul demiterii", fp_custom="Suma FP manuală (opțional)")
async def demite(interaction: discord.Interaction, membru: str, motiv: str, fp_custom: int = None):
    await interaction.response.defer()
    
    guild_id = str(interaction.guild_id)
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Folosește `/activate`.", ephemeral=True)

    
    user_id_str = "".join(filter(str.isdigit, membru))
    if not user_id_str:
        return await interaction.followup.send("❌ Te rog introdu un ID valid sau dă tag.", ephemeral=True)
    
    user_id = int(user_id_str)

    
    if not are_permisiune(interaction, sd, "demite"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
            f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** {interaction.channel.mention}\n"
            f"**Jucătorul vizat:** <@{user_id}>\n"
            f"**Motiv:** {motiv}\n"
            f"**Grad Staff:** {grad_staff}"
        )
        await trimite_log_centralizat(interaction, "👢 [TENTATIVĂ] Demitere neautorizată", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai permisiunea de a folosi această comandă.", ephemeral=True)

    
    membri_activi = sd.get("membri_activi", {})
    membru_info = membri_activi.get(str(user_id))

    if not membru_info:
        return await interaction.followup.send("❌ Acest utilizator nu este înregistrat în baza de date a facțiunii.", ephemeral=True)

    
    invoiri_data = sd.get("invoiri", {}).get(str(user_id))
    if invoiri_data:
        tip_invoire = invoiri_data.get("tip", "").lower()
        expira_la = invoiri_data.get("expira_la")
        motiv_comparatie = motiv.lower()

        if tip_invoire == "normala" and "inactivitate" in motiv_comparatie:
            return await interaction.followup.send(f"🛡️ **Acțiune Blocată!** <@{user_id}> are învoire activă (Inactivitate) până la `{expira_la}`.")
        
        if tip_invoire in ["normala", "ms"] and "raport" in motiv_comparatie:
            return await interaction.followup.send(f"🛡️ **Acțiune Blocată!** <@{user_id}> are învoire activă (Raport) până la `{expira_la}`.")

    
    discord_membru = interaction.guild.get_member(user_id)
    este_pe_server = discord_membru is not None

    if not este_pe_server:
        try:
            discord_membru = await bot.fetch_user(user_id)
        except discord.NotFound:
            return await interaction.followup.send("❌ Acest ID nu aparține unui cont de Discord valid.", ephemeral=True)

    
    rank_vechi = membru_info.get("rank", 1)
    if este_pe_server:
        await update_member_nick(interaction, discord_membru, rank_vechi, status="demis")

    
    toate_sanctiunile = sd.get("sanctiuni", {}).get(str(user_id), {})
    fw_count = sum(1 for s in toate_sanctiunile.values() if s.get("tip") == "FW")
    zile = membru_info.get("zile_factiune", 0)

    if fp_custom is not None:
        fp_final = fp_custom
        metoda_calcul = f"Manual ({fp_custom} FP)"
    else:
        fp_din_fw = fw_count * 10
        fp_vechime = 30 if zile < 14 else 0
        fp_final = fp_din_fw + fp_vechime
        metoda_calcul = "Automat"

    
    ref = bot.get_server_ref(interaction.guild_id)
    target_id = str(user_id)
    ref.child("membri_activi").child(target_id).delete()
    ref.child("sanctiuni").child(target_id).delete()
    ref.child("invoiri").child(target_id).delete()
    ref.child("istoric_sanctiuni").child(target_id).delete()
    ref.child("ultima_sansa").child(target_id).delete()
    
    
    stats_ref = db.reference(f'servers/{interaction.guild_id}/statistica_raport')
    stats_data = stats_ref.get()

    if stats_data and str(target_id) in stats_data.get('date', {}):
        
        del stats_data['date'][str(target_id)]
        
        
        stats_ref.child(f'date/{target_id}').delete()
        
        
        await actualizeaza_tabel_mesaj(interaction.guild, stats_data)

    
    dm_status = "❌ DM eșuat (nu se află pe server)"
    if este_pe_server:
        
        id_roluri_de_scos = set()
        config_adm = sd.get("config_admitere", {})
        
        
        
        for r_id in config_adm.get("roles_add", []): 
            try: id_roluri_de_scos.add(int(r_id))
            except: continue
        
        
        
        config_rankuri = sd.get("config_rank_roluri", {})
        
        
        if isinstance(config_rankuri, list):
            
            for rank_data in config_rankuri:
                if isinstance(rank_data, dict):
                    for r_id in rank_data.get("add", []):
                        try: id_roluri_de_scos.add(int(r_id))
                        except: continue
        elif isinstance(config_rankuri, dict):
            
            for r_num in ["1", "2", "3", "4", "5"]:
                rank_data = config_rankuri.get(r_num, {})
                if isinstance(rank_data, dict):
                    for r_id in rank_data.get("add", []):
                        try: id_roluri_de_scos.add(int(r_id))
                        except: continue

        
        setari_gen = sd.get("setari", {})
        for k in ["rol_tester", "rol_colider", "rol_lider"]:
            val = setari_gen.get(k)
            if val: 
                try: id_roluri_de_scos.add(int(val))
                except: continue

        print(f"DEBUG DEMITE: ID-uri identificate pentru scoatere: {id_roluri_de_scos}")
        
        roluri_de_sters = [r for r in discord_membru.roles if r.id in id_roluri_de_scos]
        print(f"DEBUG DEMITE: Roluri găsite pe membru: {[r.name for r in roluri_de_sters]}")
        
        try:
            if roluri_de_sters:
                
                await discord_membru.remove_roles(*roluri_de_sters, reason=f"Demis de {interaction.user} | Motiv: {motiv}")
                print(f"✅ Am scos {len(roluri_de_sters)} roluri de la {discord_membru.name}")
            
            
            adm_remove_list = config_adm.get("roles_remove", [])
            if adm_remove_list:
                rol_civil = interaction.guild.get_role(int(adm_remove_list[0]))
                if rol_civil: 
                    await discord_membru.add_roles(rol_civil, reason="Resetare la Civil")
        except Exception as e: 
            print(f"❌ Eroare la modificarea rolurilor: {e}")

        
        try:
            embed_dm = discord.Embed(title="⚠️ Ai primit uninvite!", color=discord.Color.red())
            embed_dm.add_field(name="Facțiune", value=interaction.guild.name)
            embed_dm.add_field(name="FP", value=f"{fp_final} FP")
            embed_dm.add_field(name="Motiv", value=motiv)
            embed_dm.add_field(name="De către", value=interaction.user.mention)
            await discord_membru.send(embed=embed_dm)
            dm_status = "✅ DM trimis"
        except: dm_status = "❌ DM închis"

    
    embed_fin = discord.Embed(title="🚫 Membru Demis", color=discord.Color.dark_red())
    embed_fin.add_field(name="Membru", value=f"<@{user_id}> (`{membru_info.get('nume_joc', 'Necunoscut')}`)", inline=True)
    embed_fin.add_field(name="Vechime", value=f"{zile} zile", inline=True)
    embed_fin.add_field(name="FP", value=f"**{fp_final} FP**", inline=False)
    embed_fin.add_field(name="Motiv", inline=False, value=motiv)
    embed_fin.set_footer(text=f"DM: {dm_status} | Calcul: {metoda_calcul}")

    await interaction.followup.send(embed=embed_fin)

    
    grad_staff = get_staff_rank(interaction, interaction.user)
    log_final = (
        f"**Staff:** {interaction.user.mention}\n"
        f"**Jucător:** <@{user_id}>\n"
        f"**FP:** {fp_final}\n"
        f"**Motiv:** {motiv}\n"
        f"**Grad:** {grad_staff}"
    )
    await trimite_log_centralizat(interaction, "👢 Jucător demis din facțiune", log_final, discord.Color.gold())
    
class RankRoleSettingsView(discord.ui.View):
    def __init__(self, rank):
        super().__init__(timeout=120)
        self.rank = rank
        self.roles_to_add = []
        self.roles_to_remove = []

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Roluri de ADAUGAT la acest rank...", min_values=0, max_values=5)
    async def select_add(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.roles_to_add = [str(r.id) for r in select.values]
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Roluri de SCOS la acest rank...", min_values=0, max_values=5)
    async def select_remove(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.roles_to_remove = [str(r.id) for r in select.values]
        await interaction.response.defer()

    @discord.ui.button(label="Salveaza Configuratia", style=discord.ButtonStyle.success, emoji="✅")
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = {
            "add": self.roles_to_add,
            "remove": self.roles_to_remove
        }
        db.reference(f'servers/{interaction.guild_id}/config_rank_roluri/{self.rank}').set(data)
        await interaction.followup.send(f"✅ Configuratia pentru **Rank {self.rank}** a fost salvata!", ephemeral=True)

@bot.tree.command(name="rankup", description="Acorda rank up, actualizeaza rolurile si nickname-ul conform setarilor")
@app_commands.describe(membru="Membrul care primeste avansarea")
async def rankup(interaction: discord.Interaction, membru: discord.Member):
    await interaction.response.defer()
    
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    if not are_permisiune(interaction, sd, "rankup"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
            f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
            f"**Jucatorul vizat:** {membru}\n"
            f"**Grad:** {grad_staff}"
        )
        await trimite_log_centralizat(interaction, "⬆️ [TENTATIVA] Rank up neautorizat.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai permisiunea de a folosi aceasta comanda.", ephemeral=True)
    
    
    membru_info = sd.get("membri_activi", {}).get(str(membru.id))
    if not membru_info:
        return await interaction.followup.send("❌ Acest membru nu figureaza ca fiind activ in baza de date.", ephemeral=True)

    rank_actual = int(membru_info.get("rank", 1))
    if rank_actual >= 5:
        return await interaction.followup.send(f"❌ {membru.mention} are deja rank-ul maxim (5).", ephemeral=True)

    if rank_actual < 5:
        next_rank = rank_actual + 1

        
        
        praguri_cumulativ = {2: 14, 3: 28, 4: 49, 5: 70}
        zile_baza_necesare = praguri_cumulativ.get(next_rank, 14)

        
        sanctiuni_active = sd.get("sanctiuni", {}).get(str(membru.id), {})
        fw_active = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "FW")
        
        
        
        zile_necesare = zile_baza_necesare + (fw_active * 7)

        
        zile_totale_membru = int(membru_info.get("zile_factiune", 0))

        
        if zile_totale_membru < zile_necesare:
            detalii = [f"Baza Rank {next_rank}: {zile_baza_necesare} zile"]
            if fw_active > 0: 
                detalii.append(f"FW Active: +{fw_active * 7} zile")
            
            return await interaction.followup.send(
                f"⏳ {membru.mention} nu are destule zile pentru Rank {next_rank}!\n"
                f"📈 Progres: **{zile_totale_membru}/{zile_necesare}** zile totale.\n"
                f"ℹ️ **Calcul:** {' + '.join(detalii)}."
            )

        
        data_acum = datetime.now(pytz.timezone('Europe/Bucharest')).strftime("%d/%m/%Y %H:%M")
        db.reference(f'servers/{interaction.guild_id}/membri_activi/{membru.id}').update({
            "rank": next_rank,
            "data_ultima_avansare": data_acum
        })

        
        log_roluri = ""
        config_generala = sd.get("config_rank_roluri", {})
        config_rank = {}

        if isinstance(config_generala, list):
            if len(config_generala) > next_rank:
                config_rank = config_generala[next_rank]
        elif isinstance(config_generala, dict):
            config_rank = config_generala.get(str(next_rank), {})

        if not isinstance(config_rank, dict): config_rank = {}

        
        role_ids_to_remove = config_rank.get("remove", [])
        if isinstance(role_ids_to_remove, list):
            for rid in role_ids_to_remove:
                r_obj = interaction.guild.get_role(int(rid))
                if r_obj:
                    try: 
                        await membru.remove_roles(r_obj)
                        log_roluri += f"➖ {r_obj.name} "
                    except: pass

        
        role_ids_to_add = config_rank.get("add", [])
        if isinstance(role_ids_to_add, list):
            for rid in role_ids_to_add:
                r_obj = interaction.guild.get_role(int(rid))
                if r_obj:
                    try: 
                        await membru.add_roles(r_obj)
                        log_roluri += f"➕ {r_obj.name} "
                    except: pass
        
        if not log_roluri: log_roluri = "Nicio modificare de roluri."

        
        try:
            await update_member_nick(interaction, membru, next_rank, status="activ")
            status_nick = "✅ Actualizat"
        except: status_nick = "⚠️ Eroare/Permisiuni"

        embed = discord.Embed(title="📈 Avansare Membru", color=discord.Color.blue())
        embed.set_thumbnail(url=membru.display_avatar.url)
        embed.add_field(name="Membru", value=membru.mention, inline=True)
        embed.add_field(name="Grad Nou", value=f"Rank {next_rank}", inline=True)
        embed.add_field(name="Nickname", value=status_nick, inline=True)
        embed.add_field(name="Modificari Roluri", value=log_roluri, inline=False)
        embed.set_footer(text=f"Data: {data_acum}")

        await interaction.followup.send(embed=embed)


        
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
            f"**Utilizator:** {interaction.user.mention}\n"
            f"**Membru avansat:** {membru.mention} (`{membru.id}`)\n"
            f"**Rank primit:** Rank {next_rank}\n"
            f"**Grad:** {grad_staff}"
        )
        await trimite_log_centralizat(interaction, "⬆️ Rank Up acordat cu succes.", descriere_log, discord.Color.green())

@bot.tree.command(name="finfo", description="Profil complet: Date active din baza + Istoric din Registru")
async def finfo(interaction: discord.Interaction, membru: discord.Member = None):
    await interaction.response.defer()
    membru = membru or interaction.user
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    if not are_permisiune(interaction, sd, "finfo") and interaction.user.id != membru.id: 
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucatorul pe care a fost folosita comanda:** {membru}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "👤 [TENTATIVA] A fost verificat informatiile unui jucator din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Acces refuzat.", ephemeral=True)
    
    membru_info = sd.get("membri_activi", {}).get(str(membru.id))
    if not membru_info:
        return await interaction.followup.send(f"❌ {membru.mention} nu este membru activ.")
    
    if interaction.guild_id == 795348393005416489 or interaction.guild_id == 1256583675739504711:
    
        sanctiuni_active = sd.get("sanctiuni", {}).get(str(membru.id), {})
        sanctiuni_istorie = sd.get("istoric_sanctiuni", {}).get(str(membru.id), {})
        fw_count = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "FW")
        av_count = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "AV")
        fw_count_istorie = sum(1 for s in sanctiuni_istorie.values() if s.get("tip") == "FW")
    
        
        istoric_dict = sd.get("istoric_sanctiuni", {}).get(str(membru.id), {})
        istoric_recent = []

    
        invoiri_data = sd.get("invoiri", {}).get(str(membru.id))
        status_invoire = "❌ Fara invoire activa"
        
        if invoiri_data and isinstance(invoiri_data, dict):
            try:
                
                
                sfarsit_raw = invoiri_data.get("expira_la")

                
                if sfarsit_raw:
                    data_azi = datetime.now(pytz.timezone('Europe/Bucharest')).date()
                    
                    
                    
                    
                    
                    
                    
                    
                    if invoiri_data.get("tip", "").lower() == "normala":
                        status_invoire = f"✅ **Activa** (Pana pe {sfarsit_raw})"
                    else:
                        status_invoire = f"✅ **Activa(invoire MS)** (Pana pe {sfarsit_raw})"
            except Exception as e:
                
                status_invoire = f"⚠️ Format data invalid ({e})"
        

        if istoric_dict:
            
            
            lista_sanctiuni = list(istoric_dict.values())
            
            
            try:
                lista_sanctiuni.sort(key=lambda x: datetime.strptime(x.get('data', '01/01/2000 00:00'), "%d/%m/%Y %H:%M"), reverse=True)
            except:
                pass 

            
            for s in lista_sanctiuni[:5]:
                tip = s.get("tip", "Sanctiune")
                motiv = s.get("motiv", "Fara motiv")
                data_f = s.get("data", "N/A").split()[0] 
                
                
                if "FW" in tip.upper(): emoji = "🔴"
                elif "AV" in tip.upper(): emoji = "🟡"
                elif "AMENDA" in tip.upper() or "AMENDA" in tip.upper(): emoji = "💸"
                else: emoji = "⚪"
                
                istoric_recent.append(f"{emoji} **{tip}** - {motiv} *({data_f})*")
        else:
            istoric_recent = ["✅ Membrul nu are sanctiuni in istoric."]

        
        if not istoric_recent:
            istoric_recent = ["✅ Fara sanctiuni recente."]

        
        rank_actual = membru_info.get("rank", 1)
        zile_in_factiune = membru_info.get("zile_factiune", 0)
        status_rankup = "✅ Rank Maxim"
        if rank_actual < 5:
            zile_baza = {2: 14, 3: 14, 4: 21, 5: 21}[rank_actual + 1]
            zile_necesare = zile_baza + (fw_count_istorie * 7)
            
            
            #data_ref_str = membru_info.get("data_ultima_avansare") or membru_info.get("data_admitere")
            
            
            
            
            if zile_in_factiune >= zile_necesare:
                status_rankup = "🟢 **Eligibil pentru Rank Up!**"
            else:
                status_rankup = f"⏳ Eligibil in {zile_necesare - zile_in_factiune} zile"

        
        embed = discord.Embed(title=f"Profil Factiune: {membru_info.get('nume_joc', membru.display_name)}", color=0x2b2d31)
        embed.set_thumbnail(url=membru.display_avatar.url)
        
        embed.add_field(name="📊 Info Generale", 
                        value=f"**Rank:** {rank_actual}\n**Zile:** {membru_info.get('zile_factiune', 0)}\n**Admis pe:** {membru_info['data_admitere'].split()[0]}", 
                        inline=True)
        
        embed.add_field(name="📅 Invoire", value=status_invoire, inline=True)
        
        embed.add_field(name="⚖️ Sanctiuni Active", 
                        value=f"**FW:** {fw_count}/3\n**AV:** {av_count}/2", 
                        inline=True)

        embed.add_field(name="📈 Status Rank Up", value=status_rankup, inline=False)

        text_istoric = "\n".join(istoric_recent) if istoric_recent else "*Nicio sanctiune gasita in registru.*"
        embed.add_field(name="📜 Istoric Recent (din Registru)", value=text_istoric, inline=False)
        
        embed.set_footer(text=f"ID Discord: {membru.id}")
        await interaction.followup.send(embed=embed)
    else:
        sanctiuni_active = sd.get("sanctiuni", {}).get(str(membru.id), {})
        sanctiuni_istorie = sd.get("istoric_sanctiuni", {}).get(str(membru.id), {})
        fw_count = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "FW")
        av_count = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "AV")
        fw_count_istorie = sum(1 for s in sanctiuni_istorie.values() if s.get("tip") == "FW")
    
        
        istoric_dict = sd.get("istoric_sanctiuni", {}).get(str(membru.id), {})
        istoric_recent = []

    
        invoiri_data = sd.get("invoiri", {}).get(str(membru.id))
        status_invoire = "❌ Fara invoire activa"
        
        if invoiri_data and isinstance(invoiri_data, dict):
            try:
                
                
                sfarsit_raw = invoiri_data.get("expira_la")

                
                if sfarsit_raw:
                    data_azi = datetime.now(pytz.timezone('Europe/Bucharest')).date()
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    status_invoire = f"✅ **Activa** (Pana pe {sfarsit_raw})"
            except Exception as e:
                
                status_invoire = f"⚠️ Format data invalid ({e})"
        

        if istoric_dict:
            
            
            lista_sanctiuni = list(istoric_dict.values())
            
            
            try:
                lista_sanctiuni.sort(key=lambda x: datetime.strptime(x.get('data', '01/01/2000 00:00'), "%d/%m/%Y %H:%M"), reverse=True)
            except:
                pass 

            
            for s in lista_sanctiuni[:5]:
                tip = s.get("tip", "Sanctiune")
                motiv = s.get("motiv", "Fara motiv")
                data_f = s.get("data", "N/A").split()[0] 
                
                
                if "FW" in tip.upper(): emoji = "🔴"
                elif "AV" in tip.upper(): emoji = "🟡"
                elif "AMENDA" in tip.upper() or "AMENDA" in tip.upper(): emoji = "💸"
                else: emoji = "⚪"
                
                istoric_recent.append(f"{emoji} **{tip}** - {motiv} *({data_f})*")
        else:
            istoric_recent = ["✅ Membrul nu are sanctiuni in istoric."]

        
        if not istoric_recent:
            istoric_recent = ["✅ Fara sanctiuni recente."]

        
        rank_actual = membru_info.get("rank", 1)
        status_rankup = "✅ Rank Maxim"
        if rank_actual < 5:
            zile_baza = {2: 14, 3: 14, 4: 21, 5: 21}[rank_actual + 1]
            zile_necesare = zile_baza + (fw_count_istorie * 7)
            
            
            data_ref_str = membru_info.get("data_ultima_avansare") or membru_info.get("data_admitere")
            data_ref = datetime.strptime(data_ref_str.split()[0], "%d/%m/%Y").date()
            data_azi = datetime.now(pytz.timezone('Europe/Bucharest')).date()
            zile_trecute = (data_azi - data_ref).days
            
            if zile_trecute >= zile_necesare:
                status_rankup = "🟢 **Eligibil pentru Rank Up!**"
            else:
                status_rankup = f"⏳ Eligibil in {zile_necesare - zile_trecute} zile"

        
        embed = discord.Embed(title=f"Profil Factiune: {membru_info.get('nume_joc', membru.display_name)}", color=0x2b2d31)
        embed.set_thumbnail(url=membru.display_avatar.url)
        
        embed.add_field(name="📊 Info Generale", 
                        value=f"**Rank:** {rank_actual}\n**Zile:** {membru_info.get('zile_factiune', 0)}\n**Admis pe:** {membru_info['data_admitere'].split()[0]}", 
                        inline=True)
        
        embed.add_field(name="📅 Invoire", value=status_invoire, inline=True)
        
        embed.add_field(name="⚖️ Sanctiuni Active", 
                        value=f"**FW:** {fw_count}/3\n**AV:** {av_count}/2", 
                        inline=True)

        embed.add_field(name="📈 Status Rank Up", value=status_rankup, inline=False)

        text_istoric = "\n".join(istoric_recent) if istoric_recent else "*Nicio sanctiune gasita in registru.*"
        embed.add_field(name="📜 Istoric Recent (din Registru)", value=text_istoric, inline=False)
        
        embed.set_footer(text=f"ID Discord: {membru.id}")
        await interaction.followup.send(embed=embed)
    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul pe care a fost folosita comanda:** {membru}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "👤 A fost verificat informatiile unui jucator din factiune.", descriere_log, discord.Color.from_str("#3498DB"))
    
@bot.tree.command(
    name="debug_rank", 
    description="[STAFF] Calcul cumulativ zile necesare până la un rank specific",
    guild=GUILD_STAFF
)
@app_commands.describe(server_id="ID-ul serverului", membru_id="ID-ul jucătorului", rank_tinta="Rank-ul la care vrei să ajungă (2-5)")
async def debug_rank(interaction: discord.Interaction, server_id: str, membru_id: str, rank_tinta: int):
    await interaction.response.defer()
    
    user_id_clean = "".join(filter(str.isdigit, membru_id))
    sd = bot.get_server_data(server_id)
    
    if not sd or not sd.get("activat", False):
        return await interaction.followup.send(f"❌ Serverul `{server_id}` nu este în bază.")

    membru_info = sd.get("membri_activi", {}).get(user_id_clean)
    if not membru_info:
        return await interaction.followup.send(f"❌ Jucătorul `{user_id_clean}` nu este membru activ.")

    rank_actual = membru_info.get("rank", 1)
    zile_factiune = membru_info.get("zile_factiune", 0)
    
    if rank_tinta <= rank_actual:
        return await interaction.followup.send(f"⚠️ Jucătorul are deja Rank {rank_actual}. Alege un rank mai mare decât cel curent.")

    
    zile_config = {2: 14, 3: 14, 4: 21, 5: 21}
    
    
    total_zile_baza = 0
    explicatie_trepte = ""
    
    for r in range(rank_actual + 1, rank_tinta + 1):
        zile_etapa = zile_config.get(r, 14)
        total_zile_baza += zile_etapa
        explicatie_trepte += f"▫️ Rank {r-1} ➔ {r}: `{zile_etapa} zile`\n"

    
    istoric = sd.get("istoric_sanctiuni", {}).get(user_id_clean, {})
    fw_istoric = sum(1 for s in istoric.values() if s.get("tip") == "FW")
    penalizare_fw = fw_istoric * 7

    
    total_necesar_absolut = total_zile_baza + penalizare_fw
    restante = total_necesar_absolut - zile_factiune

    
    embed = discord.Embed(
        title=f"🔍 Debug Rank Cumulativ: {membru_info.get('nume_joc', user_id_clean)}",
        color=discord.Color.gold()
    )
    
    descriere = (
        f"**De la Rank {rank_actual} până la Rank {rank_tinta}**\n\n"
        f"**Etape zile de bază:**\n{explicatie_trepte}"
        f"➕ Penalizare FW ({fw_istoric} buc): `+{penalizare_fw} zile`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 **Total necesar de la 0:** `{total_necesar_absolut} zile`\n"
        f"📅 **Zile acumulate deja:** `{zile_factiune} zile`"
    )
    embed.description = descriere

    if restante <= 0:
        embed.add_field(name="✅ Status", value=f"**Eligibil pentru Rank {rank_tinta}!** (Are destule zile de la intrare)")
    else:
        embed.add_field(name="⏳ Status", value=f"Mai are nevoie de **{restante} zile** în total pentru a atinge Rank {rank_tinta}.")

    embed.set_footer(text=f"Server: {server_id} | Calcul bazat pe istoricul complet")
    await interaction.followup.send(embed=embed)
    
@bot.tree.command(name="invoirems", description="Adauga o invoire MS (protectie doar pentru raport)")
async def invoirems(interaction: discord.Interaction, membru: discord.Member, zile: int, motiv: str):
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    if not are_permisiune(interaction, sd, "invoirems"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucatorul invoit:** {membru}\n"
        f"**Expira invoirea pe data de:** {data_expirare}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "💬📈 [TENTATIVA] A fost invoitms un jucator din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai acces.")

    tz_ro = pytz.timezone('Europe/Bucharest')
    data_expirare = datetime.now(tz_ro) + timedelta(days=zile)
    expirare_str = data_expirare.strftime("%d/%m/%Y %H:%M")
    
    invoire_data = {
        "tip": "ms",
        "motiv": motiv,
        "expira_la": expirare_str,
        "autor": str(interaction.user)
    }
    
    db.reference(f'servers/{interaction.guild_id}/invoiri/{membru.id}').set(invoire_data)
    
    await interaction.followup.send(f"✅ **Invoire MS** activata pentru {membru.mention} pana la `{expirare_str}`.")

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul invoit:** {membru}\n"
    f"**Expira invoirea pe data de:** {data_expirare}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "💬 A fost invoitms un jucator din factiune.", descriere_log, discord.Color.from_str("#FFF200"))
    
@bot.tree.command(name="invoire", description="Adauga o invoire (protectie raport si inactivitate)")
async def invoire(interaction: discord.Interaction, membru: discord.Member, zile: int, motiv: str):
    await interaction.response.defer()
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    if not are_permisiune(interaction, sd, "invoire"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Jucatorul invoit:** {membru}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "✉️ [TENTATIVA] A fost invoit un jucator din factiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai acces.")

    tz_ro = pytz.timezone('Europe/Bucharest')
    data_start = datetime.now(tz_ro)
    data_expirare = data_start + timedelta(days=zile)
    
    expirare_str = data_expirare.strftime("%d/%m/%Y %H:%M")
    
    invoire_data = {
        "tip": "normala",
        "motiv": motiv,
        "expira_la": expirare_str,
        "autor": str(interaction.user)
    }

    ref_membru = bot.get_server_ref(interaction.guild_id).child("membri_activi").child(str(membru.id))
    date_actuale = ref_membru.get()

    
    zile_vechi = date_actuale.get("zile_invoire", 0)
    ref_membru.update({"zile_invoire": int(zile_vechi or 0) + zile})
    
    
    db.reference(f'servers/{interaction.guild_id}/invoiri/{membru.id}').set(invoire_data)

    
    embed = discord.Embed(title="📝 Invoire Noua", color=discord.Color.green())
    embed.add_field(name="Membru", value=membru.mention, inline=True)
    embed.add_field(name="Durata", value=f"{zile} zile", inline=True)
    embed.add_field(name="Expira la", value=expirare_str, inline=False)
    embed.add_field(name="Motiv", value=motiv, inline=False)
    
    await interaction.followup.send(embed=embed)

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Jucatorul invoit:** {membru}\n"
    f"**Expira invoirea pe data de:** {data_expirare}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "✉️ A fost invoit un jucator din factiune.", descriere_log, discord.Color.from_str("#FFF200"))



class ChannelSelector(discord.ui.ChannelSelect):
    def __init__(self, label, key):
        super().__init__(placeholder=label, channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        canal_ales = self.values[0]
        db.reference(f'servers/{interaction.guild_id}/{self.key}').set(str(canal_ales.id))
        await interaction.response.send_message(f"✅ Canalul pentru **{self.key.replace('_', ' ')}** a fost setat pe {canal_ales.mention}", ephemeral=True)

class RankRoleSelector(discord.ui.RoleSelect):
    def __init__(self, rank, tip):
        
        super().__init__(
            placeholder=f"Selecteaza roluri de {tip.upper()} pentru Rank {rank}",
            min_values=1,
            max_values=10
        )
        self.rank = rank
        self.tip = tip

    async def callback(self, interaction: discord.Interaction):
        
        role_ids = [str(role.id) for role in self.values]
        
        
        ref = db.reference(f'servers/{interaction.guild_id}/config_rank_roluri/{self.rank}/{self.tip}')
        ref.set(role_ids)
        
        await interaction.response.send_message(
            f"✅ Rank **{self.rank}**: Rolurile de **{self.tip.upper()}** au fost actualizate!", 
            ephemeral=True
        )



class RankPickerView(discord.ui.View):
    def __init__(self, rank_ales):
        super().__init__(timeout=120)
        
        self.add_item(RankRoleSelector(rank=rank_ales, tip="add"))
        self.add_item(RankRoleSelector(rank=rank_ales, tip="remove"))

class RankChoiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Configurare Rank 2", value="2", emoji="2️⃣"),
            discord.SelectOption(label="Configurare Rank 3", value="3", emoji="3️⃣"),
            discord.SelectOption(label="Configurare Rank 4", value="4", emoji="4️⃣"),
            discord.SelectOption(label="Configurare Rank 5", value="5", emoji="5️⃣"),
            discord.SelectOption(label="Configurare Rank 6", value="6", emoji="6️⃣"),
        ]
        super().__init__(placeholder="Pentru ce rank vrei sa setezi rolurile?", options=options)

    async def callback(self, interaction: discord.Interaction):
        rank_ales = self.values[0]
        
        view = RankPickerView(rank_ales)
        await interaction.response.send_message(
            f"🎭 **Configurare Roluri - Rank {rank_ales}**\n"
            "Alege din listele de mai jos ce roluri se dau si ce roluri se scot:",
            view=view,
            ephemeral=True
        )

class RoleSelector(discord.ui.RoleSelect):
    def __init__(self, label, key):
        
        
        super().__init__(placeholder=label, min_values=1, max_values=1)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        
        rol_ales = self.values[0]
        
        
        ref = db.reference(f'servers/{interaction.guild_id}/{self.key}')
        ref.set(str(rol_ales.id))
        
        
        await interaction.response.send_message(
            f"✅ Rolul pentru **{self.key.replace('_', ' ')}** a fost setat pe: **{rol_ales.name}**", 
            ephemeral=True
        )



class NumeRankDenumiriModal(discord.ui.Modal, title="Denumiri Rank 1-5"):
    r1 = discord.ui.TextInput(label="Nume Rank 1", placeholder="Ex: Voluntar", required=True)
    r2 = discord.ui.TextInput(label="Nume Rank 2", placeholder="Ex: Membru", required=True)
    r3 = discord.ui.TextInput(label="Nume Rank 3", placeholder="Ex: Veteran", required=True)
    r4 = discord.ui.TextInput(label="Nume Rank 4", placeholder="Ex: Agent", required=True)
    r5 = discord.ui.TextInput(label="Nume Rank 5", placeholder="Ex: Coordonator", required=True)
    

    async def on_submit(self, interaction: discord.Interaction):
        ref = db.reference(f'servers/{interaction.guild_id}/setari_nume/rankuri')
        ref.set({
            "1": self.r1.value, "2": self.r2.value, "3": self.r3.value,
            "4": self.r4.value, "5": self.r5.value
        })
        await interaction.response.send_message("✅ Denumirile rank-urilor au fost salvate!", ephemeral=True)


class FormatNumeModal(discord.ui.Modal, title="Configurare Format Nickname"):
    format_nume = discord.ui.TextInput(
        label="Format (Ex: {nume} - {rank_nume})", 
        placeholder="{nume} - {rank_nume}",
        default="{nume} - {rank_nume}",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        db.reference(f'servers/{interaction.guild_id}/setari_nume/format').set(self.format_nume.value)
        await interaction.response.send_message(f"✅ Format setat: `{self.format_nume.value}`", ephemeral=True)


class AdmitereModal(discord.ui.Modal, title="Configurare Mesaje Admitere"):
    msg_welcome = discord.ui.TextInput(
        label="Mesaj Bun Venit", 
        style=discord.TextStyle.paragraph,
        placeholder="Mesajul trimis cand cineva este admis...",
        required=True
    )
    tag_lider = discord.ui.TextInput(label="Tag Lider la Admitere? (Da/Nu)", placeholder="Da", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        db.reference(f'servers/{interaction.guild_id}/setari_admitere_detalii').set({
            "mesaj": self.msg_welcome.value,
            "tag": self.tag_lider.value.lower() == "da"
        })
        await interaction.response.send_message("✅ Setarile de admitere au fost actualizate!", ephemeral=True)



class AdmitereChannelSelector(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Alege canalul pentru /admiteretest",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        canal_id = str(self.values[0].id)
        db.reference(f'servers/{interaction.guild_id}/canal_test').set(canal_id)
        
        await interaction.response.send_message(f"✅ Comanda `/admiteretest` poate fi folosita acum pe {self.values[0].mention}.", ephemeral=True)

class AdmitereSettingsModal(discord.ui.Modal, title="Configurare Test Admitere"):
    nr_intrebari = discord.ui.TextInput(
        label="Numar de intrebari per test",
        placeholder="Ex: 10",
        min_length=1,
        max_length=2,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not self.nr_intrebari.value.isdigit():
            return await interaction.response.send_message("❌ Te rog introdu un numar valid!", ephemeral=True)
        
        nr = int(self.nr_intrebari.value)
        db.reference(f'servers/{interaction.guild_id}/numar_test').set(nr)
        
        await interaction.response.send_message(f"✅ Fiecare test va avea acum **{nr}** intrebari.", ephemeral=True)

class ConfigView(discord.ui.View):
    def __init__(self, sd):
        super().__init__(timeout=180)
        self.sd = sd

    @discord.ui.select(
        placeholder="Alege categoria pe care vrei sa o configurezi...",
        options=[
    discord.SelectOption(label="Canale", value="canale", emoji="🔗"),
    discord.SelectOption(label="Roluri Conducere", value="staff", emoji="🎖️"),
    discord.SelectOption(label="Denumiri Rank-uri", value="nume_ranks", emoji="🏷️"),
    discord.SelectOption(label="Format Nickname", value="format_nick", emoji="👤"), 
    discord.SelectOption(label="Admitere", value="admitere", emoji="📝"),
    discord.SelectOption(
    label="Configurare Roluri Rankup", 
    value="setup_roles_logic", 
    emoji="🎭")
]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.sd = bot.get_server_data(interaction.guild_id, force_refresh=True)
        categoria = select.values[0]

        
        if categoria == "canale":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                f"**Categoria selectata:** {categoria}\n"
                f"**Grad:** {grad_staff}"
            )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare a serverului.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Nu ai permisiunea `setari` in matrice.", ephemeral=True)
            
            view = discord.ui.View()
            view.add_item(ChannelSelector("Selecteaza Canal Anunturi Bot", "canal_anunturi"))
            view.add_item(ChannelSelector("Selecteaza Canal Logs Server", "canal_logsserver"))
            view.add_item(ChannelSelector("Selecteaza Canal Logs Bot", "canal_logsbot"))
            await interaction.response.send_message("📌 **Configurare Canale:** Alege din listele de mai jos:", view=view, ephemeral=True)

        
        elif categoria == "staff":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                f"**Categoria selectata:** {categoria}\n"
                f"**Grad:** {grad_staff}"
            )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare a serverului.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Nu ai permisiunea `setlider`.", ephemeral=True)
            
            view = discord.ui.View()
            view.add_item(RoleSelector("Rol Lider", "rol_lider"))
            view.add_item(RoleSelector("Rol Co-Lider", "rol_colider"))
            view.add_item(RoleSelector("Rol Tester", "rol_tester"))
            await interaction.response.send_message("🎖️ **Configurare Roluri Conducere:** Alege rolurile corespunzatoare:", view=view, ephemeral=True)

        
        elif categoria == "nume_ranks":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                f"**Categoria selectata:** {categoria}\n"
                f"**Grad:** {grad_staff}"
            )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare a serverului.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Lipsa permisiune.", ephemeral=True)
            await interaction.response.send_modal(NumeRankDenumiriModal())

        elif categoria == "format_nick":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                f"**Categoria selectata:** {categoria}\n"
                f"**Grad:** {grad_staff}"
            )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare a serverului.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Lipsa permisiune.", ephemeral=True)
            await interaction.response.send_modal(FormatNumeModal())

        elif categoria == "setup_roles_logic":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
                f"**Categoria selectata:** {categoria}\n"
                f"**Grad:** {grad_staff}"
            )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare a serverului.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Lipsa permisiune `setari_rank`.", ephemeral=True)
    
    
            view = discord.ui.View()
            view.add_item(RankChoiceSelect())
            await interaction.response.send_message("⚙️ Alege rank-ul pe care doresti sa il configurezi:", view=view, ephemeral=True)

        
        elif categoria == "admitere":
            if not are_permisiune(interaction, self.sd, "setari"):
                grad_staff = get_staff_rank(interaction, interaction.user)
                descriere_log = (
                    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"**Canal:** {interaction.channel_id}\n"
                    f"**Categoria selectata:** {categoria}\n"
                    f"**Grad:** {grad_staff}"
                )
                await trimite_log_centralizat(interaction, "🔧 [TENTATIVA] A folosit comanda de configurare.", descriere_log, discord.Color.from_str("#7F8C8D"))
                return await interaction.response.send_message("❌ Nu ai permisiunea `setari_admitere`.", ephemeral=True)
            
            view = discord.ui.View()
            
            
            view.add_item(AdmitereChannelSelector())
            
            
            view.add_item(MultiRoleSelector(
                placeholder="🎭 Alege rolurile primite (Rank 1)", 
                db_path=f"servers/{interaction.guild_id}/config_admitere/roles_add",
                max_val=5
            ))
            
            
            view.add_item(MultiRoleSelector(
                placeholder="🗑️ Alege rolurile scoase (ex: Civil)", 
                db_path=f"servers/{interaction.guild_id}/config_admitere/roles_remove",
                max_val=5
            ))
            
            
            btn_nr = discord.ui.Button(label="Seteaza Nr. Intrebari", style=discord.ButtonStyle.gray, emoji="🔢")
            async def btn_nr_callback(inter):
                await inter.response.send_modal(AdmitereSettingsModal())
            btn_nr.callback = btn_nr_callback
            view.add_item(btn_nr)

            await interaction.response.send_message(
                "📝 **Configurare Modul Admitere**\n"
                "• Alege canalul de teste.\n"
                "• Seteaza ce roluri **primeste** si ce roluri **pierde** candidatul.\n"
                "• Seteaza numarul de intrebari.", 
                view=view, 
                ephemeral=True
            )

class RankRoleSelector(discord.ui.RoleSelect):
    def __init__(self, rank, tip):
        super().__init__(
            placeholder=f"Roluri de {tip.upper()} la Rank {rank}",
            min_values=1,
            max_values=5
        )
        self.rank = rank
        self.tip = tip

    async def callback(self, interaction: discord.Interaction):
        role_ids = [str(role.id) for role in self.values]
        db.reference(f'servers/{interaction.guild_id}/config_rank_roluri/{self.rank}/{self.tip}').set(role_ids)
        await interaction.response.send_message(f"✅ Salvat {self.tip} pentru Rank {self.rank}!", ephemeral=True)

class RankPickerView(discord.ui.View):
    def __init__(self, rank_ales):
        super().__init__(timeout=120)
        self.add_item(RankRoleSelector(rank=rank_ales, tip="add"))
        self.add_item(RankRoleSelector(rank=rank_ales, tip="remove"))

class MultiRoleSelector(discord.ui.RoleSelect):
    def __init__(self, placeholder, db_path, max_val=10):
        super().__init__(placeholder=placeholder, min_values=1, max_values=max_val)
        self.db_path = db_path

    async def callback(self, interaction: discord.Interaction):
        
        role_ids = [str(role.id) for role in self.values]
        
        
        db.reference(self.db_path).set(role_ids)
        
        nume_roluri = ", ".join([r.name for r in self.values])
        await interaction.response.send_message(
            f"✅ Am actualizat rolurile in: `{self.db_path.split('/')[-1]}`\n**Roluri selectate:** {nume_roluri}", 
            ephemeral=True
        )



@bot.tree.command(name="configurare", description="Panoul central pentru toate setarile factiunii")
async def configurare(interaction: discord.Interaction):
    
    sd = bot.get_server_data(interaction.guild_id)

    if not sd.get("activat", False): 
        return await interaction.response.send_message("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    
    
    view = ConfigView(sd)
    await interaction.response.send_message(
        "🛠️ **Faction Management Hub**\n"
        "Foloseste meniul de mai jos pentru a configura setarile serverului.\n"
        "*Accesul la optiuni este limitat de matricea de permisiuni.*", 
        view=view, 
        ephemeral=True
    )

    grad_staff = get_staff_rank(interaction, interaction.user)
    descriere_log = (
    f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
    f"**Grad:** {grad_staff}"
)
    await trimite_log_centralizat(interaction, "📈 A folosit comanda de configurare.", descriere_log, discord.Color.from_str("#9B59B6"))

async def recalculeaza_fw(guild_id, user_id):
    ref_path = f'servers/{guild_id}/sanctiuni/{user_id}'
    ref = db.reference(ref_path)
    toate_sanctiunile = ref.get()

    if not toate_sanctiunile:
        return

    fw_list = []
    
    format_data = "%d/%m/%Y %H:%M"

    for key, val in toate_sanctiunile.items():
        if val.get('tip', '').lower() == 'fw':
            
            d_primire = val.get('data_primire') or val.get('data_acordarii')
            if d_primire:
                fw_list.append({
                    "id": key, 
                    "data_primire": d_primire
                })

    if not fw_list:
        return

    
    try:
        fw_list.sort(key=lambda x: datetime.strptime(x['data_primire'], format_data))
    except Exception as e:
        print(f"DEBUG: Eroare la sortare (verifica formatul datei): {e}")
        return

    ultima_expirare_dt = None

    for i, fw in enumerate(fw_list):
        try:
            data_primire_dt = datetime.strptime(fw['data_primire'], format_data)
            
            if i == 0:
                
                noua_expirare = data_primire_dt + timedelta(days=7)
            else:
                
                data_prim_anterior_dt = datetime.strptime(fw_list[i-1]['data_primire'], format_data)
                diferenta = (data_primire_dt - data_prim_anterior_dt).days

                if diferenta <= 3:
                    
                    noua_expirare = ultima_expirare_dt + timedelta(days=7)
                else:
                    
                    noua_expirare = data_primire_dt + timedelta(days=7)

            ultima_expirare_dt = noua_expirare
            
            
            data_finala_str = noua_expirare.strftime(format_data)
            
            
            ref.child(fw['id']).update({
                'data_expirarii': data_finala_str
            })
            print(f"DEBUG: FW {fw['id']} recalculat -> data_expirarii: {data_finala_str}")
            
        except Exception as e:
            print(f"DEBUG: Eroare procesare FW {fw['id']}: {e}")

class SelectieSanctiune(discord.ui.Select):
    def __init__(self, membru, sanctiuni_dict, interaction_original):
        self.membru = membru
        self.sanctiuni_dict = sanctiuni_dict
        
        options = []
        for s_id, date in sanctiuni_dict.items():
            tip = date.get("tip", "Sanctiune")
            motiv = date.get("motiv", "Fara motiv")
            
            valoare = date.get("valoare_amenda", 0)
            
            label = f"{tip} - {motiv[:40]}"
            
            descriere = f"Suma: {valoare:,} $" if valoare > 0 else f"Data: {date.get('data_acordarii', 'N/A')}"
            
            options.append(discord.SelectOption(
                label=label, 
                description=descriere, 
                value=s_id,
                emoji="💰" if valoare > 0 else "⚠️"
            ))

        super().__init__(placeholder="Alege sanctiunea de sters...", options=options)

    async def callback(self, interaction: discord.Interaction):
        s_id_ales = self.values[0] 
        
        
        ref_activa = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(self.membru.id)).child(s_id_ales)
        
        
        ref_istoric = bot.get_server_ref(interaction.guild_id).child("istoric_sanctiuni").child(str(self.membru.id)).child(s_id_ales)
        
        
        date_vechi = self.sanctiuni_dict.get(s_id_ales)
        tip_sanctiune = date_vechi.get('tip', '').lower()
        
        
        ref_activa.delete()
        ref_istoric.delete()

        if tip_sanctiune == "fw":
            await recalculeaza_fw(interaction.guild_id, self.membru.id)
        
        await interaction.response.send_message(f"✅ Sanctiunea **{date_vechi.get('tip')}** a fost scoasa!", ephemeral=True)
        
        
        suma_log = f" (Valoare: {date_vechi.get('valoare_amenda')} $)" if date_vechi.get('valoare_amenda') else ""
        descriere = f"**Utilizator:** {interaction.user.mention}\n**Membru:** {self.membru.mention}\n**Tip:** {date_vechi.get('tip')}{suma_log}"
        await trimite_log_centralizat(interaction, "🗑️ Sanctiune Scoasa", descriere, discord.Color.from_str("#FFF200"))

        embed_dm = discord.Embed(
        title="⚠️ O sanctiune ti-a fost scoasa!",
        description=f"Salutare, o sanctiune a fost scoasa de pe serverul **{interaction.guild.name}**.",
        color=discord.Color.red()
        )
        embed_dm.add_field(name="Sanctiune", value=date_vechi.get('tip'), inline=True) 
        embed_dm.add_field(name="Scos de", value=interaction.user.mention, inline=False)

        try:
            await self.membru.send(embed=embed_dm)
            dm_status = "✅ DM trimis"
        except:
            dm_status = "❌ DM esuat (inchis)"

class ViewSelectie(discord.ui.View):
    def __init__(self, membru, sanctiuni_dict, interaction_original):
        super().__init__(timeout=60)
        self.add_item(SelectieSanctiune(membru, sanctiuni_dict, interaction_original))

@bot.tree.command(name="scoatesanctiune", description="Alege o sanctiune specifica pentru a o sterge")
async def scoate_sanctiune(interaction: discord.Interaction, membru: discord.Member):
    sd = bot.get_server_data(interaction.guild_id)
    await interaction.response.defer(ephemeral=True)
    
    
    if not are_permisiune(interaction, sd, "scoatesanctiune"):
        grad_staff = get_staff_rank(interaction, interaction.user)
        descriere_log = (
        f"**Utilizator:** {interaction.user.mention} (`{interaction.user.id}`)\n**Canal:** {interaction.channel_id}\n"
        f"**Grad:** {grad_staff}"
    )
        await trimite_log_centralizat(interaction, "🧼 [TENTATIVA] A folosit comanda de scoatesanctiune.", descriere_log, discord.Color.from_str("#7F8C8D"))
        return await interaction.followup.send("❌ Nu ai permisiunea `scoatesanctiune`!", ephemeral=True)

    
    sanctiuni_dict = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).get()

    if not sanctiuni_dict:
        return await interaction.followup.send(f"❌ {membru.mention} nu are nicio sanctiune.", ephemeral=True)
    
    

    
    view = ViewSelectie(membru, sanctiuni_dict, interaction)
    await interaction.followup.send(f"Selecteaza sanctiunea pe care vrei sa o scoti pentru {membru.mention}:", view=view, ephemeral=True)


@bot.tree.command(
    name="fixzileall", 
    description="[OWNER] Adauga zile tuturor membrilor de pe un anumit server."
)
@app_commands.describe(
    id_server="ID-ul serverului de Discord unde vrei sa cresti zilele",
    zile="Cate zile sa adaugi fiecarui membru"
)
@app_commands.guilds(GUILD_STAFF) 
async def fix_zile_all(interaction: discord.Interaction, id_server: str, zile: int):
    
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Nu ai acces la aceasta comanda maestre.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    try:
        
        ref_membri = db.reference(f'servers/{id_server}/membri_activi')
        membri = ref_membri.get()

        if not membri:
            return await interaction.followup.send(f"❌ Nu am gasit membri activi in baza de date pentru serverul `{id_server}`.")

        
        count = 0
        for m_id, info in membri.items():
            zile_vechi = info.get("zile_factiune", 0)
            ref_membri.child(m_id).update({
                "zile_factiune": zile_vechi + zile
            })
            count += 1

        
        await interaction.followup.send(
            f"✅ Operatiune reusita!\n"
            f"**Server ID:** `{id_server}`\n"
            f"**Membri actualizati:** {count}\n"
            f"**Zile adaugate:** +{zile}"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ A aparut o eroare la Firebase: {e}")

class HelpDropdown(discord.ui.Select):
    def __init__(self, optiuni):
        
        options = [
            discord.SelectOption(label=nume, description=f"Mergi la link-ul pentru {nume}")
            for nume in optiuni.keys()
        ]
        super().__init__(placeholder="Alege categoria de ajutor...", options=options)
        self.optiuni_linkuri = optiuni

    async def callback(self, interaction: discord.Interaction):
        link_destinatie = self.optiuni_linkuri.get(self.values[0])
        
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=f"Deschide {self.values[0]}", url=link_destinatie))
        
        await interaction.response.send_message(
            f"🔗 Ai ales **{self.values[0]}**. Apasa butonul de mai jos pentru a accesa site-ul:",
            view=view,
            ephemeral=True
        )

class HelpView(discord.ui.View):
    def __init__(self, optiuni):
        super().__init__()
        self.add_item(HelpDropdown(optiuni))

@bot.tree.command(name="help", description="Afiseaza categoriile de ajutor disponibile")
async def help_command(interaction: discord.Interaction):
    
    
    optiuni = db.reference(f"setari_help").get()

    if not optiuni or not isinstance(optiuni, dict):
        return await interaction.response.send_message(
            "❌ Nu au fost configurate optiuni de ajutor.", 
            ephemeral=True
        )

    view = HelpView(optiuni)
    embed = discord.Embed(
        title="📚 Centru de Ajutor - PCAF",
        description="Selecteaza din lista de mai jos subiectul care te intereseaza pentru a fi redirectionat catre site-ul nostru.",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
@bot.tree.command(name="mute", description="Pune timeout unui membru (Mute)")
@app_commands.describe(
    membru="Membru pe care vrei sa il reduci la tacere", 
    durata="Durata in minute (ex: 10, 60, 1440)", 
    motiv="Motivul sanctiunii"
)
async def mute(interaction: discord.Interaction, membru: discord.Member, durata: int, motiv: str):
    
    sd = bot.get_server_data(interaction.guild_id)
    if not are_permisiune(interaction, sd, "mute"):
        return await interaction.response.send_message("❌ Nu ai permisiunea necesara pentru a folosi aceasta comanda.", ephemeral=True)

    
    if membru.id == interaction.user.id:
        return await interaction.response.send_message("❌ Nu iti poti da mute singur.", ephemeral=True)
    
    if membru.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Nu poti pedepsi un membru cu grad egal sau mai mare decat al tau.", ephemeral=True)

    
    
    if durata > 40320:
        durata = 40320

    timeout_duration = timedelta(minutes=durata)
    
    try:
        
        await membru.timeout(timeout_duration, reason=motiv)
        
        
        tz_ro = pytz.timezone('Europe/Bucharest')
        data_acum = datetime.now(tz_ro).strftime("%d/%m/%Y %H:%M")
        

        
        descriere_log = (
            f"**Membru:** {membru.mention} (`{membru.id}`)\n"
            f"**Durata:** {durata} minute\n"
            f"**Motiv:** {motiv}\n"
            f"**Autor:** {interaction.user.mention}"
        )
        await trimite_log_centralizat(interaction, "🔇 Membru Redus la Tacere", descriere_log, discord.Color.orange())

        
        await interaction.response.send_message(f"✅ **{membru.display_name}** a primit mute pentru **{durata}** minute.\nMotiv: {motiv}")

        
        try:
            embed_dm = discord.Embed(
                title=f"🔇 Ai primit mute pe {interaction.guild.name}",
                description=f"Nu vei mai putea scrie sau vorbi timp de {durata} minute.",
                color=discord.Color.orange()
            )
            embed_dm.add_field(name="Motiv", value=motiv)
            embed_dm.add_field(name="Expiră peste", value=f"{durata} minute")
            await membru.send(embed=embed_dm)
        except:
            pass

    except Exception as e:
        await interaction.response.send_message(f"❌ A aparut o eroare: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Scoate timeout-ul unui membru")
async def unmute(interaction: discord.Interaction, membru: discord.Member):
    if not are_permisiune(interaction, bot.get_server_data(interaction.guild_id), "mute"):
        return await interaction.response.send_message("❌ Lipsa permisiuni.", ephemeral=True)

    try:
        await membru.timeout(None)
        await interaction.response.send_message(f"🔊 I-a fost scos mute-ul lui **{membru.display_name}**.")
        
        
        await trimite_log_centralizat(interaction, "🔊 Mute Scos", f"**Membru:** {membru.mention}\n**Autor:** {interaction.user.mention}", discord.Color.green())
    except Exception as e:
        await interaction.response.send_message(f"❌ Eroare: {e}", ephemeral=True)
    
SERVER_ID = discord.Object(id=1397667791846375504)
@bot.tree.command(name="rolurisv", description="Afișează ierarhia rolurilor de pe un server specific", guild=SERVER_ID)
@app_commands.describe(id_server="ID-ul serverului pentru care vrei lista de roluri")
async def rolurisv(interaction: discord.Interaction, id_server: str):
    
    
    if interaction.guild_id != 1397667791846375504: 
        return await interaction.response.send_message("❌ Această comandă este administrativă și nu poate fi folosită aici.", ephemeral=True)

    
    try:
        target_guild = bot.get_guild(int(id_server))
    except ValueError:
        return await interaction.response.send_message("❌ ID-ul introdus nu este valid.", ephemeral=True)

    if not target_guild:
        return await interaction.response.send_message("❌ Botul nu se află pe acest server sau ID-ul este greșit.", ephemeral=True)

    
    
    roles = sorted(target_guild.roles, key=lambda r: r.position, reverse=True)

    
    lista_roluri = ""
    for role in roles:
        if role.name == "@everyone": continue 
        
        linie = f"**{role.position}.** {role.name} (`{role.id}`)\n"
        
        
        if len(lista_roluri) + len(linie) > 3900:
            lista_roluri += "... și altele (prea multe roluri pentru afișare)."
            break
        lista_roluri += linie

    
    embed = discord.Embed(
        title=f"Ierarhie Roluri: {target_guild.name}",
        description=lista_roluri or "Nu am găsit roluri.",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Total: {len(target_guild.roles)} roluri")
    
    await interaction.response.send_message(embed=embed)


class RaportDataModal(Modal):
    def __init__(self, membru_nume, activitati, callback_func):
        super().__init__(title=f"Raport: {membru_nume}")
        self.activitati = activitati
        self.callback_func = callback_func
        self.inputs = {}

        for act in self.activitati:
            text_input = TextInput(
                label=f"Câte {act} are?",
                placeholder="Ex: 5",
                required=True,
                default="0" 
            )
            self.add_item(text_input)
            self.inputs[act] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        rezultate = {}
        for act, text_input in self.inputs.items():
            try:
                rezultate[act] = int(text_input.value)
            except ValueError:
                rezultate[act] = 0
        
        
        await self.callback_func(interaction, rezultate)

VALORI_PUNCTE = {
    "licente": 1,        
    "transporturi": 1,
    "heals": 1,
    "incendii": 1,
    "apeluri": 1,        
    "contracte": 1,
    "rapiri": 1,
    "amenzi": 1,
    "runners": 1,         
    "vame": 1
    }


class RaportFlowView(View):
    def __init__(self, interaction, membrii_activi, cerinte_raport, invoiti):
        super().__init__(timeout=None)
        self.initial_interaction = interaction
        self.membrii = membrii_activi
        self.cerinte = cerinte_raport
        self.invoiti = invoiti
        self.index = 0
        self.final_stats = []
        self.leaderboard = []

    async def incepe(self):
        
        await self.proceseaza_urmatorul(self.initial_interaction)

    async def proceseaza_urmatorul(self, interaction: discord.Interaction):
        
        if self.index >= len(self.membrii):
            embed_final = discord.Embed(title="📊 Rezultate Finale Raport", color=0x2b2d31)
            
            
            top_sorted = sorted(self.leaderboard, key=lambda x: x['puncte'], reverse=True)
            
            text_top = "**🏆 MEMBRUL SAPTAMANII:**\n"
            for i, user in enumerate(top_sorted[:1]): 
                medalie = ["🥇"][i]
                
                
                detalii_list = []
                for act, val in user['detalii'].items():
                    if int(val) > 0: 
                        detalii_list.append(f"{val} {act}")
                
                detalii_text = ", ".join(detalii_list)
                text_top += f"{medalie} **{user['nume']}** - `{user['puncte']} pct`\n"
                text_top += f"└─ *({detalii_text})*\n" 

            embed_final.description = text_top + "\n**📋 STATUS MEMBRI:**\n" + "\n".join(self.final_stats)

            if interaction.response.is_done():
                return await interaction.followup.send(embed=embed_final)
            else:
                return await interaction.response.send_message(embed=embed_final)

        membru_curent = self.membrii[self.index]
        nume_afisat = membru_curent.get('nume', membru_curent.get('nume_joc', "Membru Necunoscut"))
        
        
        disc_id = str(membru_curent.get('discord_id', ''))
        if disc_id in self.invoiti:
            self.final_stats.append(f"🔹 **{nume_afisat}**: ✅ Învoit")
            self.index += 1
            return await self.proceseaza_urmatorul(interaction)

        
        sd = bot.get_server_data(interaction.guild_id)
        id_rol_tester = str(sd.get("rol_tester", ""))
        rank_idx = int(membru_curent.get('rank', 1))
        is_staff = membru_curent.get('staff', False)
        
        guild = interaction.guild
        discord_member = guild.get_member(int(membru_curent.get('discord_id', 0)))
        is_tester = any(str(role.id) == id_rol_tester for role in discord_member.roles) if discord_member else False

        cerinte_rank = {}
        if is_staff and isinstance(self.cerinte, dict):
            cerinte_rank = self.cerinte.get('tester,staff', {})
        elif is_tester and isinstance(self.cerinte, dict):
            cerinte_rank = self.cerinte.get('tester,staff', {})
        elif isinstance(self.cerinte, list):
            cerinte_rank = self.cerinte[rank_idx] if rank_idx < len(self.cerinte) else {}
        else:
            cerinte_rank = self.cerinte.get(str(rank_idx), {})

        if not cerinte_rank:
            self.final_stats.append(f"⚪ **{nume_afisat}**: Fără cerințe.")
            self.index += 1
            return await self.proceseaza_urmatorul(interaction)

        
        activitati = [k for k in cerinte_rank.keys() if k not in ["staff", "tester"]]
        modal = RaportDataModal(nume_afisat, activitati, self.salveaza_si_continua)
        
        
        
        if interaction.type == discord.InteractionType.modal_submit:
            view = View()
            btn = discord.ui.Button(label=f"Verifică: {nume_afisat}", style=discord.ButtonStyle.primary)
            
            async def btn_callback(it: discord.Interaction):
                await it.response.send_modal(modal)
            
            btn.callback = btn_callback
            view.add_item(btn)
            
            await interaction.response.send_message(content=f"S-a salvat. Apasă butonul pentru următorul membru:", view=view, ephemeral=True)
        else:
            
            await interaction.response.send_modal(modal)

    async def salveaza_si_continua(self, interaction: discord.Interaction, date_introduse: dict):
        membru_curent = self.membrii[self.index]
        nume_afisat = membru_curent.get('nume', membru_curent.get('nume_joc', "Membru Necunoscut"))

        puncte_totale = 0
        for activitate, cantitate in date_introduse.items():
            valoare_unitara = VALORI_PUNCTE.get(activitate.lower(), 0)
            puncte_totale += int(cantitate) * valoare_unitara
        
        
        self.leaderboard.append({
            "nume": nume_afisat, 
            "puncte": puncte_totale,
            "detalii": date_introduse
        })

        
        stats_ref = db.reference(f'servers/{interaction.guild_id}/statistica_raport')
        stats_data = stats_ref.get()

        if stats_data:
            m_id = str(membru_curent['discord_id'])
            
            
            vechiul_membru_data = stats_data.get('date', {}).get(m_id, {})
            puncte_vechi = vechiul_membru_data.get('puncte', 0)
            detalii_vechi = vechiul_membru_data.get('detalii', {})

            
            noul_total_puncte = puncte_vechi + puncte_totale

            
            noile_detalii = detalii_vechi.copy()
            for activitate, cantitate in date_introduse.items():
                cantitate_veche = noile_detalii.get(activitate, 0)
                noile_detalii[activitate] = int(cantitate_veche) + int(cantitate)

            
            stats_ref.child(f'date/{m_id}').update({
                "nume": nume_afisat,
                "puncte": noul_total_puncte,
                "detalii": noile_detalii
            })
            
            
            stats_data_updatat = stats_ref.get()
            await actualizeaza_tabel_mesaj(interaction.guild, stats_data_updatat)
        
        
        rank_idx = int(membru_curent.get('rank', 1))
        is_staff = membru_curent.get('staff', False)
                
        sd = bot.get_server_data(interaction.guild_id)
        id_rol_tester = str(sd.get("rol_tester", ""))
        
        guild = interaction.guild
        discord_member = guild.get_member(int(membru_curent.get('discord_id', 0)))
        is_tester = any(str(role.id) == id_rol_tester for role in discord_member.roles) if discord_member else False
        
        if is_staff and isinstance(self.cerinte, dict):
            cerinte_rank = self.cerinte.get('tester,staff', {})
        elif is_tester and isinstance(self.cerinte, dict):
            cerinte_rank = self.cerinte.get('tester,staff', {})
        else:
            cerinte_rank = self.cerinte[rank_idx] if isinstance(self.cerinte, list) else self.cerinte.get(str(rank_idx), {})

        lipsuri = []
        for act, minim in cerinte_rank.items():
            if act in ["staff", "tester"]: continue
            are = date_introduse.get(act, 0)
            if are < int(minim):
                lipsuri.append(f"{int(minim) - are} {act}")

        status = "✅ Complet" if not lipsuri else f"❌ Lipsă: {', '.join(lipsuri)}"
        
        if is_staff:
            emoji = "⭐"  
        elif is_tester:
            emoji = "🧪"  
        elif rank_idx == 7:
            emoji = "👑"  
        elif rank_idx == 6:
            emoji = "💎"  
        else:
            emoji = "👤"  

        
        self.final_stats.append(f"{emoji} **{nume_afisat}**: {status} (**{puncte_totale} pct**)")
        
        grad_staff = get_staff_rank(interaction, interaction.user)
        
        
        text_raport_introdus = ""
        for act, val in date_introduse.items():
            text_raport_introdus += f"• {act}: **{val}**\n"

        descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {nume_afisat}\n"
            f"**Grad Verificator:** {grad_staff}\n\n"
            f"**Date introduse în formular:**\n{text_raport_introdus}"
        )
        
        await trimite_log_centralizat(
            interaction, 
            f"📊 Verificare Raport: {nume_afisat}", 
            descriere_log, 
            discord.Color.blue()
        )

        self.index += 1
        
        await self.proceseaza_urmatorul(interaction)


@bot.tree.command(name="vraport", description="Verifică raportul membrilor")
async def vraport(interaction: discord.Interaction):
    sd = bot.get_server_data(interaction.guild_id, force_refresh=True)
    
    cerinte = sd.get("raport", [])
    membrii_dict = sd.get("membri_activi", {}) 
    
    invoiti_ms = sd.get("invoiri_ms", {})
    invoiti_normal = sd.get("invoiri", {})
    toate_inv = [str(k) for k in invoiti_ms.keys()] + [str(k) for k in invoiti_normal.keys()]

    if not membrii_dict:
        return await interaction.response.send_message("❌ Nu am găsit membri în `membri_factiune`.")

    lista_membri = []
    for m_id, m_data in membrii_dict.items():
        
        if isinstance(m_data, dict):
            m_data['discord_id'] = m_id
            lista_membri.append(m_data)
        
    
    lista_membri.sort(key=lambda x: int(x.get('rank', 0)), reverse=True)

    view = RaportFlowView(interaction, lista_membri, cerinte, toate_inv)
    await view.incepe()



def get_rank_name_safe(nume_rankuri, rn):
    
    try:
        
        rankuri_valide = [r for r in nume_rankuri if r is not None]
        if 1 <= rn <= len(rankuri_valide):
            return rankuri_valide[rn - 1]
        return f"Rank {rn}"
    except:
        return f"Rank {rn}"

@bot.tree.command(name="acordagrad", description="Acordă funcția de Tester sau Co-Lider")
@app_commands.describe(membru="Membru vizat", functie="Funcția dorită")
@app_commands.choices(functie=[
    app_commands.Choice(name="Tester", value="tester"),
    app_commands.Choice(name="Co-Lider", value="colider"),
    app_commands.Choice(name="STAFF", value="staff")
])
async def acordagrad(interaction: discord.Interaction, membru: discord.Member, functie: str):
    await interaction.response.defer(ephemeral=True)
    sd = bot.get_server_data(interaction.guild_id)
    grad_staff = get_staff_rank(interaction, interaction.user)

    if not are_permisiune(interaction, sd, "setlider"):
        return await interaction.followup.send("❌ Lipsa permisiuni.", ephemeral=True)

    info_ref = bot.get_server_ref(interaction.guild_id).child('setari_nume')
    ref_membru = bot.get_server_ref(interaction.guild_id).child(f'membri_activi/{membru.id}')
    
    data_membru = ref_membru.get()
    setari_nume = info_ref.get() or {}

    if not data_membru:
        return await interaction.followup.send("❌ Membrul nu este în baza de date!")

    nume_joc = data_membru.get('nume_joc') or data_membru.get('nume') or membru.display_name.split(' - ')[0]
    rank_nr = int(data_membru.get('rank', 1))
    nume_rankuri = setari_nume.get('rankuri', [])
    format_p = setari_nume.get('format', "{nume} - {rank_nume}")

    status_actiuni = []

    if functie == "tester":
        rol_id = sd.get("rol_tester")
        if rol_id:
            rol = interaction.guild.get_role(int(rol_id))
            if rol:
                try:
                    await membru.add_roles(rol)
                    status_actiuni.append("✅ Rol Tester adăugat")
                except discord.Forbidden:
                    status_actiuni.append("❌ Lipsă permisiuni pentru rol Tester")

        nume_r_text = get_rank_name_safe(nume_rankuri, rank_nr)
        valoare_rank_finala = f"{nume_r_text} & Tester"
        noua_porecla = format_p.replace("{nume}", nume_joc).replace("{rank_nume}", valoare_rank_finala)
        
        try:
            await membru.edit(nick=noua_porecla[:32])
            status_actiuni.append(f"✅ Poreclă actualizată: `{noua_porecla[:32]}`")
        except discord.Forbidden:
            status_actiuni.append("❌ Nu pot schimba porecla (Ierarhie/Owner)")

    elif functie == "colider":
        
        config_generala = sd.get("config_rank_roluri", {})
        config_roluri = {}

        if isinstance(config_generala, list):
            
            if len(config_generala) > 6:
                config_roluri = config_generala[6]
        elif isinstance(config_generala, dict):
            
            config_roluri = config_generala.get("6", {})

        
        if not isinstance(config_roluri, dict):
            config_roluri = {}

        roluri_de_adaugat = config_roluri.get("add", [])
        roluri_de_scos = config_roluri.get("remove", [])

        
        if isinstance(roluri_de_adaugat, list):
            for r_id in roluri_de_adaugat:
                rol = interaction.guild.get_role(int(r_id))
                if rol:
                    try: await membru.add_roles(rol)
                    except: status_actiuni.append(f"❌ Nu am putut adăuga rolul {rol.name}")

        
        if isinstance(roluri_de_scos, list):
            for r_id in roluri_de_scos:
                rol = interaction.guild.get_role(int(r_id))
                if rol:
                    try: await membru.remove_roles(rol)
                    except: pass

        
        ref_membru.update({"rank": 6})
        nume_r6_text = get_rank_name_safe(nume_rankuri, 6)
        noua_porecla = format_p.replace("{nume}", nume_joc).replace("{rank_nume}", nume_r6_text)
        
        try:
            await membru.edit(nick=noua_porecla[:32])
            status_actiuni.append(f"✅ Grad Co-Lider acordat.")
        except discord.Forbidden:
            status_actiuni.append("❌ Nu pot schimba porecla (Ierarhie/Owner)")

    elif functie == "staff":
        try:
            ref_membru.update({"staff": True})
            status_actiuni.append("✅ Membrul a fost marcat ca membru **STAFF**.")
        except Exception as e:
            status_actiuni.append(f"❌ Eroare la actualizarea bazei de date: {e}")

    await interaction.followup.send("\n".join(status_actiuni))



@bot.tree.command(name="scoategrad", description="Scoate funcția unui membru")
@app_commands.describe(membru="Membru vizat", functie="Funcția de scos")
@app_commands.choices(functie=[
    app_commands.Choice(name="Tester", value="tester"),
    app_commands.Choice(name="Co-Lider", value="colider"),
    app_commands.Choice(name="STAFF", value="staff")
])
async def scoategrad(interaction: discord.Interaction, membru: discord.Member, functie: str):
    await interaction.response.defer(ephemeral=True)
    sd = bot.get_server_data(interaction.guild_id)

    if not are_permisiune(interaction, sd, "setlider"):
        return await interaction.followup.send("❌ Lipsa permisiuni.", ephemeral=True)

    info_ref = bot.get_server_ref(interaction.guild_id).child('setari_nume')
    ref_membru = bot.get_server_ref(interaction.guild_id).child(f'membri_activi/{membru.id}')
    
    data_membru = ref_membru.get()
    setari_nume = info_ref.get() or {}

    if not data_membru:
        return await interaction.followup.send("❌ Membrul nu este în baza de date!")

    nume_joc = data_membru.get('nume_joc') or data_membru.get('nume') or membru.display_name.split(' - ')[0]
    nume_rankuri = setari_nume.get('rankuri', [])
    format_p = setari_nume.get('format', "{nume} - {rank_nume}")

    status_actiuni = []

    if functie == "tester":
        rol_id = sd.get("rol_tester")
        if rol_id:
            rol = interaction.guild.get_role(int(rol_id))
            if rol:
                try: await membru.remove_roles(rol)
                except: pass

        rank_actual = int(data_membru.get('rank', 1))
        nume_r_curat = get_rank_name_safe(nume_rankuri, rank_actual)
        noua_porecla = format_p.replace("{nume}", nume_joc).replace("{rank_nume}", nume_r_curat)
        
        try:
            await membru.edit(nick=noua_porecla[:32])
            status_actiuni.append(f"✅ Tester scos. Poreclă: `{noua_porecla[:32]}`")
        except:
            status_actiuni.append("⚠️ Rank-ul a fost actualizat, dar porecla nu a putut fi schimbată.")

    elif functie == "colider":
        config_roluri = sd.get("config_rank_roluri", {}).get("6", {})
        roluri_de_scos = config_roluri.get("add", []) 
        roluri_de_pus_inapoi = config_roluri.get("remove", []) 

        
        for r_id in roluri_de_scos:
            rol = interaction.guild.get_role(int(r_id))
            if rol:
                try: await membru.remove_roles(rol)
                except: pass

        
        for r_id in roluri_de_pus_inapoi:
            rol = interaction.guild.get_role(int(r_id))
            if rol:
                try: await membru.add_roles(rol)
                except: pass

        
        zile = int(data_membru.get('zile_factiune', 0))
        
        sanctiuni_active = sd.get("sanctiuni", {}).get(str(membru.id), {})
        fw_count = sum(1 for s in sanctiuni_active.values() if s.get("tip") == "FW")
        
        zile_ajustate = zile - (fw_count * 7)
        
        if zile_ajustate >= 70: nr = 5
        elif zile_ajustate >= 49: nr = 4
        elif zile_ajustate >= 28: nr = 3
        elif zile_ajustate >= 14: nr = 2
        else: nr = 1

        ref_membru.update({"rank": nr})
        nume_r_nou = get_rank_name_safe(nume_rankuri, nr)
        noua_porecla = format_p.replace("{nume}", nume_joc).replace("{rank_nume}", nume_r_nou)
        
        try:
            await membru.edit(nick=noua_porecla[:32])
            status_actiuni.append(f"✅ Co-Lider scos. Membrul a revenit la Rank {nr}.")
        except:
            status_actiuni.append(f"✅ Co-Lider scos din DB, dar porecla a rămas neschimbată.")

    elif functie == "staff":
        try:
            
            ref_membru.child("staff").delete() 
            
            status_actiuni.append("✅ Membrul nu mai este marcat ca membru **STAFF**.")
        except Exception as e:
            status_actiuni.append(f"❌ Eroare la actualizarea bazei de date: {e}")

    await interaction.followup.send("\n".join(status_actiuni))

import re


def parse_timp(timp_str):
    minute_totale = 0
    ore = re.search(r'(\d+)h', timp_str.lower())
    minute = re.search(r'(\d+)m', timp_str.lower())
    if ore:
        minute_totale += int(ore.group(1)) * 60
    if minute:
        minute_totale += int(minute.group(1))
    return minute_totale

@bot.tree.command(name="inactivitate", description="Setează un termen limita pentru intrarea pe joc")
@app_commands.describe(membru="Membrul vizat", timp="Format: 1h, 30m sau 1h 30m")
async def ultimansansa(interaction: discord.Interaction, membru: discord.Member, timp: str):
    await interaction.response.defer()
    nume_server = interaction.guild.name
    sd = bot.get_server_data(interaction.guild_id)
    grad_staff = get_staff_rank(interaction, interaction.user)
    if not are_permisiune(interaction, sd, "demite"):
        descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {membru}\n"
            f"**Timp:** {timp}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
        await trimite_log_centralizat(
            interaction, 
            "📊 [TENTATIVA] termen inactivitate!", 
            descriere_log, 
            discord.Color.from_str("#6E696E")
        )
        return await interaction.followup.send("❌ Lipsa permisiuni.")
    
    descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {membru}\n"
            f"**Timp:** {timp}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
    await trimite_log_centralizat(
            interaction, 
            "📊 termen inactivitate!", 
            descriere_log, 
            discord.Color.from_str("#F811E5")
        )
    
    minute = parse_timp(timp)
    
    if minute <= 0:
        return await interaction.followup.send("❌ Format timp invalid! Folosește `1h`, `30m` sau `1h 30m`.")

    
    acum = datetime.now(pytz.timezone('Europe/Bucharest'))
    data_expirare = acum + timedelta(minutes=minute)
    data_str = data_expirare.strftime("%d/%m/%Y %H:%M")

    
    ref = bot.get_server_ref(interaction.guild_id).child(f'ultima_sansa/{membru.id}')
    ref.set({
        "nume": membru.display_name,
        "termen": data_str,
        "canal_anunturi": sd.get("canal_anunturi")
    })

    
    try:
        embed_dm = discord.Embed(
            title="⚠️ INACTIVITATE - IMPORTANT",
            description=f"Salut! Ai primit un termen limită de **{timp}** pe {nume_server} pentru a intra pe serverul de joc.\n\n"
                        f"**Termen limită:** `{data_str}`\n"
                        f"Dacă nu ești prezent pe joc până la această oră, vei fi demis.",
            color=discord.Color.red()
        )
        await membru.send(embed=embed_dm)
        msg_dm = "✅ Mesaj privat trimis."
    except:
        msg_dm = "⚠️ Mesajul privat nu a putut fi trimis (DM închis)."

    await interaction.followup.send(f"✅ Am setat termenul pentru inactivitatea jucatorului {membru.mention} până la `{data_str}`.\n{msg_dm}")

class UltimaSansaButtons(discord.ui.View):
    def __init__(self, user_id=None, nume=None): 
        super().__init__(timeout=None)
        self.user_id = user_id
        self.nume = nume

    @discord.ui.button(label="A INTRAT", style=discord.ButtonStyle.success, custom_id="sansa_a_intrat_v2")
    async def a_intrat(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        uid = self.user_id
        sd = bot.get_server_data(interaction.guild_id)
        grad_staff = get_staff_rank(interaction, interaction.user)
        nume_jucator = self.nume or "Necunoscut"
        
        if not uid:
            import re
            match = re.search(r"ID: (\d+)", interaction.message.content)
            if match: uid = match.group(1)

        await interaction.response.defer(ephemeral=True)
        
        
        if not are_permisiune(interaction, sd, "demite"):
            descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {uid}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
            await trimite_log_centralizat(
            interaction, 
            "📊 [TENTATIVA] aprobare membru a intrat pe server!", 
            descriere_log, 
            discord.Color.from_str("#6E696E")
        )
            return await interaction.followup.send(
                f"❌ Nu ai permisiunea de a valida intrarea jucătorilor!", 
                ephemeral=True
            )

        
        
        await interaction.followup.send(
            f"✅ Jucătorul **{nume_jucator}** ({uid}) a fost marcat ca **ACTIV** de către {interaction.user.mention}.",
            ephemeral=False 
        )

        
        descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {uid}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
        await trimite_log_centralizat(
            interaction, 
            "📊 aprobare membru a intrat pe server!", 
            descriere_log, 
            discord.Color.from_str("#F811E5")
        )

        
        
        try:
            db.reference(f'/servers/{interaction.guild_id}/ultima_sansa/{uid}').delete()
        except:
            pass

        
        self.stop()

    @discord.ui.button(label="NU A INTRAT (DEMITE)", style=discord.ButtonStyle.danger, custom_id="sansa_nu_a_intrat_v2")
    async def nu_a_intrat(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        try:
            await interaction.response.defer()
        except:
            return 
        
        uid = self.user_id
        sd = bot.get_server_data(interaction.guild_id)
        grad_staff = get_staff_rank(interaction, interaction.user)
        if not uid:
            import re
            match = re.search(r"ID: (\d+)", interaction.message.content)
            if match: uid = match.group(1)

        

        
        if not are_permisiune(interaction, sd, "demite"):
            descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {uid}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
            await trimite_log_centralizat(
            interaction, 
            "📊 [TENTATIVA] aprobare membru nu a intrat pe server!", 
            descriere_log, 
            discord.Color.from_str("#6E696E")
        )
            
            
            return await interaction.response.send_message("❌ Nu ai permisiunea de a folosi acest buton!", ephemeral=True)

        
        if uid:
            membru_obiect = interaction.guild.get_member(int(uid))
            
            try:

                await demitere_inactivitate(interaction, membru_obiect, "Inactivitate (Ultima Șansă)")
                
                
                

                descriere_log = (
            f"**Verificator:** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Canal:** <#{interaction.channel_id}>\n"
            f"**Jucător vizat:** {uid}\n"
            f"**Grad Verificator:** {grad_staff}"
        )
        
                await trimite_log_centralizat(
            interaction, 
            "📊 aprobare membru nu a intrat pe server!", 
            descriere_log, 
            discord.Color.from_str("#F811E5")
        )

                try:
                    interaction.client.get_server_ref(interaction.guild_id).child(f'ultima_sansa/{uid}').delete()
                except:
                    pass
            except Exception as e:
                await interaction.response.send_message(f"❌ Eroare la demitere: {e}", ephemeral=True)

@bot.tree.command(name="listamembri", description="Afiseaza lista tuturor membrilor din factiune")
@app_commands.describe(
    id_server="ID-ul serverului de Discord unde vrei sa citesti"
)
@app_commands.guilds(GUILD_STAFF) 
async def lista_membri(interaction: discord.Interaction, id_server: str = None):
    await interaction.response.defer()
    sd = bot.get_server_data(id_server, force_refresh=True)
    membri = sd.get("membri_activi", {})

    if not sd.get("activat", False): 
        return await interaction.followup.send("❌ Botul nu este activat. Foloseste /activate.", ephemeral=True)
    
    if interaction.user.id != OWNER_ID:
        return await interaction.followup.send("❌ Nu ai acces la aceasta comanda.", ephemeral=True)

    if not membri:
        return await interaction.followup.send("📭 Nu exista membri inregistrati.", ephemeral=True)

    
    lista_membri_pregatita = []
    for m_id, info in membri.items():
        lista_membri_pregatita.append({
            "id": m_id, 
            "nume": info.get('nume_joc', 'Necunoscut'),
            "rank": int(info.get('rank', 777)),
            "zile": int(info.get('zile_factiune', 777))
        })

    
    membri_sortati = sorted(lista_membri_pregatita, key=lambda x: (-x['rank'], -x['zile']))

    
    embed = discord.Embed(title=f"👥 Membri Factiunii - {interaction.guild.name}", color=discord.Color.blue())
    
    descriere = ""
    for i, m in enumerate(membri_sortati, 1):
        descriere += f"{i}. **{m['nume']}** (<@{m['id']}>) - Rank {m['rank']} - {m['zile']} zile\n"

    
    embed.description = descriere[:4000] if descriere else "Niciun membru gasit."
    await interaction.followup.send(embed=embed)

@bot.command(name="scoaterol")
@commands.has_permissions(administrator=True) 
async def scoaterol(ctx, rol_vizat: discord.Role, *, exceptii: str = ""):
    
    lista_exceptii = [e.strip().lower() for e in exceptii.replace('"', '').split(',')] if exceptii else []
    
    confirmare = await ctx.send(f"⏳ Se începe procesul de scoatere a rolului {rol_vizat.mention}...")
    
    rezultate = []
    contor_scos = 0
    contor_verificat = 0

    
    
    for membru in list(rol_vizat.members):
        nume_display = membru.name
        
        
        if nume_display.lower() in lista_exceptii:
            rezultate.append(f"🔹 **{nume_display}** - Verificat (nu s-a scos rolul)")
            contor_verificat += 1
        else:
            try:
                await membru.remove_roles(rol_vizat, reason=f"Comandă executată de {ctx.author}")
                rezultate.append(f"✅ **{nume_display}** - A scos rolul")
                contor_scos += 1
            except discord.Forbidden:
                rezultate.append(f"❌ **{nume_display}** - Eroare (Lipsă permisiuni)")
            except Exception as e:
                rezultate.append(f"❌ **{nume_display}** - Eroare neașteptată")

    
    
    header = f"📊 **Raport finalizare scoatere rol {rol_vizat.name}:**\n"
    footer = f"\nTotal: {contor_scos} scoase, {contor_verificat} exceptate."
    
    output = header + "\n".join(rezultate) + footer

    if len(output) > 1900:
        
        with open("raport_rol.txt", "w", encoding="utf-8") as f:
            f.write(output.replace("**", ""))
        await ctx.send("✅ Proces finalizat! Raportul este prea lung:", file=discord.File("raport_rol.txt"))
        os.remove("raport_rol.txt")
    else:
        await ctx.send(output)

class EditGenericModal(discord.ui.Modal):
    def __init__(self, titlu, s_id, data, ref, fields_to_edit):
        super().__init__(title=titlu)
        self.s_id = s_id
        self.ref = ref
        self.inputs = {}

        
        
        for key, label in fields_to_edit:
            valoare_initiala = str(data.get(key, ""))
            text_input = discord.ui.TextInput(
                label=label,
                default=valoare_initiala,
                style=discord.TextStyle.short if len(valoare_initiala) < 50 else discord.TextStyle.paragraph,
                required=False
            )
            self.add_item(text_input)
            self.inputs[key] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        update_data = {}
        
        for key, inp in self.inputs.items():
            valoare = inp.value
            
            
            
            if valoare.isdigit() and "id" not in key.lower():
                update_data[key] = int(valoare)
            else:
                update_data[key] = valoare
                
        if self.s_id:
            self.ref.child(self.s_id).update(update_data)
        else:
            self.ref.update(update_data)
            
        await interaction.response.send_message("✅ Datele au fost actualizate!", ephemeral=True)

class ActionButtons(discord.ui.View):
    def __init__(self, s_id, data, ref, fields):
        super().__init__(timeout=None)
        self.s_id = s_id
        self.data = data
        self.ref = ref
        self.fields = fields

    @discord.ui.button(label="Editează Toate Campurile", style=discord.ButtonStyle.primary)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditGenericModal("Editează Detalii", self.s_id, self.data, self.ref, self.fields))

    @discord.ui.button(label="Șterge", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.s_id:
            self.ref.child(self.s_id).delete()
        else:
            self.ref.delete()
        await interaction.response.send_message(f"✅ Șters!", ephemeral=True)

class MigrareIDModal(discord.ui.Modal, title="Migrare Date pe ID Nou"):
    id_nou = discord.ui.TextInput(label="ID Discord Nou", placeholder="Introdu noul ID (cifre)...", min_length=15)

    def __init__(self, guild_id, id_vechi):
        super().__init__()
        self.guild_id = guild_id
        self.id_vechi = str(id_vechi)

    async def on_submit(self, interaction: discord.Interaction):
        id_nou = self.id_nou.value.strip()
        base_path = f'servers/{self.guild_id}'
        
        
        noduri = ["membri_activi", "sanctiuni", "istoric_sanctiuni", "invoiri", "inactivitate"]
        mutari_efectuate = []

        for nod in noduri:
            ref_vechi = db.reference(f'{base_path}/{nod}/{self.id_vechi}')
            date = ref_vechi.get()
            
            if date:
                
                db.reference(f'{base_path}/{nod}/{id_nou}').set(date)
                
                ref_vechi.delete()
                mutari_efectuate.append(nod)

        if not mutari_efectuate:
            await interaction.response.send_message(f"❌ Nu s-au gasit date de mutat pentru ID-ul `{self.id_vechi}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Migrare finalizată!\nDatele din `{', '.join(mutari_efectuate)}` au fost mutate de pe `{self.id_vechi}` pe `{id_nou}`.", ephemeral=True)

CATEGORII_EDIT = ["istoric sanctiuni", "sanctiuni active", "membri", "invoiri", "inactivitate", "modificare id discord", "functii"]

async def categorie_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=c.capitalize(), value=c)
        for c in CATEGORII_EDIT if current.lower() in c.lower()
    ]

@bot.tree.command(name="edit", description="Editeaza datele din baza de date (Membru sau ID)")
@app_commands.describe(categorie="Alege categoria", user_input="Tag membru SAU introdu ID-ul direct")
@app_commands.autocomplete(categorie=categorie_autocomplete)
async def edit(interaction: discord.Interaction, categorie: str, user_input: str):
    sd = bot.get_server_data(interaction.guild_id)
    if not are_permisiune(interaction, sd, "edit"):
        return await interaction.response.send_message("❌ N-ai voie!", ephemeral=True)
    
    
    target_id = None
    target_name = user_input
    categorie = categorie.lower()
    
    if user_input.startswith('<@') and user_input.endswith('>'):
        target_id = user_input.replace('<@!', '').replace('<@', '').replace('>', '')
    
    elif user_input.isdigit():
        target_id = user_input
    
    else:
        member = discord.utils.get(interaction.guild.members, display_name=user_input)
        if member:
            target_id = str(member.id)
            target_name = member.display_name

    if not target_id:
        return await interaction.response.send_message("❌ Nu am putut identifica utilizatorul. Introdu un ID valid sau dă-i tag.", ephemeral=True)

    
    if categorie == "modificare id discord":        
        return await interaction.response.send_modal(MigrareIDModal(interaction.guild_id, target_id))

    
    config = {
        "sanctiuni active": {
            "path": f'/servers/{interaction.guild_id}/sanctiuni/{target_id}',
            "fields": [("tip", "Tip (FW/AV/Amenda)"), ("motiv", "Motiv"), ("data_acordarii", "Data Acordarii"), ("data_expirarii", "Data Expirarii"), ("acordat_de", "Acordat de")]
        },
        "istoric sanctiuni": {
            "path": f'/servers/{interaction.guild_id}/istoric_sanctiuni/{target_id}',
            "fields": [("tip", "Tip"), ("motiv", "Motiv"), ("data", "Data"), ("autor_nume", "Acordat de(nume discord)")]
        },
        "membri": {
            "path": f'/servers/{interaction.guild_id}/membri_activi/{target_id}',
            "fields": [("nume_joc", "Nume Joc"), ("rank", "Rank"), ("zile_factiune", "Zile Totale"), ("zile_invoire", "Zile Invoire"), ("data_admitere", "Data Admitere")]
        },
        "invoiri": {
            "path": f'/servers/{interaction.guild_id}/invoiri/{target_id}',
            "fields": [("motiv", "Motiv"), ("expira_la", "Expira la"), ("tip", "Tip(normala/ms)"), ("autor", "Acordat de(nume discord)")]
        },
        "inactivitate": {
            "path": f'/servers/{interaction.guild_id}/ultima_sansa/{target_id}',
            "fields": [("nume", "Numele membrului"), ("termen", "Data pana poate intra")]
        },
        "functii": {
            "path": f'/servers/{interaction.guild_id}/functii',
            "fields": [("admiteretest", "Un jucator poate fi bagat numai daca a dat testul[/admiteretest](**true/false**)"), ("obligatie_addjucator_admitere", "Acesta trebuie sa se afle in "), ("status", "Status")]
        }
    }

    if categorie not in config and categorie != "Modificare ID Discord":
        return await interaction.response.send_message(f"❌ Categoria `{categorie}` nu este configurată.", ephemeral=True)

    c_info = config[categorie]
    ref = db.reference(c_info["path"])
    data = ref.get()

    if not data:
        return await interaction.response.send_message(f"🚫 Nu există date pentru ID-ul `{target_id}` în categoria {categorie.capitalize()}.", ephemeral=True)

    
    display_label = target_name if target_name != target_id else f"ID: {target_id}"

    if isinstance(data, dict) and categorie in ["sanctiuni active", "istoric sanctiuni"]:
        view = EditSanctiuniView(display_label, data, ref, c_info["fields"])
        await interaction.response.send_message(f"📂 Selectează o intrare din **{categorie.capitalize()}** pentru {display_label}:", view=view, ephemeral=True)
    else:
        view = ActionButtons(None, data, ref, c_info["fields"])
        await interaction.response.send_message(f"📝 Editezi datele curente pentru **{categorie.capitalize()}** ({display_label}):", view=view, ephemeral=True)

class EditSanctiuniView(discord.ui.View):
    def __init__(self, display_name, istoric, ref, fields):
        super().__init__(timeout=None)
        self.istoric = istoric
        self.ref = ref
        self.fields = fields
        
        options = []
        
        sorted_items = sorted(istoric.items(), key=lambda x: x[1].get('data', ''), reverse=True)
        
        for s_id, data in sorted_items[:25]:
            label = f"{data.get('tip', 'S')} - {data.get('motiv', 'Fara motiv')[:50]}"
            options.append(discord.SelectOption(label=label, value=s_id, description=f"Data: {data.get('data', 'N/A')}"))
        
        select = discord.ui.Select(placeholder="Alege intrarea exacta...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        s_id = interaction.data['values'][0]
        entry_data = self.istoric[s_id]
        
        view = ActionButtons(s_id, entry_data, self.ref, self.fields)
        await interaction.response.send_message(f"Ai selectat ID: `{s_id}`. Ce doresti sa faci?", view=view, ephemeral=True)

@bot.tree.command(name="add_global_word", description="[STAFF] Adaugă un cuvânt interzis pentru TOATE serverele", guild=GUILD_STAFF)
async def add_global_word(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=True)
    
    
    ref = db.reference('security_global/blacklist')
    cuvinte = ref.get() or []
    
    text_f = text.lower().strip()
    if text_f not in cuvinte:
        cuvinte.append(text_f)
        ref.set(cuvinte)
        await interaction.followup.send(f"✅ Adăugat global: `{text_f}`. Toate serverele sunt acum protejate.")
    else:
        await interaction.followup.send("ℹ️ Cuvântul există deja în baza de date globală.")

@bot.tree.command(name="refresh_limited", description="[STAFF] Scanare istoric cu raport TOTAL", guild=GUILD_STAFF)
async def refresh_limited(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    servere_vizate = [795348393005416489, 905520317047373834, 784166739558531072, 765580654632501258] 
    db_root = db.reference('/').get() or {}
    cuvinte_global = db_root.get('security_global', {}).get('blacklist', [])
    
    if not cuvinte_global:
        return await interaction.followup.send("❌ Blacklist gol.")

    timp_limita = datetime.now() - timedelta(days=1)
    stats = {"mesaje": 0, "canale": 0, "sanctiuni": 0}
    raport_detaliat = []

    await interaction.followup.send(f"🚀 Pornit scanarea pe {len(servere_vizate)} servere...")

    for s_id in servere_vizate:
        guild = bot.get_guild(s_id)
        if not guild: continue
        
        
        server_config = db_root.get('servers', {}).get(str(s_id), {})
        canal_anunturi_id = server_config.get('canal_anunturi')
        canal_anunturi = guild.get_channel(int(canal_anunturi_id)) if canal_anunturi_id else None

        for channel in guild.text_channels:
            try:
                stats["canale"] += 1
                async for message in channel.history(after=timp_limita, limit=2000):
                    if message.author.bot: continue
                    stats["mesaje"] += 1
                    
                    continut = message.content.lower()
                    trigger = next((c for c in cuvinte_global if c.lower() in continut), None)
                    
                    if trigger:
                        try:
                            
                            info_jucator = f"NICK: {message.author.display_name} | ID: {message.author.id} | TAG: @{message.author.name}"
                            log_entry = (
                                f"🌐 SERVER: {guild.name}\n"
                                f"👤 {info_jucator}\n"
                                f"💬 MESAJ: {message.content}\n"
                                f"🎯 TRIGGER: {trigger}\n"
                                f"⏳ SANCTIUNE: Mute 28 zile\n"
                                f"{'='*50}"
                            )
                            raport_detaliat.append(log_entry)

                            
                            if canal_anunturi:
                                embed = discord.Embed(title="🛡️ Auto-Moderare (refresh): Sancțiune", color=discord.Color.red(), timestamp=datetime.now())
                                embed.add_field(name="👤 Utilizator", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                                embed.add_field(name="🚫 Mesaj șters", value=f"```{message.content}```", inline=False)
                                embed.add_field(name="🎯 Trigger", value=f"`{trigger}`", inline=True)
                                embed.add_field(name="⏳ Sancțiune", value="Mute: **28 zile**", inline=True)
                                embed.set_footer(text="Liderul/co-liderul este rugat să ia măsuri(Ban/Kick/Unmute/etc.).")
                                await canal_anunturi.send(embed=embed)

                            
                            try:
                                await message.author.timeout(timedelta(days=28), reason=f"Global Scan: {trigger}")
                            except Exception as e:
                                print(f"Eroare la timeout: {e}")
                            await message.reply(f"{message.author.mention} Cont spart? Pentru asta ai mute 28 de zile.")
                            await message.delete()
                            stats["sanctiuni"] += 1

                        except Exception as e:
                            print(f"Eroare la {message.author}: {e}")
            except: continue

    
    rezumat = (
        f"📊 **REZUMAT FINAL**\n"
        f"• Servere: `{len(servere_vizate)}` | Canale: `{stats['canale']}`\n"
        f"• Mesaje scanate: `{stats['mesaje']}`\n"
        f"• Sancțiuni date: `{stats['sanctiuni']}`\n"
    )

    if not raport_detaliat:
        await interaction.followup.send(rezumat + "✅ Totul este curat.")
    else:
        log_complet = "\n".join(raport_detaliat)
        file = discord.File(io.BytesIO(log_complet.encode()), filename="RAPORT_SECURITATE.txt")
        await interaction.followup.send(content=rezumat, file=file)



@bot.tree.command(name="list_global_words", description="[STAFF] Arată toate cuvintele din blacklist-ul global", guild=GUILD_STAFF)
async def list_global_words(interaction: discord.Interaction):
    
    await interaction.response.defer(ephemeral=True)
    
    cuvinte = db.reference('security_global/blacklist').get() or []
    
    if not cuvinte:
        return await interaction.followup.send("Empty blacklist.", ephemeral=True)
    
    header = "📋 **Cuvinte monitorizate global:**\n"
    pagini = []
    text_curent = ""

    
    cuvinte_sortate = sorted(list(cuvinte))

    for c in cuvinte_sortate:
        linie = f"- {c}\n"
        
        if len(text_curent) + len(linie) > 1900:
            pagini.append(text_curent)
            text_curent = linie
        else:
            text_curent += linie

    
    if text_curent:
        pagini.append(text_curent)

    
    await interaction.followup.send(f"{header}{pagini[0]}", ephemeral=True)

    
    for i in range(1, len(pagini)):
        await interaction.followup.send(f"📋 **(Continuare):**\n{pagini[i]}", ephemeral=True)

@bot.tree.command(name="remove_global_word", description="[STAFF] Scoate un cuvânt din blacklist-ul global", guild=GUILD_STAFF)
@app_commands.describe(text="Cuvântul exact pe care vrei să îl scoți")
async def remove_global_word(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=True)
    
    ref = db.reference('security_global/blacklist')
    cuvinte = ref.get() or []
    
    text_f = text.lower().strip()
    if text_f in cuvinte:
        cuvinte.remove(text_f)
        ref.set(cuvinte)
        await interaction.followup.send(f"🗑️ Am scos `{text_f}` din monitorizarea globală.")
    else:
        await interaction.followup.send(f"❌ Cuvântul `{text_f}` nu a fost găsit în listă.")


@bot.tree.command(name="list_servers", description="[STAFF] Arată toate serverele în care se află botul", guild=GUILD_STAFF)
async def list_servers(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    
    guilds = sorted(bot.guilds, key=lambda g: g.member_count, reverse=True)
    
    total_membri = sum(g.member_count for g in guilds)
    
    
    linii_raport = [
        f"📊 STATISTICI BOT: {len(guilds)} Servere | {total_membri} Membri totali",
        f"{'='*60}"
    ]
    
    for i, guild in enumerate(guilds, 1):
        data_intrare = guild.me.joined_at.strftime("%d/%m/%Y") if guild.me.joined_at else "Necunoscută"
        linii_raport.append(
            f"{i}. 🏰 NUME: {guild.name}\n"
            f"   🆔 ID: {guild.id}\n"
            f"   👥 MEMBRI: {guild.member_count}\n"
            f"   📅 INTRAT PE: {data_intrare}\n"
            f"{'-'*40}"
        )

    text_final = "\n".join(linii_raport)

    
    if len(text_final) > 1900:
        file = discord.File(io.BytesIO(text_final.encode()), filename="lista_servere.txt")
        await interaction.followup.send(content=f"✅ Am găsit `{len(guilds)}` servere. Lista completă este în fișier:", file=file)
    else:
        await interaction.followup.send(content=f"```\n{text_final}\n```")

PESTI_CONFIG = [
    ("🐟 Pește Comun", 60, 10, 50, discord.Color.light_grey()),
    ("🐠 Pește Tropical", 25, 60, 150, discord.Color.blue()),
    ("🐡 Pește Balon", 10, 200, 400, discord.Color.gold()),
    ("🦈 Rechin", 4, 1000, 2500, discord.Color.dark_blue()),
    ("🐋 Balenă Albastră", 1, 5000, 15000, discord.Color.purple())
]

@bot.tree.command(name="toggle_games", description="Configurează sistemul de jocuri")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(stare="Activ sau Inactiv", canale="Tag la canalele permise (ex: #canal1 #canal2)")
async def toggle_games(interaction: discord.Interaction, stare: bool, canale: str = None):
    guild_id = str(interaction.guild_id)
    
    channel_ids = []
    if canale:
        
        
        found_ids = re.findall(r'\d+', canale)
        channel_ids = [int(cid) for cid in found_ids]

    config_data = {
        "active": stare,
        "channels": channel_ids
    }
    
    db.reference(f'servers/{guild_id}/games').set(config_data)
    
    msg = f"✅ Jocurile au fost **{'Activate' if stare else 'Dezactivate'}**."
    if channel_ids:
        msg += f"\n📍 Canale permise: {', '.join([f'<#{c}>' for c in channel_ids])}"
    else:
        msg += "\n🌍 Permise pe toate canalele (deoarece nu ai specificat niciunul)."
        
    await interaction.response.send_message(msg)



@bot.tree.command(name="slots", description="Joacă la păcănele virtuale (Slots)")
@games_enabled()
async def slots(interaction: discord.Interaction, pariu: int):
    if pariu < 5:
        return await interaction.response.send_message("❌ Pariul minim este de 5 bani!", ephemeral=True)
    
    
    if pariu > 1000000: 
        return await interaction.response.send_message("❌ Pariul maxim permis este de 1000000 bani!", ephemeral=True)

    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild_id)
    user_ref = db.reference(f'servers/{guild_id}/economie/{user_id}')
    
    data = user_ref.get() or {}
    bani_actuali = data.get('bani', 0)

    if bani_actuali < pariu:
        return await interaction.response.send_message(f"❌ N-ai bani! Ai doar `{bani_actuali}` bani.", ephemeral=True)

    
    
    simboluri = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣", "🍃", "🎃"]
    
    s1 = random.choice(simboluri)
    s2 = random.choice(simboluri)
    s3 = random.choice(simboluri)

    win = False
    multiplicator = 0

    
    if s1 == s2 == s3:
        win = True
        if s1 == "7️⃣": multiplicator = 15    
        elif s1 == "💎": multiplicator = 8     
        elif s1 == "🍒": multiplicator = 5     
        else: multiplicator = 3
    
    
    
    
    elif s1 == s2 or s2 == s3 or s1 == s3:
        
        if random.random() < 0.5: 
            win = True
            multiplicator = 1.2 
        else:
            win = False

    if win:
        
        
        castig_total = int(pariu * multiplicator)
        nou_sold = (bani_actuali - pariu) + castig_total
        rezultat_text = f"✨ **CÂȘTIGĂTOR!** Ai primit `{castig_total}` bani!"
        culoare = discord.Color.gold()
    else:
        nou_sold = bani_actuali - pariu
        rezultat_text = "Ai pierdut. Mai încearcă o dată! 💸"
        culoare = discord.Color.red()

    user_ref.update({'bani': nou_sold})

    embed = discord.Embed(title="🎰 PĂCĂNELE 🎰", description=f"{rezultat_text}\n")
    embed.set_footer(text=f"Sold nou: {nou_sold:,} | Pariu: {pariu:,}") 
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="fish", description="Pescuiește pentru bani virtuali")
@games_enabled()
@app_commands.checks.cooldown(1, 30.0)
async def fish(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild_id)
    
    sansa = random.randint(1, 100)
    ales = ("👟 Ghetă Veche", 5, discord.Color.dark_orange()) 

    prag = 0
    
    for nume, prob, p_min, p_max, culoare in sorted(PESTI_CONFIG, key=lambda x: x[1]):
        prag += prob
        if sansa <= prag:
            ales = (nume, random.randint(p_min, p_max), culoare)
            break

    nume_peste, valoare, culoare_embed = ales
    
    
    user_ref = db.reference(f'servers/{guild_id}/economie/{user_id}')
    current_data = user_ref.get() or {}
    noul_sold = current_data.get('bani', 0) + valoare
    user_ref.update({'bani': noul_sold})

    embed = discord.Embed(title="🎣 Rezultat Pescuit", description=f"Ai prins: **{nume_peste}**!", color=culoare_embed)
    embed.add_field(name="💰 Valoare", value=f"{valoare} bani")
    embed.set_footer(text=f"Portofel: {noul_sold} bani")
    await interaction.response.send_message(embed=embed)
@fish.error
async def fish_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        
        secunde_ramase = round(error.retry_after, 1)
        
        
        await interaction.response.send_message(
            f"⏳ Ai răbdare, pescarule! Firul undiței s-a încurcat. \n"
            f"Mai poți pescui peste **{secunde_ramase} secunde**.", 
            ephemeral=True
        )
    else:
        
        print(f"Eroare neprevăzută la fish: {error}")

@bot.tree.command(name="coinflip", description="Pariază la datul cu banul")
@games_enabled()
@app_commands.describe(suma="Suma de pariat", alegere="Cap sau Pajură")
@app_commands.choices(alegere=[
    app_commands.Choice(name="Cap", value="cap"),
    app_commands.Choice(name="Pajură", value="pajura")
])
async def coinflip(interaction: discord.Interaction, suma: int, alegere: str):
    if suma < 10: return await interaction.response.send_message("❌ Pariul minim este de 10 bani.", ephemeral=True)
    
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild_id)
    user_ref = db.reference(f'servers/{guild_id}/economie/{user_id}')
    bani_actuali = (user_ref.get() or {}).get('bani', 0)

    if bani_actuali < suma:
        return await interaction.response.send_message(f"❌ Bani insuficienți! Ai doar `{bani_actuali}`.", ephemeral=True)

    rezultat = random.choice(["cap", "pajura"])
    win = (alegere == rezultat)
    nou_sold = bani_actuali + suma if win else bani_actuali - suma
    
    user_ref.update({'bani': nou_sold})

    embed = discord.Embed(
        title="🪙 Coinflip Result",
        description=f"A picat **{rezultat.upper()}**!\n" + ("✅ Ai câștigat!" if win else "❌ Ai pierdut..."),
        color=discord.Color.green() if win else discord.Color.red()
    )
    embed.add_field(name="Sold Nou", value=f"{nou_sold} bani")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_infotest", description="Setează mesajul de informații pentru teste")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    titlu="Titlul Embed-ului (ex: Regulament Teste)", 
    descriere="Mesajul principal (folosește \n pentru rând nou)",
    culoare="Cod HEX (ex: #ff0000 pentru roșu) sau lăsați gol"
)
async def set_infotest(interaction: discord.Interaction, titlu: str, descriere: str, culoare: str = "#2b2d31"):
    guild_id = str(interaction.guild_id)
    if not are_permisiune(interaction, guild_id, "edit"):
        return await interaction.response.send_message("❌ N-ai voie!", ephemeral=True)
    
    
    culoare_hex = culoare.replace("#", "")
    try:
        culoare_int = int(culoare_hex, 16)
    except ValueError:
        return await interaction.response.send_message("❌ Codul culorii HEX este invalid! Exemplu valid: `#ff0000`", ephemeral=True)

    
    db.reference(f'servers/{guild_id}/infotest').set({
        "titlu": titlu,
        "descriere": descriere.replace("\\n", "\n"), 
        "culoare": culoare_int
    })

    await interaction.response.send_message("✅ Mesajul pentru `/infotest` a fost configurat cu succes!", ephemeral=True)

@bot.tree.command(name="infotest", description="Afișează informațiile despre teste configurate")
async def infotest(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    
    
    data = db.reference(f'servers/{guild_id}/infotest').get()

    if not data:
        return await interaction.response.send_message(
            "❌ Nu a fost configurat niciun mesaj de info. Folosește `/set_infotest` mai întâi!", 
            ephemeral=True
        )

    
    embed = discord.Embed(
        title=data.get("titlu", "Informații Teste"),
        description=data.get("descriere", "Nicio descriere setată."),
        color=data.get("culoare", 0x2b2d31)
    )
    
    
    embed.set_footer(text=f"Cerut de {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = datetime.now()

    
    await interaction.response.send_message(embed=embed)

@bot.command(name="reload")
@commands.is_owner()
async def reload(ctx, extension: str = None):
    
    if not extension:
        
        reloaded = []
        errors = []
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                ext_name = f'cogs.{filename[:-3]}'
                try:
                    await bot.reload_extension(ext_name)
                    reloaded.append(filename)
                except Exception as e:
                    errors.append(f"❌ {filename}: {e}")
        
        msg = ""
        if reloaded: msg += f"✅ Reincarcate: {', '.join(reloaded)}\n"
        if errors: msg += f"⚠️ Erori:\n" + "\n".join(errors)
        return await ctx.send(msg or "Nu am gasit module.")

    
    try:
        target = extension if extension.startswith('cogs.') else f'cogs.{extension}'
        await bot.reload_extension(target)
        await ctx.send(f"✅ Modulul `{target}` a fost reincarcat!")
    except Exception as e:
        await ctx.send(f"❌ Eroare la `{extension}`:\n```{e}```")

@reload.error
async def reload_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("⛔ Doar proprietarul poate folosi aceasta comanda.")

@bot.command(name="copy_role_perms")
@commands.has_permissions(administrator=True)
async def copy_role_perms(ctx, sursa: discord.Role, *destinatii: discord.Role):
    print(f"DEBUG: Comanda a fost apelată de {ctx.author}") 
    if not destinatii:
        return await ctx.send("❌ Trebuie să menționezi cel puțin un rol destinație!")

    perms_sursa = sursa.permissions
    succes = []
    erori = []

    for rol in destinatii:
        try:
            await rol.edit(permissions=perms_sursa, reason=f"Sync de la {sursa.name} (Autor: {ctx.author})")
            succes.append(rol.name)
        except Exception as e:
            erori.append(f"{rol.name} ({e})")

    msg = f"✅ Permisiuni copiate de la {sursa.mention} la: **{', '.join(succes)}**"
    if erori:
        msg += f"\n⚠️ Erori la: {', '.join(erori)}"
    
    await ctx.send(msg)

@bot.command(name="copy_channel_perms")
@commands.has_permissions(administrator=True)
async def copy_channel_perms(ctx, sursa: discord.TextChannel, *destinatii: discord.TextChannel):
    if not destinatii:
        return await ctx.send("❌ Trebuie să menționezi cel puțin un canal destinație!")

    overwrites_sursa = sursa.overwrites
    succes = []
    erori = []

    for canal in destinatii:
        try:
            await canal.edit(overwrites=overwrites_sursa, reason=f"Sync de la {sursa.name} (Autor: {ctx.author})")
            succes.append(canal.mention)
        except Exception as e:
            erori.append(f"{canal.name} ({e})")

    embed = discord.Embed(title="🔄 Sincronizare Canale", color=discord.Color.blue())
    embed.add_field(name="Sursă", value=sursa.mention, inline=False)
    embed.add_field(name="Destinații reușite", value=", ".join(succes) if succes else "Niciuna", inline=False)
    
    if erori:
        embed.add_field(name="❌ Erori", value="\n".join(erori), inline=False)

    await ctx.send(embed=embed)

import asyncio


@bot.tree.command(name="ban", description="Dă ban unui membru (Permanent sau Temporar)")
@app_commands.describe(
    membru="Jucătorul care primește ban", 
    motiv="Motivul banului", 
    durata="Ex: 7d, 2h, 30m sau 'perm' pentru permanent"
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membru: discord.Member, motiv: str, durata: str = "perm"):
    await interaction.response.defer() 
    sd = bot.get_server_data(interaction.guild_id)
    if not are_permisiune(interaction, sd, "sanctiune"):
        return await interaction.followup.send("❌ Nu ai permisiunea de a da ban!", ephemeral=True)

    
    timp_secunde = 0
    durata_text = "Permanent"
    is_temp = False

    if durata.lower() != "perm":
        unitati = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            
            valoare = int(durata[:-1])
            unitate = durata[-1].lower()
            if unitate in unitati:
                timp_secunde = valoare * unitati[unitate]
                durata_text = f"{valoare} {unitate}"
                is_temp = True
            else:
                return await interaction.followup.send("❌ Format durată invalid! Folosește: 30m, 2h, 7d sau perm.", ephemeral=True)
        except:
            return await interaction.followup.send("❌ Durată invalidă! Exemplu corect: `7d` (7 zile) sau `perm`.", ephemeral=True)

    
    dm_trimis = "✅ DM Trimis"
    try:
        embed_dm = discord.Embed(title="🚫 Ai primit BAN!", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed_dm.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed_dm.add_field(name="Server", value=interaction.guild.name, inline=True)
        embed_dm.add_field(name="Durată", value=durata_text, inline=True)
        embed_dm.add_field(name="Motiv", value=motiv, inline=False)
        embed_dm.add_field(name="De către", value=interaction.user.mention, inline=True)
        embed_dm.set_footer(text="Dacă consideri că este o greșeală, contactează conducerea.")
        
        await membru.send(embed=embed_dm)
    except:
        dm_trimis = "❌ DM Închis (nu a putut fi contactat)"

    
    try:
        await membru.ban(reason=f"Admin: {interaction.user} | Motiv: {motiv} | Timp: {durata_text}")
    except discord.Forbidden:
        return await interaction.followup.send("❌ Nu am permisiunea de a da ban acestui membru (ierarhie roluri)!")

    
    embed_fin = discord.Embed(title="🔨 Membru banat", color=discord.Color.dark_red())
    embed_fin.add_field(name="Utilizator", value=f"{membru.mention} (`{membru.id}`)", inline=True)
    embed_fin.add_field(name="Tip", value="TEMPORAR" if is_temp else "PERMANENT", inline=True)
    embed_fin.add_field(name="Durată", value=durata_text, inline=True)
    embed_fin.add_field(name="Motiv", value=motiv, inline=False)
    embed_fin.set_footer(text=f"Status DM: {dm_trimis}")

    await interaction.followup.send(embed=embed_fin)

    
    if is_temp:
        await asyncio.sleep(timp_secunde)
        try:
            await interaction.guild.unban(membru, reason="Expirare ban temporar")
            print(f"🔓 Ban-ul lui {membru.name} a expirat.")
        except Exception as e:
            print(f"Eroare la unban automat: {e}")

class DetaliiModal(discord.ui.Modal, title="Detalii Suplimentare"):
    raspuns = discord.ui.TextInput(
        label="Introdu detalii aici:",
        placeholder="Scrie aici motivul sau detaliile...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=5,
        max_length=200
    )

    def __init__(self, user_id, view, guild_id):
        super().__init__()
        self.user_id = user_id
        self.view = view
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        
        db.reference(f"turneu_{self.guild_id}/raspunsuri/{self.user_id}").update({
            "detalii": self.raspuns.value
        })

        
        await interaction.response.send_message(f"✅ Detaliile au fost salvate!", ephemeral=True)
        
        
        await self.view.update_embed(self.guild_id)

class ChestionarView(discord.ui.View):
    def __init__(self, membri_activi=None, log_channel=None, intrebare_text=None, guild_id=None):
        
        super().__init__(timeout=None)
        self.log_channel = log_channel
        self.intrebare_text = intrebare_text
        self.guild_id = guild_id

    def gaseste_guild_id(self, user_id):
        
        toate_datele = db.reference().get() or {}
        for cheie, date in toate_datele.items():
            if cheie.startswith("turneu_"):
                raspunsuri = date.get('raspunsuri', {})
                if user_id in raspunsuri:
                    
                    return cheie.replace("turneu_", "")
        return None

    async def update_embed(self, guild_id):
        
        data_turneu = db.reference(f"turneu_{guild_id}").get()
        if not data_turneu: return

        sd = bot.get_server_data(guild_id)
        membri_info = sd.get("membri_activi", {})
        raspunsuri = data_turneu.get('raspunsuri', {})

        lista_sortata = []
        for uid, resp in raspunsuri.items():
            info_extra = membri_info.get(uid, {})
            
            
            def safe_int(val):
                if not val: return 0
                try:
                    
                    curat = "".join(filter(str.isdigit, str(val)))
                    return int(curat) if curat else 0
                except: return 0

            lista_sortata.append({
                "uid": uid,
                "nume": resp.get('nume', 'Necunoscut'),
                "optiune": resp.get('optiune', '⏳ Nu a răspuns'),
                "detalii": resp.get('detalii', '-'),
                "rank": safe_int(info_extra.get('rank', 0)),
                "zile": safe_int(info_extra.get('zile_factiune', 0)) 
            })
        lista_sortata.sort(key=lambda x: (x['rank'], x['zile']), reverse=True)

        
        embeds = []
        current_embed = discord.Embed(title="📊 Rezultate Turneu", color=discord.Color.gold())
        current_embed.description = f"**Întrebare:** {data_turneu.get('intrebare', 'Turneu active')}\n\n"
        
        desc_acum = ""
        
        for item in lista_sortata:
            status = f"**{item['optiune']}**"
            if item['detalii'] != "-":
                status += f" (📝 *{item['detalii']}*)"
            
            linie = f"R{item['rank']} | **{item['nume']}** ({item['zile']}z) -> {status}\n"

            
            if len(desc_acum) + len(linie) > 3800:
                
                current_embed.description += desc_acum
                embeds.append(current_embed)
                
                
                current_embed = discord.Embed(title="📊 Rezultate Turneu (Continuare)", color=discord.Color.gold())
                desc_acum = linie
            else:
                desc_acum += linie

        
        current_embed.description += desc_acum
        embeds.append(current_embed)

        
        try:
            chan_id = data_turneu.get('canal_log_id')
            msg_id = data_turneu.get('message_id')
            channel = bot.get_channel(chan_id)
            if channel:
                msg = await channel.fetch_message(msg_id)
                
                await msg.edit(embeds=embeds) 
        except Exception as e:
            print(f"Eroare la update embed (safety): {e}")

    async def handle_click(self, interaction, optiune):
        
        user_id = str(interaction.user.id)
        g_id = self.guild_id or self.gaseste_guild_id(user_id)

        if not g_id:
            return await interaction.response.send_message("❌ Server negăsit.", ephemeral=True)

        
        
        status_final = optiune 

        
        if optiune in ["Particip la câteva", "Nu sunt sigur"]:
            
            await interaction.response.send_modal(DetaliiModal(user_id, self, g_id))
            
            
            db.reference(f"turneu_{g_id}/raspunsuri/{user_id}").update({
                "optiune": status_final
            })
        else:
            
            await interaction.response.defer(ephemeral=True)
            
            db.reference(f"turneu_{g_id}/raspunsuri/{user_id}").update({
                "optiune": status_final,
                "detalii": "-" 
            })
            
            await self.update_embed(g_id)
            await interaction.followup.send(f"✅ Status actualizat: **{status_final}**", ephemeral=True)

    
    @discord.ui.button(label="DA, particip", style=discord.ButtonStyle.success, custom_id="btn_turneu_da")
    async def particip_da(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, "Prezent")

    @discord.ui.button(label="Particip la câteva", style=discord.ButtonStyle.primary, custom_id="btn_turneu_partial")
    async def particip_partial(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, "Particip la câteva")

    @discord.ui.button(label="NU pot veni", style=discord.ButtonStyle.danger, custom_id="btn_turneu_nu")
    async def particip_nu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, "Absent")

    @discord.ui.button(label="Nu sunt sigur", style=discord.ButtonStyle.secondary, custom_id="btn_turneu_nesigur")
    async def particip_nesigur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_click(interaction, "Nu sunt sigur")

@bot.command(name="turneu")
@commands.has_permissions(administrator=True)
async def turneu(ctx, canal_log: discord.TextChannel):
    
    INTREBARE_TEXT = "Salut! Te rugam sa spui daca porti participa la turneu."
    
    
    sd = bot.get_server_data(ctx.guild.id)
    membri_activi = sd.get("membri_activi", {})

    if not membri_activi:
        return await ctx.send("❌ Nu există membri activi în baza de date.")

    
    
    structura_initiala = {}
    for m_id, info in membri_activi.items():
        structura_initiala[m_id] = {
            'nume': info.get('nume_joc', 'Necunoscut'),
            'optiune': '⏳ Nu a răspuns',
            'detalii': '-'
        }

    
    embed_incarcare = discord.Embed(title="📊 Rezultate Turneu", description="Se generează tabelul...", color=discord.Color.blue())
    msg_log = await canal_log.send(embed=embed_incarcare)

    
    db.reference(f"turneu_{ctx.guild.id}").set({
        "canal_log_id": canal_log.id,
        "message_id": msg_log.id,
        "intrebare": INTREBARE_TEXT,
        "raspunsuri": structura_initiala
    })
    

    await ctx.send(f"⏳ Încep trimiterea către `{len(membri_activi)}` membri...")

    
    view = ChestionarView(membri_activi, canal_log, INTREBARE_TEXT, guild_id=ctx.guild.id)
    
    
    await view.update_embed(ctx.guild.id)

    succes = 0
    esec = 0

    for user_id_str in membri_activi.keys():
        try:
            user = await bot.fetch_user(int(user_id_str))
            embed_dm = discord.Embed(
                title="📢 Anunț Facțiune",
                description=INTREBARE_TEXT,
                color=discord.Color.blue()
            )
            embed_dm.set_footer(text="Apasă pe un buton de mai jos pentru a răspunde.")
            
            
            await user.send(embed=embed_dm, view=view)
            succes += 1
            await asyncio.sleep(0.5) 
        except Exception as e:
            print(f"Eroare DM {user_id_str}: {e}")
            esec += 1

    await ctx.send(f"✅ Proces finalizat!\n📬 Trimise: {succes}\n🚫 Eșuate: {esec}")

@bot.command(name="turneu_fix")
@commands.has_permissions(administrator=True)
async def turneu_fix(ctx, message_id: int):
    try:
        mesaj = await ctx.channel.fetch_message(message_id)
        if not mesaj.embeds:
            return await ctx.send("❌ Mesajul nu are Embed.")
        
        embed_vechi = mesaj.embeds[0]
        sd = bot.get_server_data(ctx.guild.id)
        membri_activi = sd.get("membri_activi", {})
        
        
        date_existente = db.reference(f"turneu_{ctx.guild.id}/raspunsuri").get() or {}
        raspunsuri_noi = {}

        await ctx.send("⏳ Sincronizez datele și păstrez voturile...")

        
        for field in embed_vechi.fields:
            nume_jucator = field.name.strip().replace("*", "")
            valoare_text = field.value.lower()

            
            u_id = None
            for m_id, info in membri_activi.items():
                if info.get('nume_joc') == nume_jucator:
                    u_id = m_id
                    break
            
            if u_id:
                
                optiune = "⏳ Nu a răspuns"
                detalii = "-"
                
                if "prezent" in valoare_text or "da, particip" in valoare_text: 
                    optiune = "Prezent"
                elif "absent" in valoare_text or "nu pot veni" in valoare_text or "nu particip" in valoare_text: 
                    optiune = "Absent"
                elif "câteva" in valoare_text: 
                    optiune = "Particip la câteva"
                elif "sigur" in valoare_text: 
                    optiune = "Nu sunt sigur"

                
                if "(" in field.value:
                    try:
                        detalii = field.value.split("(")[1].split(")")[0].replace("📝", "").strip()
                    except: pass

                raspunsuri_noi[u_id] = {
                    "nume": nume_jucator,
                    "optiune": optiune,
                    "detalii": detalii
                }

        
        for m_id, info in membri_activi.items():
            if m_id not in raspunsuri_noi:
                raspunsuri_noi[m_id] = {
                    "nume": info.get('nume_joc', 'Necunoscut'),
                    "optiune": "⏳ Nu a răspuns",
                    "detalii": "-"
                }

        
        db.reference(f"turneu_{ctx.guild.id}").update({
            "canal_log_id": ctx.channel.id,
            "message_id": message_id,
            "intrebare": embed_vechi.title or "Turneu Actualizat",
            "raspunsuri": raspunsuri_noi
        })

        
        
        view_temp = ChestionarView(guild_id=ctx.guild.id)
        await view_temp.update_embed(ctx.guild.id)

        
        trimise = 0
        for u_id, date in raspunsuri_noi.items():
            if date['optiune'] == "⏳ Nu a răspuns":
                try:
                    user = await bot.fetch_user(int(u_id))
                    
                    await user.send(f"📢 **Turneu**: {embed_vechi.title}\nTe rugăm să răspunzi:", view=ChestionarView(guild_id=ctx.guild.id))
                    trimise += 1
                    await asyncio.sleep(0.5)
                except: pass

        await ctx.send(f"✅ Sincronizare reușită!\n👥 Total jucători: `{len(raspunsuri_noi)}`\n📩 Mesaje noi trimise: `{trimise}` (doar celor fără răspuns)")

    except Exception as e:
        print(f"EROARE FIX: {e}")
        await ctx.send(f"🔥 Eroare la fix: {e}")

import time


ID_CANAL_PODIUM = 1282287983554465923  
sedinta_activa = False
date_sedinta = {}

@bot.command(name="start_sedinta")
@commands.has_permissions(administrator=True)
async def start_sedinta(ctx):
    global sedinta_activa, date_sedinta
    if sedinta_activa:
        return await ctx.send("⚠️ Ședința este deja pornită!")

    sedinta_activa = True
    date_sedinta = {}
    acum = time.time()

    
    canal_podium = ctx.guild.get_channel(ID_CANAL_PODIUM)
    if not canal_podium:
        return await ctx.send("❌ Nu am găsit canalul de voce. Verifică ID-ul!")

    for member in canal_podium.members:
        if member.bot: continue
        date_sedinta[member.id] = {
            "nume": member.display_name,
            "total_secunde": 0,
            "last_start": acum
        }

    await ctx.send(f"🎙️ **Ședința a început!** Canal de podium: {canal_podium.mention}.")

@bot.event
async def on_voice_state_update(member, before, after):
    global sedinta_activa, date_sedinta
    if not sedinta_activa or member.bot:
        return

    acum = time.time()
    uid = member.id

    
    if uid not in date_sedinta:
        date_sedinta[uid] = {"nume": member.display_name, "total_secunde": 0, "last_start": None}

    
    if after.channel and after.channel.id == ID_CANAL_PODIUM:
        if before.channel is None or before.channel.id != ID_CANAL_PODIUM:
            date_sedinta[uid]["last_start"] = acum
            print(f"DEBUG: {member.display_name} a intrat pe podium.")

    
    elif before.channel and before.channel.id == ID_CANAL_PODIUM:
        if after.channel is None or after.channel.id != ID_CANAL_PODIUM:
            if date_sedinta[uid]["last_start"] is not None:
                durata = acum - date_sedinta[uid]["last_start"]
                date_sedinta[uid]["total_secunde"] += durata
                date_sedinta[uid]["last_start"] = None
                print(f"DEBUG: {member.display_name} a părăsit podiumul. Timp salvat.")

@bot.command(name="verifica_sedinta")
async def verifica_sedinta(ctx):
    if not sedinta_activa:
        return await ctx.send("❌ Nu este nicio ședință în curs.")

    embed = discord.Embed(title="🔎 Monitorizare Podium Live", color=discord.Color.blue())
    desc = ""
    acum = time.time()
    
    for uid, data in date_sedinta.items():
        timp_total = data["total_secunde"]
        if data["last_start"] is not None:
            timp_total += (acum - data["last_start"])
        
        if timp_total > 0:
            min = int(timp_total // 60)
            sec = int(timp_total % 60)
            status = "🎤 Pe Podium" if data["last_start"] else "💤 Absent"
            desc += f"**{data['nume']}**: `{min}m {sec}s` | {status}\n"

    embed.description = desc or "Nimeni nu a intrat pe podium încă."
    await ctx.send(embed=embed)

@bot.command(name="final_sedinta")
@commands.has_permissions(administrator=True)
async def final_sedinta(ctx):
    global sedinta_activa
    if not sedinta_activa: return await ctx.send("❌ Sesiune inactivă.")

    rezultate = []
    acum = time.time()
    for uid, data in date_sedinta.items():
        t = data["total_secunde"]
        if data["last_start"]: t += (acum - data["last_start"])
        if t > 10: 
            rezultate.append((data["nume"], int(t // 60), int(t % 60)))

    rezultate.sort(key=lambda x: x[1], reverse=True)
    
    desc = "\n".join([f"🏆 **{n}**: `{m} min și {s} sec`" for n, m, s in rezultate])
    embed = discord.Embed(title="📊 Raport Final Podium", description=desc, color=discord.Color.gold())
    
    sedinta_activa = False
    await ctx.send("🛑 Monitorizarea s-a încheiat.", embed=embed)

@bot.command(name="dezactivare")
async def dezactivare(ctx: commands.Context):
    
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Doar proprietarul bot-ului poate folosi această comanda.")

    guild_id = str(ctx.guild.id)
    
    
    paths_to_delete = [
        f'servers/{guild_id}',
        f'turneu_{guild_id}'
    ]

    await ctx.send("⏳ Se creează backup al datelor înainte de ștergere...")

    
    SERVER_ID_DESTINATIE = 1397667791846375504  
    CANAL_ID_DESTINATIE = 1496150670917763254   
    

    try:
        
        toate_datele = db.reference('/').get()
        json_string = json.dumps(toate_datele, indent=4, ensure_ascii=False)

        
        breasla = bot.get_guild(SERVER_ID_DESTINATIE)
        if not breasla:
            return await ctx.send("❌ Server no found.")

        canal = breasla.get_channel(CANAL_ID_DESTINATIE)
        if not canal:
            return await ctx.send("❌ Channel no found.")

        
        with io.BytesIO(json_string.encode('utf-8')) as f:
            discord_file = discord.File(f, filename="backup_global.json")
            await canal.send(f"📦 **Backup General Bază de Date**\n📅 Generat la: <t:{int(datetime.now().timestamp())}:F>", file=discord_file)
        
        await ctx.send(f"✅ Backup creat!")

    except Exception as e:
        await ctx.send(f"⚠️ Eroare la crearea backup-ului(check console for more details)")
        print(f"Eroare la backup: {e}")
        return
    await ctx.send("⏳ Se sterg datele din baza de date...")
    
    try:
        
        for path in paths_to_delete:
            db.reference(path).delete()
        
        await ctx.send("✅ Toate datele au fost sterse cu succes. Bot-ul a parasit serverul.")
        
        
        await ctx.guild.leave()
        
    except Exception as e:
        await ctx.send(f"⚠️ Eroare la stergerea datelor sau la părăsirea serverului (check console for more details)")
        print(f"Eroare: {e}")

class ParticipareView(discord.ui.View):
    def __init__(self, interaction, membri_lista, autor):
        super().__init__(timeout=900)
        self.interaction = interaction
        self.autor = autor
        
        self.date_prezenta = {m_id: {"nume": info["nume_joc"], "status": None, "sanctiune": "Niciuna"} 
                             for m_id, info in membri_lista.items()}
        self.membri_ids = list(self.date_prezenta.keys())
        self.index = 0

    async def genera_embed_pas(self):
        m_id = self.membri_ids[self.index]
        date = self.date_prezenta[m_id]
        embed = discord.Embed(title="📋 Monitorizare Activitate", color=discord.Color.blue())
        embed.description = f"Setează statusul pentru: **{date['nume']}**\nProgres: `{self.index + 1}/{len(self.membri_ids)}`"
        
        status_actual = date['status'] or "Necompletat"
        embed.add_field(name="Status", value=f"`{status_actual}`", inline=True)
        if date['status'] == "Absent":
            sanc_text = "Se va alege în privat" if date['sanctiune'] == "Alegere PV" else date['sanctiune']
            embed.add_field(name="Sancțiune", value=f"`{sanc_text}`", inline=True)
        return embed

    async def actualizeaza_interfata(self, interaction):
        embed = await self.genera_embed_pas()
        m_id = self.membri_ids[self.index]
        is_absent = self.date_prezenta[m_id]["status"] == "Absent"
        
        self.fw_btn.disabled = self.amenda_btn.disabled = self.rp_btn.disabled = self.next_btn.disabled = not is_absent
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Prezent", style=discord.ButtonStyle.green, row=0)
    async def prezent_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        m_id = self.membri_ids[self.index]
        self.date_prezenta[m_id]["status"] = "Prezent"
        self.date_prezenta[m_id]["sanctiune"] = "Niciuna"
        await self.next_pas(interaction)

    @discord.ui.button(label="Absent", style=discord.ButtonStyle.red, row=0)
    async def absent_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.date_prezenta[self.membri_ids[self.index]]["status"] = "Absent"
        await self.actualizeaza_interfata(interaction)

    
    @discord.ui.button(label="Next (Alegere în PV)", style=discord.ButtonStyle.gray, row=0, disabled=True)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        m_id = self.membri_ids[self.index]
        self.date_prezenta[m_id]["sanctiune"] = "Alegere PV"
        
        
        

        await self.next_pas(interaction)

    @discord.ui.button(label="FW", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def fw_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.date_prezenta[self.membri_ids[self.index]]["sanctiune"] = "FW"
        await acorda_sanctiune(interaction, interaction.user, "FW", "Neparticipare RP", 0, self.membru_vizat,
            forced_guild_id=self.guild_id) 
        await self.next_pas(interaction)

    @discord.ui.button(label="Amenda 100kk", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def amenda_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.date_prezenta[self.membri_ids[self.index]]["sanctiune"] = "Amenda 100kk"
        await acorda_sanctiune(interaction, interaction.user, "Amenda", "Neparticipare RP", 100000000, self.membru_vizat,
            forced_guild_id=self.guild_id) 
        await self.next_pas(interaction)

    @discord.ui.button(label="Neparticipare RP", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def rp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.date_prezenta[self.membri_ids[self.index]]["sanctiune"] = "Neparticipare RP"
        await acorda_sanctiune(interaction, interaction.user, "RP Personalizat", "Neparticipare RP", 0, self.membru_vizat,
            forced_guild_id=self.guild_id) 
        await self.next_pas(interaction)

    async def next_pas(self, interaction):
        if self.index < len(self.membri_ids) - 1:
            self.index += 1
            await self.actualizeaza_interfata(interaction)
        else:
            view_final = ReviewParticipareView(self.interaction, self.date_prezenta, self.autor)
            await view_final.send_review(interaction)

class MembruAlegereSanctiuneView(discord.ui.View):
    def __init__(self, guild_id=None, user_id=None, nume_joc=None, canal_anunturi_id=None, membru_vizat=None):
        
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.user_id = user_id
        self.nume_joc = nume_joc
        self.canal_id = canal_anunturi_id
        self.target_guild_id = guild_id 
        self.membru_vizat = membru_vizat 

    
    @discord.ui.button(label="FW", style=discord.ButtonStyle.danger, custom_id="persistent:fw")
    async def fw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.trimite_confirmare(interaction, "FW")
        await acorda_sanctiune(interaction, interaction.user, "FW", "Neparticipare RP", 0, user_vizat=self.membru_vizat, 
                               forced_guild_id=self.target_guild_id)

    @discord.ui.button(label="Amenda 100kk", style=discord.ButtonStyle.secondary, custom_id="persistent:amenda")
    async def amenda(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.trimite_confirmare(interaction, "Amenda 100kk")
        await acorda_sanctiune(interaction, interaction.user, "Amenda", "Neparticipare RP", 100000000, user_vizat=self.membru_vizat, 
                               forced_guild_id=self.target_guild_id)

    @discord.ui.button(label="RP Personalizat", style=discord.ButtonStyle.primary, custom_id="persistent:rp")
    async def rp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.trimite_confirmare(interaction, "RP Personalizat")
        await acorda_sanctiune(interaction, interaction.user, "RP Personalizat", "Neparticipare RP", 0, user_vizat=self.membru_vizat, 
                               forced_guild_id=self.target_guild_id)

    

    async def trimite_confirmare(self, interaction, sanctiune):
        
        
        nume_afisat = self.nume_joc or interaction.user.display_name
        
        await interaction.response.edit_message(content=f"✅ Ai ales sancțiunea: **{sanctiune}**.", view=None)
        
        
        sd = bot.get_server_data(interaction.guild_id or self.guild_id)
        c_id = sd.get("canal_anunturi") if sd else self.canal_id
        
        if c_id:
            canal = bot.get_channel(int(c_id))
            if canal:
                await canal.send(f"ℹ️ Membrul **{nume_afisat}** și-a ales sancțiunea: **{sanctiune}**. (Sanctiunea nu a fost acordata automata, trebuie oferita manual prin comanda [/sanctiune]!)")

class EditSingleMemberView(discord.ui.View):
    def __init__(self, interaction, date_prezenta, autor):
        super().__init__(timeout=300)
        self.main_interaction = interaction
        self.date_prezenta = date_prezenta
        self.autor = autor

        
        options = [discord.SelectOption(label=info["nume"], value=m_id) for m_id, info in date_prezenta.items()]
        self.select = discord.ui.Select(placeholder="Alege membrul...", options=options)
        self.select.callback = self.member_selected
        self.add_item(self.select)

    async def member_selected(self, interaction: discord.Interaction):
        m_id = self.select.values[0]
        
        
        view_edit = ParticipareView(self.main_interaction, {m_id: {"nume_joc": self.date_prezenta[m_id]["nume"]}}, self.autor)
        view_edit.date_prezenta = self.date_prezenta 
        view_edit.index = list(self.date_prezenta.keys()).index(m_id) 
        
        
        async def back_to_review(inter):
            view_rev = ReviewParticipareView(self.main_interaction, view_edit.date_prezenta, self.autor)
            await view_rev.send_review(inter)
        
        view_edit.next_pas = back_to_review
        await view_edit.actualizeaza_interfata(interaction)

class ReviewParticipareView(discord.ui.View):
    def __init__(self, interaction, date_prezenta, autor):
        super().__init__(timeout=600)
        self.interaction = interaction
        self.date_prezenta = date_prezenta
        self.autor = autor

    async def send_review(self, interaction):
        embed = discord.Embed(title="🧐 Review Listă Prezență", color=discord.Color.gold())
        desc = ""
        for m_id, info in self.date_prezenta.items():
            emoji = "✅" if info["status"] == "Prezent" else "❌"
            sanc = f" ({info['sanctiune']})" if info["status"] == "Absent" else ""
            desc += f"{emoji} **{info['nume']}**: {info['status']}{sanc}\n"
        
        embed.description = desc
        embed.set_footer(text="Ești sigur de listă sau vrei să modifici pe cineva?")
        
        if interaction.response.is_done():
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="✅ Postează Raportul", style=discord.ButtonStyle.green)
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        sd = bot.get_server_data(interaction.guild_id)
        canal_id = sd.get("canal_anunturi")
        
        prezenti = []
        absenti_text = ""

        for m_id, info in self.date_prezenta.items():
            if info["status"] == "Prezent":
                prezenti.append(info["nume"])
            else:
                sanc_display = info["sanctiune"]
                if info["sanctiune"] == "Alegere PV":
                    sanc_display = "⌛ Se alege în privat..."
                    
                    try:
                        user = await bot.fetch_user(int(m_id))
                        view_pv = MembruAlegereSanctiuneView(interaction.guild_id, m_id, info["nume"], canal_id)
                        await user.send(
                            content=f"👋 Salut **{info['nume']}**! Ai fost marcat ca **Absent** la activitate.\n"
                                    f"Organizatorul te-a lăsat pe tine să alegi sancțiunea pe care o vei primi. Te rugăm să apeși pe un buton:",
                            view=view_pv
                        )
                    except: pass
                else:
                    
                    try:
                        user = await bot.fetch_user(int(m_id))
                        await user.send(f"⚠️ Salut! Ai fost marcat ca **Absent** la activitate și ai primit sancțiunea: **{info['sanctiune']}**.")
                    except: pass
                
                absenti_text += f"• {info['nume']} - **{sanc_display}**\n"
        prezenti_pe_un_rand = ", ".join(prezenti) if prezenti else "Niciunul"
        
        embed = discord.Embed(title="📈 Raport Prezență Activitate", color=discord.Color.dark_blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name="✅ Prezenți", value=prezenti_pe_un_rand, inline=False)
        embed.add_field(name="❌ Absenți", value=absenti_text if absenti_text else "Niciunul", inline=False)
        embed.set_footer(text=f"Organizator: {self.autor.display_name}")

        if canal_id:
            canal = interaction.guild.get_channel(int(canal_id))
            if canal: await canal.send(embed=embed)
            
        await interaction.followup.send("🚀 Raportul a fost publicat!", ephemeral=True)
        descriere_log = (
                    f"**Utilizator:** {self.autor.display_name}"
        )
        await trimite_log_centralizat(interaction, "🔨 A facut prezenta membrilor.", descriere_log, discord.Color.from_str("#FFF200"))
        self.stop()

    @discord.ui.button(label="✏️ Modifică pe cineva", style=discord.ButtonStyle.blurple)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        view_select = EditSingleMemberView(self.interaction, self.date_prezenta, self.autor)
        await interaction.response.edit_message(content="Alege membrul pe care vrei să îl modifici:", view=view_select)

async def acorda_sanctiune(interaction: discord.Interaction, membru: discord.Member, tip: str, motiv: str, valoare_amenda: int, user_vizat, forced_guild_id=None):
    if not interaction.response.is_done():
        await interaction.response.defer()
    
    g_id = forced_guild_id if forced_guild_id else interaction.guild_id
    
    if not g_id or str(g_id) == "None":
        
        if interaction.guild:
            g_id = interaction.guild.id
    
    guild_id = str(g_id)
    
    
    
    print(f"ID SERVER: {guild_id}")
    if guild_id == "None":
        return await interaction.response.send_message("❌ Eroare: Nu am putut identifica serverul!", ephemeral=True)

    
    user_id = str(user_vizat.id)
    membru_db = db.reference(f"servers/{guild_id}/membri_activi/{user_id}").get()
    
    if not membru_db:
        return await interaction.response.send_message(f"❌ {user_vizat.mention} nu este în facțiune pe serverul respectiv!", ephemeral=True)

    tz_ro = pytz.timezone('Europe/Bucharest')
    data_acum = datetime.now(tz_ro)
    format_data = "%d/%m/%Y %H:%M"
    
    
    zile_expirare = {"FW": 7, "AV": 14, "Amenda": 3}
    data_expirare_finala = data_acum + timedelta(days=zile_expirare[tip])
    stack_msg = ""

    if tip == "Amenda":
        
                    
        descriere_log = (
                    
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip} ({valoare_amenda})\n"
                    f"**Motiv:** {motiv}\n"
                    
        )
        await trimite_log_centralizat(interaction, "🔨 A ales amenda.", descriere_log, discord.Color.from_str("#FFF200"))

    
    
    if tip == "AV":
        toate_s = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).get() or {}
        av_existente = [k for k, v in toate_s.items() if v.get("tip") == "AV"]

        
                    
        descriere_log = (
                    
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip}\n"
                    f"**Motiv:** {motiv}\n"
                    
        )
        await trimite_log_centralizat(interaction, "🔨 A ales AV.", descriere_log, discord.Color.from_str("#FFF200"))
        
        if len(av_existente) >= 1: 
            
            for key in av_existente:
                bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).child(key).delete()
            
            
            tip = "FW"
            motiv = f"Acumulare 2/2 AV | {motiv}"
            data_expirare_finala = data_acum + timedelta(days=7)
            stack_msg = "\n🔄 **Sistem Stacking:** Cele 2 AV-uri au fost transformate în **FW**!"

            
                    
            descriere_log = (
                    
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** FW\n"
                    f"**Motiv:** 2/2 AV-uri\n"
                    
            )
            await trimite_log_centralizat(interaction, "🔨 Din 2 AV-uri sa transformat in FW.", descriere_log, discord.Color.from_str("#FFFFFF"))



    
    if tip == "FW":
        toate_s = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id)).get() or {}
        fw_uri = [v for v in toate_s.values() if v.get("tip") == "FW"]
        
        if fw_uri:
            
            ultimul_fw = sorted(fw_uri, key=lambda x: datetime.strptime(x['data_acordarii'], format_data))[-1]
            data_ultimul_acord = datetime.strptime(ultimul_fw['data_acordarii'], format_data).replace(tzinfo=tz_ro)
            data_ultimul_expir = datetime.strptime(ultimul_fw['data_expirarii'], format_data).replace(tzinfo=tz_ro)

            
            if (data_acum - data_ultimul_acord).days <= 3:
                data_expirare_finala = data_ultimul_expir + timedelta(days=7)
                stack_msg = "\n⚠️ **Sistem Stacking:** S-au adăugat 7 zile la data de expirare anterioară (FW primit la <3 zile)."
            
        
                    
        descriere_log = (
                    
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** {tip}\n"
                    f"**Motiv:** {motiv}\n"
                    
        )
        await trimite_log_centralizat(interaction, "🔨 A ales FW.", descriere_log, discord.Color.from_str("#FFF200"))

    
    data_str = data_acum.strftime(format_data)
    expirare_str = data_expirare_finala.strftime(format_data)

    sanctiune_payload = {
        "tip": tip,
        "motiv": motiv,
        "acordat_de": str(interaction.user),
        "data_acordarii": data_str,
        "data_expirarii": expirare_str,
        "status": "Activa" if tip != "Amenda" else "Neachitata"
    }
    if tip == "Amenda":
        sanctiune_payload["valoare_amenda"] = valoare_amenda

    
    ref_user_sanctiuni = bot.get_server_ref(interaction.guild_id).child("sanctiuni").child(str(membru.id))
    new_ref = ref_user_sanctiuni.push()
    s_id_unic = new_ref.key
    new_ref.set(sanctiune_payload)

    
    bot.get_server_ref(interaction.guild_id).child("istoric_sanctiuni").child(str(membru.id)).child(s_id_unic).set({
        "tip": tip,
        "motiv": motiv,
        "autor_nume": interaction.user.display_name,
        "autor_id": interaction.user.id,
        "data": data_str,
        "valoare": valoare_amenda if tip == "Amenda" else None
    })

    
    if tip == "FW":
        actuale = ref_user_sanctiuni.get() or {}
        count_fw = sum(1 for s in actuale.values() if s.get("tip") == "FW")
        if count_fw >= 3:
            
            for path in ["membri_activi", "sanctiuni", "invoiri"]:
                bot.get_server_ref(interaction.guild_id).child(path).child(str(membru.id)).delete()

    
            
                    
            descriere_log = (
                    
                    f"**Jucatorul sanctionat:** {membru}\n"
                    f"**Sanctiunea:** Uninvite cu 30FP\n"
                    f"**Motiv:** 3/3 FW-uri\n"
                    
            )
            await trimite_log_centralizat(interaction, "🔨 A fost demis din factiune.", descriere_log, discord.Color.from_str("#FFF200"))
            return await interaction.channel.send(f"🚨 {membru.mention} a acumulat **3/3 FW** și a fost **demis automat** din facțiune!")
    
    try:
        await membru.send(f"⚠️ Ai primit **{tip}** pe {interaction.guild.name}!\nMotiv: {motiv}\nExpiră la: {expirare_str}")
        dm_status = "✅ DM trimis"
    except:
        dm_status = "❌ DM închis"

    await interaction.channel.send(f"✅ Membrul {membru.mention} a ales {tip} pentru neparticiparea la RP/Sedinta ({dm_status}). Expiră la: `{expirare_str}`{stack_msg}")

@bot.tree.command(name="prezenta", description="Începe procesul de marcare a prezenței la activitate")
async def prezenta(interaction: discord.Interaction):
    
    sd = bot.get_server_data(interaction.guild_id)
    membri_activi = sd.get("membri_activi", {})

    
    if not membri_activi:
        return await interaction.response.send_message(
            "❌ Nu există membri în baza de date pentru acest server.", 
            ephemeral=True
        )

    
    if not are_permisiune(interaction, sd, "sanctiune"):
        return await interaction.response.send_message(
            "❌ Nu ai permisiunea necesară pentru a organiza prezența.", 
            ephemeral=True
        )

    
    
    view = ParticipareView(interaction, membri_activi, interaction.user)
    
    
    embed_initial = await view.genera_embed_pas()

    
    await interaction.response.send_message(
        content="🚀 **Sistem de Prezență pornit.**\nUrmează pașii pentru fiecare membru:",
        embed=embed_initial, 
        view=view, 
        ephemeral=True
    )

@bot.tree.command(name="statistica", description="Gestionează tabelul de statistici raport")
@app_commands.choices(optiune=[
    app_commands.Choice(name="creare", value="creare"),
    app_commands.Choice(name="resetare", value="resetare"),
    app_commands.Choice(name="stergere", value="stergere")
])
async def statistica(interaction: discord.Interaction, optiune: str, canal: discord.TextChannel = None):
    
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Doar administratorii pot folosi asta.", ephemeral=True)

    guild_id = str(interaction.guild_id)
    stats_ref = db.reference(f'servers/{guild_id}/statistica_raport')
    sd = bot.get_server_data(guild_id)
    membri = sd.get("membri_activi", {})

    if optiune == "creare":
        if not canal: canal = interaction.channel
        
        
        date_start = {}
        for m_id, info in membri.items():
            date_start[m_id] = {"nume": info.get('nume_joc', 'Necunoscut'), "puncte": 0, "detalii": {}}

        embed = discord.Embed(title="📊 Statistici Live Raport", color=discord.Color.blue())
        embed.description = "Tabelul se va actualiza după fiecare verificare."
        
        msg = await canal.send(embed=embed)
        
        stats_ref.set({
            "canal_id": str(canal.id),
            "mesaj_id": str(msg.id),
            "date": date_start
        })
        await interaction.response.send_message(f"✅ Tabel creat pe canalul {canal.mention}!", ephemeral=True)

    elif optiune == "resetare":
        data = stats_ref.get()
        if not data: return await interaction.response.send_message("❌ Nu există un tabel activ.", ephemeral=True)
        
        
        for m_id in data['date']:
            data['date'][m_id]['puncte'] = 0
            data['date'][m_id]['detalii'] = {}
            
        stats_ref.update({"date": data['date']})
        await actualizeaza_tabel_mesaj(interaction.guild, data)
        await interaction.response.send_message("✅ Toate punctele au fost resetate!", ephemeral=True)

    elif optiune == "stergere":
        stats_ref.delete()
        await interaction.response.send_message("🗑️ Statistici șterse din baza de date.", ephemeral=True)

async def actualizeaza_tabel_mesaj(guild, stats_data):
    canal = guild.get_channel(int(stats_data['canal_id']))
    if not canal: return
    
    try:
        mesaj = await canal.fetch_message(int(stats_data['mesaj_id']))
    except: return

    sorted_members = sorted(stats_data['date'].items(), key=lambda x: x[1]['puncte'], reverse=True)

    embed = discord.Embed(
        title="📊 Statistici Live Raport", 
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    
    tabel_text = "```\n"
    tabel_text += f"{'Nume':<15} | {'Pct':<5} | {'Activitate'}\n"
    tabel_text += "-" * 55 + "\n"
    
    for m_id, info in sorted_members:
        nume = info['nume'][:15]
        puncte = info['puncte']
        
        
        detalii_list = []
        for act, val in info.get('detalii', {}).items():
            if int(val) > 0:
                detalii_list.append(f"{val} {act}")
        
        detalii_text = ", ".join(detalii_list)
        
        
        if len(detalii_text) > 30:
            detalii_text = detalii_text[:27] + "..."

        tabel_text += f"{nume:<15} | {puncte:<5} | {detalii_text}\n"
    
    tabel_text += "```"
    embed.description = tabel_text
    await mesaj.edit(embed=embed)

@bot.tree.command(name="afisarepermisiuni", description="Afișează permisiunile configurate pentru gradele administrative.")
async def view_permissions(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    grad_staff = get_staff_rank(interaction, interaction.user)
    
    
    if str(grad_staff).lower() not in ["lider", "co-lider", "tester"]:
        return await interaction.response.send_message(
            "❌ Nu ai acces la această comandă. Doar Staff-ul administrativ poate vedea configurația.", 
            ephemeral=True
        )

    ref = db.reference(f'servers/{guild_id}/permisiuni')
    perm_data = ref.get()

    if not perm_data:
        return await interaction.response.send_message(
            "❌ Nu există nicio configurare de permisiuni în baza de date.", 
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"🔐 Configurare Permisiuni - {interaction.guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    
    target_roles = ["lider", "co-lider", "tester"]
    
    for role_key in target_roles:
        role_perms = perm_data.get(role_key, {})
        
        if not role_perms:
            embed.add_field(name=f"👑 {role_key.upper()}", value="`Nu este configurat`", inline=False)
            continue

        role_id = role_perms.get("role_id", "Nespecificat")
        
        perms_list = []
        for perm_name, value in role_perms.items():
            if perm_name == "role_id": continue 
            
            
            pretty_name = perm_name.replace("_", " ").title()
            status = "✅" if value is True else "❌"
            perms_list.append(f"{status} {pretty_name}")

        text_final = f"**ID Rol:** <@&{role_id}>\n" if role_id != "Nespecificat" else ""
        text_final += "\n".join(perms_list) if perms_list else "Fără permisiuni specifice."

        
        if len(text_final) > 1024:
            text_final = text_final[:1020] + "..."

        embed.add_field(
            name=f"🛡️ {role_key.upper()}", 
            value=text_final, 
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sec_cuvant", description="Adaugă sau șterge un cuvânt suspect specific pentru acest server")
@app_commands.choices(actiune=[
    app_commands.Choice(name="Adaugă", value="add"),
    app_commands.Choice(name="Șterge", value="remove")
])
@app_commands.describe(cuvant="Cuvântul sau fraza suspectă")
async def sec_cuvant(interaction: discord.Interaction, actiune: str, cuvant: str):
    sd = bot.get_server_data(interaction.guild_id)
    
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni pentru configurarea securității.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    cuvant_f = cuvant.lower().strip()
    
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/blacklist_words')
    cuvinte = ref.get() or []

    if actiune == "add":
        if cuvant_f not in cuvinte:
            cuvinte.append(cuvant_f)
            ref.set(cuvinte)
            bot.get_server_data(interaction.guild_id, force_refresh=True) 
            await interaction.followup.send(f"✅ Cuvântul `{cuvant_f}` a fost adăugat în lista suspectă a acestui server.")
        else:
            await interaction.followup.send("ℹ️ Acest cuvânt este deja configurat pe server.")
    
    elif actiune == "remove":
        if cuvant_f in cuvinte:
            cuvinte.remove(cuvant_f)
            ref.set(cuvinte)
            bot.get_server_data(interaction.guild_id, force_refresh=True)
            await interaction.followup.send(f"✅ Cuvântul `{cuvant_f}` a fost șters din lista serverului.")
        else:
            await interaction.followup.send("❌ Acest cuvânt nu a fost găsit în lista serverului.")


@bot.tree.command(name="sec_whitelist", description="Adaugă sau șterge un rol care are BYPASS la sistemul anti-spam/securitate")
@app_commands.choices(actiune=[
    app_commands.Choice(name="Adaugă în Whitelist", value="add"),
    app_commands.Choice(name="Șterge din Whitelist", value="remove")
])
async def sec_whitelist(interaction: discord.Interaction, actiune: str, rol: discord.Role):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    rol_id_str = str(rol.id)
    
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/whitelist_roles')
    roles_list = ref.get() or []

    if actiune == "add":
        if rol_id_str not in roles_list:
            roles_list.append(rol_id_str)
            ref.set(roles_list)
            bot.get_server_data(interaction.guild_id, force_refresh=True)
            await interaction.followup.send(f"🛡️ Rolul {rol.mention} a fost adăugat în **Whitelist**. Membrii cu acest rol au bypass complet.")
        else:
            await interaction.followup.send("ℹ️ Acest rol este deja în Whitelist.")
            
    elif actiune == "remove":
        if rol_id_str in roles_list:
            roles_list.remove(rol_id_str)
            ref.set(roles_list)
            bot.get_server_data(interaction.guild_id, force_refresh=True)
            await interaction.followup.send(f"✅ Rolul {rol.mention} a fost scos din Whitelist.")
        else:
            await interaction.followup.send("❌ Acest rol nu se află în lista de Whitelist.")


@bot.tree.command(name="sec_status", description="Vezi cuvintele suspecte și rolurile din Whitelist de pe acest server")
async def sec_status(interaction: discord.Interaction):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    sec_data = sd.get("security_local", {})
    cuvinte = sec_data.get("blacklist_words", [])
    roluri = sec_data.get("whitelist_roles", [])
    
    embed = discord.Embed(title=f"🛡️ Configurație Securitate - {interaction.guild.name}", color=discord.Color.blue())
    
    text_cuvinte = ", ".join([f"`{c}`" for c in cuvinte]) if cuvinte else "*Niciun cuvânt setat.*"
    text_roluri = ", ".join([f"<@&{r}>" for r in roluri]) if roluri else "*Niciun rol în whitelist.*"
    
    embed.add_field(name="🎯 Cuvinte suspecte server", value=text_cuvinte, inline=False)
    embed.add_field(name="⚪ Roluri cu Bypass (Whitelist)", value=text_roluri, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sec_tag_spam", description="Setează limita de tag-uri/mențiuni unice permise în 60 de secunde")
@app_commands.describe(limita="Numărul maxim de tag-uri permise (0 pentru dezactivare). Ex: 5")
async def sec_tag_spam(interaction: discord.Interaction, limita: int):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/max_tags')
    
    if limita <= 0:
        ref.delete()
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send("✅ Protecția Mass-Mention a fost **dezactivată** pe acest server.")
    else:
        ref.set(limita)
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send(f"🛡️ Limita de tag-uri a fost setată la **{limita}** în 60 de secunde. Cine depășește va primi mute automat.")

@bot.tree.command(name="sec_msg_spam", description="Setează limita de mesaje identice permise în 60 de secunde")
@app_commands.describe(limita="Numărul maxim de mesaje identice permise (0 pentru dezactivare). Ex: 3")
async def sec_msg_spam(interaction: discord.Interaction, limita: int):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/max_identical_msgs')
    
    if limita <= 0:
        ref.delete()
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send("✅ Protecția împotriva mesajelor identice a fost **dezactivată**.")
    else:
        ref.set(limita)
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send(f"🛡️ Limita de mesaje identice a fost setată la **{limita}**. Cine trimite același text de atâtea ori în 60s va fi sancționat.")


@bot.tree.command(name="sec_sanctiune", description="Alege tipul de pedeapsă aplicat de sistemul de securitate")
@app_commands.choices(tip=[
    app_commands.Choice(name="Mute (28 zile)", value="timeout"),
    app_commands.Choice(name="Ban Permanent", value="ban")
])
async def sec_sanctiune(interaction: discord.Interaction, tip: str):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/punishment_type')
    
    ref.set(tip)
    bot.get_server_data(interaction.guild_id, force_refresh=True)
    
    nume_pedeapsa = "Mute (28 zile)" if tip == "timeout" else "Ban Permanent"
    await interaction.followup.send(f"⚙️ Pedeapsa automată de securitate a fost setată pe: **{nume_pedeapsa}**.")

@bot.tree.command(name="sec_spam_general", description="Setează limita maximă de mesaje permise în 60 de secunde (indiferent de conținut)")
@app_commands.describe(limita="Numărul maxim de mesaje permise (0 pentru dezactivare). Ex: 10")
async def sec_spam_general(interaction: discord.Interaction, limita: int):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/max_general_msgs')
    
    if limita <= 0:
        ref.delete()
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send("✅ Protecția împotriva spam-ului general a fost **dezactivată**.")
    else:
        ref.set(limita)
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        await interaction.followup.send(f"🛡️ Limita de spam general a fost setată la **{limita}** mesaje în 60s. Cine o depășește va fi sancționat, iar mesajele îi vor fi șterse.")

@bot.tree.command(name="sec_join_role", description="Oferă automat un rol restrictiv la intrarea pe server")
@app_commands.describe(
    activat="True pentru activare, False pentru dezactivare",
    canal_permis="Canalul opțional unde membrul are totuși voie să scrie (ex: #verificare)"
)
async def sec_join_role(interaction: discord.Interaction, activat: bool, canal_permis: discord.TextChannel = None):
    sd = bot.get_server_data(interaction.guild_id)
    if interaction.user.id != OWNER_ID and not are_permisiune(interaction, sd, "setari"):
        return await interaction.response.send_message("❌ Lipsă permisiuni.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    
    ref = db.reference(f'servers/{interaction.guild_id}/security_local/join_restriction')
    
    if not activat:
        ref.delete()
        bot.get_server_data(interaction.guild_id, force_refresh=True)
        return await interaction.followup.send("✅ Sistemul de restricție la intrare a fost **dezactivat**.")
        
    
    data_config = {
        "status": True,
        "canal_permis_id": str(canal_permis.id) if canal_permis else None
    }
    ref.set(data_config)
    bot.get_server_data(interaction.guild_id, force_refresh=True)
    
    mesaj_canal = f"pe canalul {canal_permis.mention}" if canal_permis else "pe niciun canal"
    await interaction.followup.send(f"🛡️ Sistem activat! Noii membri vor primi un rol restrictiv și nu vor putea scrie nicăieri, cu excepția: **{mesaj_canal}**.")

@bot.event
async def on_member_join(member):
    
    sd = bot.get_server_data(member.guild.id)
    config_join = sd.get("security_local", {}).get("join_restriction")
    
    Acum_utc = discord.utils.utcnow()
    
    
    username_cifre = sum(c.isdigit() for c in member.name)
    display_cifre = sum(c.isdigit() for c in member.display_name)
    are_prea_multe_cifre = username_cifre > 5 or display_cifre > 5
    
    
    diferenta_varsta = Acum_utc - member.created_at
    este_cont_nou_creat = diferenta_varsta < timedelta(days=1)
    
    
    este_suspect = are_prea_multe_cifre or este_cont_nou_creat
    
    
    sistem_general_activat = config_join and config_join.get("status")
    if not sistem_general_activat and not este_suspect:
        return

    guild = member.guild
    nume_rol_restrictiv = "Restricționat (Securitate)"
    
    
    rol_restrictiv = discord.utils.get(guild.roles, name=nume_rol_restrictiv)
    
    
    if not rol_restrictiv:
        try:
            perms = discord.Permissions.none()
            perms.update(send_messages=False, send_messages_in_threads=False, add_reactions=False)
            
            rol_restrictiv = await guild.create_role(
                name=nume_rol_restrictiv,
                permissions=perms,
                color=discord.Color.dark_grey(),
                reason="Sistem Securitate: Creare rol restrictiv pentru membrii noi/suspecți."
            )
            print(f"⚙️ Rolul '{nume_rol_restrictiv}' a fost creat cu succes pe serverul {guild.name}.")
        except discord.Forbidden:
            print(f"❌ Botul nu are permisiunea 'Manage Roles' pe serverul {guild.name}!")
            return
        except Exception as e:
            print(f"Eroare la crearea rolului: {e}")
            return

    
    
    canal_permis_id = config_join.get("canal_permis_id") if (sistem_general_activat and not este_suspect) else None

    
    try:
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.CategoryChannel, discord.ForumChannel, discord.VoiceChannel)):
                
                
                if canal_permis_id and str(channel.id) == str(canal_permis_id):
                    overwrite = channel.overwrites_for(rol_restrictiv)
                    if overwrite.send_messages != True:
                        overwrite.send_messages = True
                        overwrite.send_messages_in_threads = True
                        overwrite.add_reactions = True
                        await channel.set_permissions(rol_restrictiv, overwrite=overwrite, reason="Sistem Securitate: Permite acces pe canalul excepție.")
                
                
                else:
                    overwrite = channel.overwrites_for(rol_restrictiv)
                    if overwrite.send_messages != False:
                        overwrite.send_messages = False
                        overwrite.send_messages_in_threads = False
                        overwrite.add_reactions = False
                        await channel.set_permissions(rol_restrictiv, overwrite=overwrite, reason="Sistem Securitate: Blocare automată acces canal.")
                        
    except Exception as e:
        print(f"Eroare la setarea permisiunilor specifice pe canale: {e}")

    
    try:
        await member.add_roles(rol_restrictiv, reason="Sistem Securitate: Membru restricționat automat la intrare.")
        print(f"🛡️ Membrul {member.name} a primit rolul restrictiv. (Cifre: {are_prea_multe_cifre} | Cont nou: {este_cont_nou_creat})")
    except discord.Forbidden:
        print(f"❌ Botul nu are permisiunea să adauge roluri sau rolul botului este mai jos decât cel restrictiv!")
        return
    except Exception as e:
        print(f"Eroare la oferirea rolului pentru {member.name}: {e}")
        return

    
    if este_suspect:
        canal_alerta_id = sd.get("canal_sec_join") 
        if canal_alerta_id:
            try:
                canal_alerta = guild.get_channel(int(canal_alerta_id))
                if canal_alerta:
                    
                    motive = []
                    if are_prea_multe_cifre: motive.append("Cod 152")
                    if este_cont_nou_creat: motive.append("Cod 341")
                    
                    text_motiv = " și ".join(motive)
                    
                    
                    await canal_alerta.send(
                        f"⚠️ {member.mention} Contul tău este considerat **suspect** deoarece {text_motiv}. "
                        f"Ai fost restricționat automat! Va trebui ca un **Lider** sau **Co-Lider** să îți ofere accesul prin scoaterea manuală a rolului `{nume_rol_restrictiv}`."
                    )
            except Exception as e:
                print(f"Eroare la trimiterea alertei de cont suspect pe canalul {canal_alerta_id}: {e}")

@bot.tree.command(name="restart", description="Verifică starea meniurilor active și restartează botul")
async def restart_bot(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Doar proprietarul botului poate folosi această comandă.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    tz_ro = pytz.timezone('Europe/Bucharest')
    acum = datetime.now(tz_ro)
    
    toate_serverele = db.reference('servers').get() or {}
    
    meniu_sub_3_zile = False
    detalii_meniuri_vechi = []
    
    for guild_id, data in toate_serverele.items():
        guild_ob = bot.get_guild(int(guild_id))
        nume_server = guild_ob.name if guild_ob else f"ID: {guild_id}"
        
        
        turneu_data = data.get("turneu", {})
        if isinstance(turneu_data, dict) and turneu_data.get("activ"):
            data_pornire_str = turneu_data.get("data_pornire") 
            if data_pornire_str:
                try:
                    dt_pornire = tz_ro.localize(datetime.strptime(data_pornire_str, "%d/%m/%Y %H:%M"))
                    diferenta = acum - dt_pornire
                    if diferenta.days < 3:
                        meniu_sub_3_zile = True
                    else:
                        detalii_meniuri_vechi.append(f"🏟️ **Turneu** pe serverul **{nume_server}** (Pornit la: `{data_pornire_str}`)")
                except Exception as e:
                    print(f"Eroare parsare dată turneu: {e}")

        
        prezenta_data = data.get("prezenta", {})
        if isinstance(prezenta_data, dict) and prezenta_data.get("activ"):
            data_pornire_str = prezenta_data.get("data_pornire")
            if data_pornire_str:
                try:
                    dt_pornire = tz_ro.localize(datetime.strptime(data_pornire_str, "%d/%m/%Y %H:%M"))
                    diferenta = acum - dt_pornire
                    if diferenta.days < 3:
                        meniu_sub_3_zile = True
                    else:
                        detalii_meniuri_vechi.append(f"📋 **Prezență** pe serverul **{nume_server}** (Pornit la: `{data_pornire_str}`)")
                except Exception as e:
                    print(f"Eroare parsare dată prezență: {e}")

    
    if meniu_sub_3_zile:
        return await interaction.followup.send(f"❌ **Nu se poate da restart!** Există un meniu activ (Turneu sau Prezență) pornit de mai puțin de 3 zile pe unul dintre servere.\n\n{raport}", ephemeral=True)
    
    if detalii_meniuri_vechi:
        raport = "\n".join(detalii_meniuri_vechi)
        await interaction.followup.send(f"⚠️ **Meniuri active găsite (mai vechi de 3 zile):**\n\n{raport}\n\n🔄 *Se asteapta restartul...*", ephemeral=True)
    else:
        await interaction.followup.send(f"✅ Niciun meniu activ detectat. *Se asteapta restartul...*\n\n{raport}", ephemeral=True)

@bot.tree.command(name="backup_shutdown", description="Face backup la DB, părăsește serverele externe și oprește botul definitiv")
async def backup_shutdown(interaction: discord.Interaction):
    
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Doar proprietarul botului poate executa această comandă.", ephemeral=True)
    
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        await interaction.followup.send("📦 Pasul 1: Se descarcă datele complete din Firebase...", ephemeral=True)
        
        
        toata_baza_date = db.reference("/").get()
        
        if not toata_baza_date:
            return await interaction.followup.send("⚠️ Baza de date este goală sau nu a putut fi citită.", ephemeral=True)
        
        
        json_data = json.dumps(toata_baza_date, indent=4, ensure_ascii=False)
        
        
        fisier_backup = io.BytesIO(json_data.encode('utf-8'))
        discord_file = discord.File(fp=fisier_backup, filename=f"backup_complet_{datetime.now().strftime('%d_%m_%Y')}.json")
        
        
        await interaction.followup.send(
            content="✅ **Copie de rezervă creată cu succes!**\n"
                    "Mai jos ai fișierul `.json` cu toate datele proiectului.",
            file=discord_file,
            ephemeral=True
        )
        
        await interaction.followup.send("🧹 Pasul 2: Se părăsesc serverele externe...", ephemeral=True)
        
        
        server_staff_id = GUILD_STAFF.id
        servere_parasite = 0
        
        
        for guild in list(bot.guilds):
            if guild.id != server_staff_id:
                try:
                    print(f"Leaving guild: {guild.name} ({guild.id})")
                    await guild.leave()
                    servere_parasite += 1
                except Exception as e:
                    print(f"Nu s-a putut părăsi serverul {guild.name}: {e}")
        
        
        await interaction.followup.send(
            content=f"👋 **Proces finalizat cu succes!**\n"
                    f"• Am părăsit `{servere_parasite}` servere externe.\n"
                    f"• Serverul tău principal de staff (ID: `{server_staff_id}`) a fost păstrat.\n"
                    f"🔴 *Botul se va opri definitiv acum...*",
            ephemeral=True
        )
        
        
        await asyncio.sleep(4)
        
        print(f"🔴 [SHUTDOWN FINAL] Botul a părăsit {servere_parasite} servere și a fost oprit controlat de Owner.")
        
        
        await bot.close()

    except Exception as e:
        print(f"Eroare critică la salvare/curățare/oprire: {e}")
        await interaction.followup.send(f"❌ A apărut o eroare critică: `{e}`", ephemeral=True)


    
bot.run(TOKEN)
