import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread
import datetime

# --- إعداد خادم ريندر لإبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "The Elite Bot is Online and Healthy!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات ---
TOKEN = os.getenv('BOT_TOKEN')
PREFIX = '!'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ذاكرة البوت
sent_games = []
sent_news = []

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching, name="Gaming Trends 🚀")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f'✅ البوت متصل ومستعد للعمل!')

    # تشغيل المهام التلقائية
    if not check_free_games.is_running(): check_free_games.start()
    if not update_server_stats.is_running(): update_server_stats.start()
    if not check_gaming_news.is_running(): check_gaming_news.start()

# 1. نظام إحصائيات السيرفر (يتحدث كل 10 دقائق)
@tasks.loop(minutes=10)
async def update_server_stats():
    for guild in bot.guilds:
        try:
            category_name = "📊┃إحصائيات السيرفر"
            category = discord.utils.get(guild.categories, name=category_name)
            if not category: category = await guild.create_category(category_name, position=0)
            
            total_members = guild.member_count
            online_members = len([m for m in guild.members if m.status != discord.Status.offline])
            
            stats_channels = {"total": f"👤┃أعضاء السيرفر: {total_members}", "online": f"🟢┃المتواجدين الآن: {online_members}"}
            
            for key, name in stats_channels.items():
                existing = None
                for vc in category.voice_channels:
                    if "أعضاء" in vc.name and key == "total": existing = vc
                    if "المتواجدين" in vc.name and key == "online": existing = vc
                if existing:
                    if existing.name != name: await existing.edit(name=name)
                else:
                    await guild.create_voice_channel(name, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
        except Exception as e: print(f"❌ خطأ إحصائيات: {e}")

# 2. رادار أخبار الألعاب
@tasks.loop(hours=1)
async def check_gaming_news():
    global sent_news
    url = "https://newsapi.org/v2/everything?q=gaming+release+trailer&sortBy=publishedAt&language=en&apiKey=112eb229202747198a96e5eb69e15ad0"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for article in data.get('articles', [])[:2]:
                        title = article['title']
                        if title and title not in sent_news:
                            for guild in bot.guilds:
                                # يبحث عن قناة فيها كلمة "أخبار" أو "news"
                                channel = next((c for c in guild.text_channels if "أخبار" in c.name or "news" in c.name or "gaming" in c.name), None)
                                if channel:
                                    embed = discord.Embed(title=f"� | خبر عـاجـل: {title}", description=f"{article['description'][:300]}...", url=article['url'], color=discord.Color.red())
                                    if article.get('urlToImage'): embed.set_image(url=article['urlToImage'])
                                    embed.set_footer(text="Gaming News Hub")
                                    await channel.send(embed=embed)
                                    sent_news.append(title)
        except Exception as e: print(f"❌ خطأ أخبار: {e}")

# 3. صياد الألعاب المجانية
@tasks.loop(hours=1)
async def check_free_games():
    global sent_games
    url = "https://www.gamerpower.com/api/giveaways?type=game&sort-by=date"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for game in data:
                        title = game['title']
                        if ("Steam" in game['platforms'] or "Epic" in game['platforms']) and title not in sent_games:
                            for guild in bot.guilds:
                                channel = next((c for c in guild.text_channels if "ألعاب" in c.name or "free" in c.name), None)
                                if channel:
                                    embed = discord.Embed(title=f"🎁 | لـعـبـة مـجـانـيـة جـديـدة", description=f"**{title}**\n\n{game['description'][:300]}...", color=discord.Color.blue())
                                    embed.set_image(url=game['image'])
                                    embed.add_field(name="الرابط", value=f"[اضغط هنا للتحميل]({game['open_giveaway_url']})")
                                    await channel.send(content="@everyone", embed=embed)
                                    sent_games.append(title)
        except Exception as e: print(f"❌ خطأ ألعاب: {e}")

# --- الأوامر ---
@bot.command()
async def ping(ctx): await ctx.send("🏓 Pong! البوت شغال 100%.")

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="انضم للديسكورد", value=member.created_at.strftime("%Y/%m/%d"))
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 إحصائيات: {guild.name}", color=discord.Color.gold())
    embed.add_field(name="الأعضاء الكلي", value=guild.member_count)
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    await ctx.message.delete()
    embed = discord.Embed(title="🗳️ تصويت جديد", description=f"**{question}**", color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 100):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ تمت النظافة!", delete_after=3)

@bot.command()
async def check(ctx):
    await ctx.send("🔍 جاري فحص الأخبار والألعاب فوراً...")
    check_free_games.restart()
    check_gaming_news.restart()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)