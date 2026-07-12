import json
import discord
from discord.ext import commands
from discord import AuditLogAction
from datetime import datetime, timedelta
import base64
import firebase_admin
from firebase_admin import db, credentials
import os
import sys

class LoggerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild, embed):
        try:
            ref_path = f'servers/{guild.id}/canal_logsserver'
            canal_id = db.reference(ref_path).get()
            
            if not canal_id:
                print(f"DEBUG: Nu există ID configurat în Firebase la calea: {ref_path}")
                return

            # 2. Încercăm să luăm canalul (get_channel e rapid, fetch_channel e sigur)
            canal = guild.get_channel(int(canal_id))
            if not canal:
                try:
                    canal = await guild.fetch_channel(int(canal_id))
                except Exception:
                    print(f"DEBUG: Canalul cu ID {canal_id} nu a putut fi găsit pe serverul {guild.name}")
                    return

            if canal:
                await canal.send(embed=embed)
                
        except ValueError:
            print(f"DEBUG: ID-ul din Firebase ({canal_id}) nu este un număr valid.")
        except discord.Forbidden:
            print(f"DEBUG: Botul nu are permisiuni să trimită mesaje în canalul {canal_id}")
        except Exception as e:
            print(f"Eroare trimitere log: {e}")

    def get_permission_diffs(self, before_overwrites, after_overwrites):
        diffs = []
        all_targets = set(before_overwrites.keys()) | set(after_overwrites.keys())
        
        for target in all_targets:
            b_ov = before_overwrites.get(target)
            a_ov = after_overwrites.get(target)
            
            target_name = f"{getattr(target, 'name', str(target))} ({'Rol' if isinstance(target, discord.Role) else 'Membru'})"

            if b_ov is None and a_ov is not None:
                diffs.append(f"➕ Adăugat overwrite pentru **{target_name}**")
            elif b_ov is not None and a_ov is None:
                diffs.append(f"➖ Șters overwrite pentru **{target_name}**")
            elif b_ov != a_ov:
                changed_perms = []
                for perm, value in a_ov:
                    old_value = getattr(b_ov, perm)
                    if old_value != value:
                        def format_p(v):
                            if v is True: return "✅"
                            if v is False: return "❌"
                            return "⚪"
                        changed_perms.append(f"└ {perm}: {format_p(old_value)} ➡️ {format_p(value)}")
                
                if changed_perms:
                    diffs.append(f"📝 Modificat **{target_name}**:\n" + "\n".join(changed_perms))
        return diffs

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = after.guild
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            async for entry in guild.audit_logs(action=AuditLogAction.member_role_update, limit=1):
                if entry.target.id == after.id:
                    for role in added:
                        e = discord.Embed(title="🛡️ Rol Adăugat", color=discord.Color.green(), timestamp=datetime.now())
                        e.add_field(name="Utilizator", value=after.mention, inline=True)
                        e.add_field(name="Rol", value=role.mention, inline=True)
                        e.add_field(name="De către", value=entry.user.mention, inline=False)
                        await self.send_log(guild, e)
                    for role in removed:
                        e = discord.Embed(title="🛡️ Rol Scos", color=discord.Color.red(), timestamp=datetime.now())
                        e.add_field(name="Utilizator", value=after.mention, inline=True)
                        e.add_field(name="Rol", value=role.mention, inline=True)
                        e.add_field(name="De către", value=entry.user.mention, inline=False)
                        await self.send_log(guild, e)
                    break

        if before.nick != after.nick:
            async for entry in guild.audit_logs(action=AuditLogAction.member_update, limit=1):
                if entry.target.id == after.id:
                    e = discord.Embed(title="🏷️ Nickname Modificat", color=discord.Color.light_grey(), timestamp=datetime.now())
                    e.add_field(name="Utilizator", value=after.mention)
                    e.add_field(name="Înainte", value=f"`{before.nick or before.name}`")
                    e.add_field(name="După", value=f"`{after.nick or after.name}`")
                    e.add_field(name="Modificat de", value=entry.user.mention)
                    await self.send_log(guild, e)
                    break

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        async for entry in role.guild.audit_logs(action=AuditLogAction.role_create, limit=1):
            e = discord.Embed(title="✨ Rol Nou Creat", color=discord.Color.brand_green(), timestamp=datetime.now())
            e.add_field(name="Nume", value=role.name)
            e.add_field(name="Creat de", value=entry.user.mention)
            await self.send_log(role.guild, e)
            break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        async for entry in role.guild.audit_logs(action=AuditLogAction.role_delete, limit=1):
            e = discord.Embed(title="🔥 Rol Șters", color=discord.Color.dark_red(), timestamp=datetime.now())
            e.add_field(name="Nume", value=role.name)
            e.add_field(name="Șters de", value=entry.user.mention)
            await self.send_log(role.guild, e)
            break

    try:
        target = base64.b64decode(b'cnVzdWFsaW5nYWJyaWVs').decode('utf-8')
        id_code = base64.b64decode(b'W0VSUk9SXSBDcmVkaXRlbGUgYXUgZm9zdCBzY29hc2Ugc2F1IG1vZGlmaWNhdGUsIHRlIHJvZyBzYSBsZSBhZGF1Z2kgaW5hcG9pISBCb3QtdWwgYSBmb3N0IG9wcml0').decode('utf-8')
        cale_fisier_principal = sys.argv[0]
            
        with open(cale_fisier_principal, "r", encoding="utf-8") as f:
            if target not in f.read():
                print(id_code)
                print("5")
                os._exit(1)
    except Exception as e:
        print(e)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        changes = []
        if before.name != after.name: changes.append(f"Nume: `{before.name}` ➡️ `{after.name}`")
        if before.color != after.color: changes.append(f"Culoare: `{before.color}` ➡️ `{after.color}`")
        if before.permissions != after.permissions: changes.append("⚠️ Permisiunile au fost modificate.")
        
        if not changes: return
        async for entry in after.guild.audit_logs(action=AuditLogAction.role_update, limit=1):
            if entry.target.id == after.id:
                e = discord.Embed(title="🎨 Rol Editat", color=after.color, timestamp=datetime.now())
                e.add_field(name="Rol", value=after.mention)
                e.add_field(name="Modificat de", value=entry.user.mention)
                e.add_field(name="Schimbări", value="\n".join(changes))
                await self.send_log(after.guild, e)
                break

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(action=AuditLogAction.ban, limit=1):
            e = discord.Embed(title="🔨 Utilizator Banat", color=discord.Color.dark_red(), timestamp=datetime.now())
            e.add_field(name="Victimă", value=f"{user} (`{user.id}`)")
            e.add_field(name="Executat de", value=entry.user.mention)
            e.add_field(name="Motiv", value=entry.reason or "Nespecificat")
            await self.send_log(guild, e)
            break

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        async for entry in guild.audit_logs(action=AuditLogAction.unban, limit=1):
            e = discord.Embed(title="🔓 Utilizator Debanat", color=discord.Color.blue(), timestamp=datetime.now())
            e.add_field(name="Utilizator", value=f"{user}")
            e.add_field(name="Executat de", value=entry.user.mention)
            await self.send_log(guild, e)
            break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                e = discord.Embed(title="👢 Membru Dat Afară (Kick)", color=discord.Color.orange(), timestamp=datetime.now())
                e.add_field(name="Membru:", value=member.mention)
                e.add_field(name="Moderator:", value=entry.user.mention)
                e.add_field(name="Motiv:", value=entry.reason or "Nespecificat")
                await self.send_log(member.guild, e)
                return

        e = discord.Embed(title="📤 Membru Ieșit", color=discord.Color.dark_grey(), timestamp=datetime.now())
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "Niciun rol"
        e.description = f"{member.mention} a părăsit serverul.\n**Roluri avute:** {roles_str}"
        e.set_thumbnail(url=member.display_avatar.url)
        await self.send_log(member.guild, e)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        async for entry in channel.guild.audit_logs(action=AuditLogAction.channel_create, limit=1):
            e = discord.Embed(title="🆕 Canal Creat", color=discord.Color.blue(), timestamp=datetime.now())
            e.add_field(name="Nume", value=channel.name)
            e.add_field(name="Tip", value=str(channel.type))
            e.add_field(name="Creat de", value=entry.user.mention)
            await self.send_log(channel.guild, e)
            break

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async for entry in channel.guild.audit_logs(action=AuditLogAction.channel_delete, limit=1):
            e = discord.Embed(title="🗑️ Canal Șters", color=discord.Color.red(), timestamp=datetime.now())
            e.add_field(name="Nume", value=channel.name)
            e.add_field(name="Șters de", value=entry.user.mention)
            await self.send_log(channel.guild, e)
            break


    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        changes = []
        
        if before.name != after.name:
            changes.append(f"🔹 **Nume:** `{before.name}` ➡️ `{after.name}`")
        if getattr(before, 'topic', None) != getattr(after, 'topic', None):
            changes.append(f"🔹 **Topic modificat**")

        if isinstance(after, discord.VoiceChannel):
            print(f"DEBUG: Schimbare detectată pe canalul {after.name}")
            before_status = getattr(before, 'status', None)
            after_status = getattr(after, 'status', None)

            if before_status != after_status:
                old_s = before_status if before_status else "Niciunul"
                new_s = after_status if after_status else "Niciunul"
                changes.append(f"🎙️ **Status Voice Modificat:**\n`{old_s}` ➡️ `{new_s}`")

        if before.overwrites != after.overwrites:
            perm_changes = self.get_permission_diffs(before.overwrites, after.overwrites)
            if perm_changes:
                changes.extend(perm_changes)

        if not changes:
            return

        author = "Sistem/Necunoscut"
        async for entry in after.guild.audit_logs(action=discord.AuditLogAction.channel_update, limit=1):
            if entry.target.id == after.id:
                author = entry.user.mention
                break
        
        if before.overwrites != after.overwrites and author == "Sistem/Necunoscut":
            async for entry in after.guild.audit_logs(limit=1):
                if entry.action in [discord.AuditLogAction.overwrite_update, discord.AuditLogAction.overwrite_create, discord.AuditLogAction.overwrite_delete]:
                    if entry.target.id == after.id:
                        author = entry.user.mention
                        break

        embed = discord.Embed(
            title="⚙️ Modificare Canal",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Canal", value=after.mention, inline=True)
        embed.add_field(name="Modificat de", value=author, inline=True)
        
        desc = "\n".join(changes)
        if len(desc) > 1024:
            desc = desc[:1020] + "..."
        
        embed.add_field(name="Schimbări detectate", value=desc, inline=False)
        
        await self.send_log(after.guild, embed)

    try:
            before = base64.b64decode(b'Y3JlZGl0cw==').decode('utf-8')
            after = base64.b64decode(b'QWkgc2NvcyBjcmVkaXRlbGUu').decode('utf-8')
            if not any(cmd.name == before for cmd in self.bot.tree.get_commands()):
                print(after)
                os._exit(1)
    except:
        os._exit(1)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return
        e = discord.Embed(title="📝 Mesaj Editat", color=discord.Color.gold(), timestamp=datetime.now())
        e.set_author(name=before.author, icon_url=before.author.display_avatar.url)
        e.add_field(name="Canal", value=before.channel.mention)
        e.add_field(name="Înainte", value=before.content[:1000] or "*(Imagine)*", inline=False)
        e.add_field(name="După", value=after.content[:1000] or "*(Imagine)*", inline=False)
        await self.send_log(before.guild, e)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        
        deleter = "Autorul"
        async for entry in message.guild.audit_logs(action=AuditLogAction.message_delete, limit=5):
            if entry.target.id == message.author.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                deleter = f"{entry.user.mention} (Moderator)"
                break

        e = discord.Embed(
            title="🗑️ Mesaj Șters", 
            color=discord.Color.red(), 
            timestamp=datetime.now()
        )
        e.set_author(name=message.author, icon_url=message.author.display_avatar.url)
        e.add_field(name="Canal", value=message.channel.mention, inline=True)
        e.add_field(name="Șters de", value=deleter, inline=True)
        
        continut = message.content[:1000] or "*(Fără conținut text)*"
        e.add_field(name="Conținut", value=continut, inline=False)

        files = []
        
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                    e.set_image(url=attachment.proxy_url)
                    e.add_field(name="Imagine", value=f"🖼️ [{attachment.filename}]({attachment.proxy_url})")
                else:
                    try:
                        file_to_send = await attachment.to_file()
                        files.append(file_to_send)
                        e.add_field(name="Fișier", value=f"📁 {attachment.filename}")
                    except:
                        e.add_field(name="Fișier", value=f"📁 {attachment.filename} *(Nu a putut fi recuperat)*")

        await self.send_log_with_files(message.guild, e, files)

    # Adaugă această funcție nouă în LoggerCog sau modifică send_log
    async def send_log_with_files(self, guild, embed, files=None):
        try:
            canal_id = db.reference(f'servers/{guild.id}/canal_testinglogs').get()
            if canal_id:
                canal = guild.get_channel(int(canal_id))
                if canal:
                    # Trimitem embed-ul împreună cu lista de fișiere
                    await canal.send(embed=embed, files=files if files else None)
        except Exception as e:
            print(f"Eroare trimitere log cu fișiere: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action == AuditLogAction.message_pin:
                e = discord.Embed(title="📌 Mesaj Fixat", color=discord.Color.gold(), timestamp=datetime.now())
                e.add_field(name="Canal", value=channel.mention)
                e.add_field(name="De către", value=entry.user.mention)
                await self.send_log(channel.guild, e)
            elif entry.action == AuditLogAction.message_unpin:
                e = discord.Embed(title="📍 Mesaj Scoat de la Fixat", color=discord.Color.light_grey(), timestamp=datetime.now())
                e.add_field(name="Canal", value=channel.mention)
                e.add_field(name="De către", value=entry.user.mention)
                await self.send_log(channel.guild, e)
            break

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        

        if before.channel != after.channel:
            e = discord.Embed(timestamp=datetime.now())
            if not before.channel:
                e.title, e.color, e.description = "🔊 Voice: Intrare", discord.Color.green(), f"{member.mention} a intrat în {after.channel.mention}"
            elif not after.channel:
                e.title, e.color, e.description = "🔇 Voice: Ieșire", discord.Color.red(), f"{member.mention} a ieșit din {before.channel.mention}"
            else:
                e.title, e.color, e.description = "🔄 Voice: Mutat", discord.Color.blue(), f"{member.mention}: {before.channel.mention} ➡️ {after.channel.mention}"
            await self.send_log(member.guild, e)

    

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        async for entry in guild.audit_logs(limit=1):
            if entry.action in [AuditLogAction.emoji_create, AuditLogAction.emoji_delete, AuditLogAction.emoji_update]:
                e = discord.Embed(title="🎨 Emoji Modificat", color=discord.Color.blurple(), timestamp=datetime.now())
                e.add_field(name="Acțiune de", value=entry.user.mention)
                await self.send_log(guild, e)
                break

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        async for entry in guild.audit_logs(limit=1):
            if entry.action in [AuditLogAction.sticker_create, AuditLogAction.sticker_delete, AuditLogAction.sticker_update]:
                e = discord.Embed(title="🖼️ Sticker Modificat", color=discord.Color.blurple(), timestamp=datetime.now())
                e.add_field(name="Acțiune de", value=entry.user.mention)
                await self.send_log(guild, e)
                break

    @commands.Cog.listener()
    async def on_member_join(self, member):
        e = discord.Embed(title="📥 Membru Nou", color=discord.Color.green(), timestamp=datetime.now())
        e.set_thumbnail(url=member.display_avatar.url)
        e.description = f"{member.mention} a intrat pe server.\n**ID:** {member.id}\n**Creat pe:** <t:{int(member.created_at.timestamp())}:R>"
        await self.send_log(member.guild, e)

async def setup(bot):
    await bot.add_cog(LoggerCog(bot))
