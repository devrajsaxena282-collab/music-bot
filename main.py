import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio
from discord.ui import Button, View
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run(): app.run(host='0.0.0.0', port=5000)
def keep_alive(): Thread(target=run).start()

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="-", intents=intents)

# Queue storage: {guild_id: [list_of_sources]}
song_queues = {}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queues and song_queues[guild_id]:
        next_song = song_queues[guild_id].pop(0)
        source = discord.FFmpegPCMAudio(next_song['url'], **ffmpeg_options)
        ctx.voice_client.play(source, after=lambda e: play_next(ctx))
        
        # Announcement (Optional: Message bhej sakta hai)
        asyncio.run_coroutine_threadsafe(ctx.send(f"🎶 Now playing next: **{next_song['title']}**"), bot.loop)

class MusicControls(View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="⏸", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("Paused", ephemeral=True)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("Resumed", ephemeral=True)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.stop() # play_next apne aap trigger ho jayega
            await interaction.response.send_message("Skipped", ephemeral=True)

@bot.command(aliases=["p"])
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ Join a voice channel first!")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client
    guild_id = ctx.guild.id

    async with ctx.typing():
        info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        song_data = {'url': info['url'], 'title': info['title']}

        if vc.is_playing() or vc.is_paused():
            if guild_id not in song_queues:
                song_queues[guild_id] = []
            song_queues[guild_id].append(song_data)
            await ctx.send(f"✅ Added to queue: **{info['title']}**")
        else:
            source = discord.FFmpegPCMAudio(song_data['url'], **ffmpeg_options)
            vc.play(source, after=lambda e: play_next(ctx))
            
            embed = discord.Embed(title="🎶 Now Playing", description=f"**{info['title']}**", color=discord.Color.red())
            await ctx.send(embed=embed, view=MusicControls(vc))

@bot.event
async def on_ready():
    print(f"🔥 Bot Online: {bot.user}")

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
