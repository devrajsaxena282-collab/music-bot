import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio
from discord.ui import Button, View
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR UPTIMEROBOT ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- MUSIC BOT CODE ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="-", intents=intents)

# YTDL Options optimized for streaming
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class MusicControls(View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="⏸", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸ Paused", ephemeral=True)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶ Resumed", ephemeral=True)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.vc:
            self.vc.stop()
            await interaction.response.send_message("⏭ Skipped", ephemeral=True)

    @discord.ui.button(label="⏹", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        await self.vc.disconnect()
        await interaction.response.send_message("⏹ Stopped", ephemeral=True)

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        if ctx.voice_client:
            return await ctx.send("⚠️ Already connected")
        await ctx.author.voice.channel.connect()
        await ctx.send("✅ Joined voice channel")
    else:
        await ctx.send("❌ Voice channel join karo")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left voice channel")
    else:
        await ctx.send("❌ Already disconnected")

@bot.command(aliases=["p"])
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ Pehle voice channel join karo")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    async with ctx.typing():
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info['url']
            title = info['title']
            thumbnail = info.get("thumbnail")
            
            # Use FFmpeg with streaming options
            source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
            
            if vc.is_playing():
                vc.stop()
            
            vc.play(source)

            embed = discord.Embed(title="🎶 Now Playing", description=f"**{title}**", color=discord.Color.red())
            embed.set_thumbnail(url=thumbnail)
            await ctx.send(embed=embed, view=MusicControls(vc))
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

@bot.event
async def on_ready():
    print(f"🔥 Bot Online: {bot.user}")

# --- START BOT ---
keep_alive() # Server starts here
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ TOKEN NOT FOUND IN SECRETS!")
