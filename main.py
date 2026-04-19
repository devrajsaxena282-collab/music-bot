import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
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

queues = {}
ytdl_opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'auto', 'nocheckcertificate': True}
ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn', 
    'executable': 'ffmpeg'
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

# --- BUTTON INTERFACE ---
class MusicControls(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Feature: Previous", ephemeral=True)
    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, row=0)
    async def rewind(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Feature: Rewind", ephemeral=True)
    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0)
    async def pause(self, i: discord.Interaction, b: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.pause()
            await i.response.send_message("⏸️ Paused", ephemeral=True)
        elif self.ctx.voice_client and self.ctx.voice_client.is_paused():
            self.ctx.voice_client.resume()
            await i.response.send_message("▶️ Resumed", ephemeral=True)
    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, row=0)
    async def forward(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Feature: Forward", ephemeral=True)
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=0)
    async def skip(self, i: discord.Interaction, b: discord.ui.Button):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()
            await i.response.send_message("⏭️ Skipped!", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def vol(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Volume Control", ephemeral=True)
    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Loop Toggled", ephemeral=True)
    @discord.ui.button(emoji="❤️", style=discord.ButtonStyle.secondary, row=1)
    async def like(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Liked!", ephemeral=True)
    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, row=1)
    async def loop_one(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Loop One Toggled", ephemeral=True)

    @discord.ui.button(emoji="📜", style=discord.ButtonStyle.secondary, row=2)
    async def queue_list(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Queue Display", ephemeral=True)
    @discord.ui.button(emoji="✨", style=discord.ButtonStyle.secondary, row=2)
    async def effect(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_message("Audio Effects", ephemeral=True)
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=2)
    async def stop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        if self.ctx.voice_client:
            queues[self.ctx.guild.id] = []
            await self.ctx.voice_client.disconnect()
            await i.response.send_message("⏹️ Stopped & Disconnected!", ephemeral=True)

# --- CORE LOGIC ---
def play_next(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        song = queues[ctx.guild.id].pop(0)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song['url'], **ffmpeg_opts))
        def after_playing(error):
            if error: print(f"Error: {error}")
            asyncio.run_coroutine_threadsafe(next_song_trigger(ctx), bot.loop)
        ctx.voice_client.play(source, after=after_playing)
        asyncio.run_coroutine_threadsafe(send_playing_embed(ctx, song), bot.loop)
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("🏁 Queue Finished!"), bot.loop)

async def send_playing_embed(ctx, song):
    embed = discord.Embed(title="🎶 Now Playing", description=f"**{song['title']}**", color=0x00FF00)
    if 'thumb' in song: embed.set_thumbnail(url=song['thumb'])
    await ctx.send(embed=embed, view=MusicControls(ctx))

async def next_song_trigger(ctx): play_next(ctx)

# --- COMMANDS ---

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command(name="join")
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("✅ Joined the voice channel!")
    else: await ctx.send("❌ You need to be in a voice channel!")

@bot.command(name="play", aliases=["p"])
async def play(ctx, *, query):
    if not ctx.author.voice: return await ctx.send("❌ Join a channel first!")
    async with ctx.typing():
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            if ctx.guild.id not in queues: queues[ctx.guild.id] = []
            song_data = {'url': info['url'], 'title': info['title'], 'thumb': info['thumbnail'], 'duration': info.get('duration', '0:00'), 'author': info.get('uploader', 'Unknown'), 'requester': ctx.author.mention}
            queues[ctx.guild.id].append(song_data)
            embed = discord.Embed(title="Enqueued", description=f"**{song_data['title']}**", color=0xFFFF00)
            embed.add_field(name="Author", value=song_data['author'], inline=True)
            embed.add_field(name="Duration", value=song_data['duration'], inline=True)
            embed.add_field(name="Requester", value=song_data['requester'], inline=True)
            if 'thumb' in song_data: embed.set_thumbnail(url=song_data['thumb'])
            await ctx.send(embed=embed)
            if not ctx.voice_client:
                await ctx.author.voice.channel.connect()
                play_next(ctx)
            elif not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused(): play_next(ctx)
        except Exception as e: await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="skip")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped!")
    else: await ctx.send("❌ Nothing is playing.")

@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        ctx.voice_client.stop()
        await ctx.send("⏹️ Music stopped and queue cleared.")
    else: await ctx.send("❌ I'm not playing anything.")

@bot.command(name="leave", aliases=["dc", "disconnect"])
async def leave(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")
    else: await ctx.send("❌ I'm not in a voice channel.")

@bot.command(name="purge")
async def purge(ctx, limit: int = 100):
    await ctx.channel.purge(limit=limit + 1)
    await ctx.send(f"🧹 Purged {limit} messages.", delete_after=5)

@bot.event
async def on_ready(): print(f"🔥 Bot Online: {bot.user}")

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
