import discord
from discord.ext import commands
import yt_dlp
import os
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="-", intents=intents)

ytdl = yt_dlp.YoutubeDL({
    'format': 'bestaudio',
    'quiet': True
})

ffmpeg_options = {
    'options': '-vn'
}

# 🎛 CONTROL BUTTONS
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
        self.vc.stop()
        await interaction.response.send_message("⏭ Skipped", ephemeral=True)

    @discord.ui.button(label="⏹", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        await self.vc.disconnect()
        await interaction.response.send_message("⏹ Stopped", ephemeral=True)

# 🔊 JOIN
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("✅ Joined voice channel")
    else:
        await ctx.send("❌ Voice channel join karo")

# 👋 LEAVE
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left voice channel")

# 🎶 PLAY
@bot.command(aliases=["p"])
async def play(ctx, *, query):

    if not ctx.author.voice:
        return await ctx.send("❌ Pehle voice channel join karo")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client

    try:
        info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
    except:
        return await ctx.send("❌ Song not found")

    url = info['url']
    title = info['title']
    duration = info.get("duration", 0)
    thumbnail = info.get("thumbnail")

    source = discord.FFmpegPCMAudio(
        url,
        executable="ffmpeg",
        options="-vn"
    )

    vc.stop()
    vc.play(source)

    embed = discord.Embed(
        title="🎶 Now Playing",
        description=f"**{title}**",
        color=discord.Color.dark_red()
    )

    embed.add_field(name="Duration", value=f"{duration//60}:{duration%60:02d}")
    embed.set_thumbnail(url=thumbnail)

    view = MusicControls(vc)

    await ctx.send(embed=embed, view=view)

# 🔥 BOT READY
@bot.event
async def on_ready():
    print(f"🔥 Bot Online: {bot.user}")

# 🔐 TOKEN (RAILWAY SAFE)
bot.run(os.getenv("DISCORD_TOKEN"))