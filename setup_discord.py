import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread
import datetime

# --- إعداد خادم ريندر ---
app = Flask('')
@app.route('/')
def home(): return "The Elite Bot is Online!"

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
    print(f'✅ البوت قيد التشغيل: {bot.user}')

    if not check_free_games.is_running(): check_free_games.start()
    if not update_server_stats.is_running(): update_server_stats.start()
    if not check_gaming_news.is_running(): check_gaming_news.start()

# 1. نظام إحصائيات السيرفر
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
                existing = next((vc for vc in category.voice_channels if (key == "total" and "أعضاء" in vc.name) or (key == "online" and "المتواجدين" in vc.name)), None)
                if existing:
                    if existing.name != name: await existing.edit(name=name)
                else:
                    await guild.create_voice_channel(name, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
        except Exception as e: print(f"❌ خطأ إحصائيات: {e}")

# 2. رادار أخبار الألعاب (المحسن بمصدر بديل)
@tasks.loop(hours=1)
async def check_gaming_news():
    global sent_news
    # استراتيجية جديدة: البحث بكلمات محددة واستخدام "User-Agent" فخم
    url = "https://newsapi.org/v2/top-headlines?category=technology&q=gaming&apiKey=112eb229202747198a96e5eb69e15ad0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('articles', [])
                    for article in articles[:3]: # نأخذ أول 3 أخبار عاجلة
                        title = article.get('title')
                        if title and title not in sent_news:
                            for guild in bot.guilds:
                                channel = next((c for c in guild.text_channels if "news" in c.name.lower() or "أخبار" in c.name), None)
                                if channel:
                                    embed = discord.Embed(title=f"📰 | {title}", description=f"{article.get('description', '')[:250]}...", url=article['url'], color=discord.Color.red())
                                    if article.get('urlToImage'): embed.set_image(url=article['urlToImage'])
                                    embed.set_footer(text="Gaming News | شلة المصافيق")
                                    await channel.send(embed=embed)
                                    sent_news.append(title)
                                    if len(sent_news) > 50: sent_news.pop(0)
                else:
                    print(f"❌ خطأ في جلب الأخبار: {response.status}")
        except Exception as e: print(f"❌ خطأ رادار الأخبار: {e}")

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

@bot.command()
async def ping(ctx): await ctx.send("🏓 Pong! البوت شغال وسريع.")

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="انضم للديسكورد", value=member.created_at.strftime("%Y/%m/%d"))
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    embed = discord.Embed(title=f"📊 إحصائيات: {ctx.guild.name}", color=discord.Color.gold())
    embed.add_field(name="الأعضاء الكلي", value=ctx.guild.member_count)
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
    await ctx.send("🔍 جاري جلب آخر الأخبار والألعاب المجانية...")
    check_free_games.restart()
    check_gaming_news.restart()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)