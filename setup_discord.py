import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread
import datetime

# --- إعداد خادم وهمي لإبقاء البوت حياً في Render ---
app = Flask('')
@app.route('/')
def home():
    return "Diagnostic Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات ---
TOKEN = os.getenv('BOT_TOKEN')
PREFIX = '!'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ذاكرة البوت
sent_games = []
sent_news = []

@bot.event
async def on_ready():
    print(f'--- تشخيص البوت بدأ ---')
    print(f'✅ متصل باسم: {bot.user}')
    print(f'Servers: {[g.name for g in bot.guilds]}')
    
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
            
            stats_channels = {"total": f"👤┃الأعضاء: {total_members}", "online": f"🟢┃أونلاين: {online_members}"}
            
            for key, name in stats_channels.items():
                existing = None
                for vc in category.voice_channels:
                    if "الأعضاء" in vc.name and key == "total": existing = vc
                    if "أونلاين" in vc.name and key == "online": existing = vc
                if existing:
                    if existing.name != name: await existing.edit(name=name)
                else:
                    await guild.create_voice_channel(name, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
        except Exception as e: print(f"❌ خطأ إحصائيات: {e}")

# 2. رادار أخبار الألعاب (نسخة التشخيص)
@tasks.loop(hours=1)
async def check_gaming_news():
    global sent_news
    print(f"🔍 بدأ فحص الأخبار في: {datetime.datetime.now()}")
    
    # استخدام مفتاح API بديل وعام
    url = "https://newsapi.org/v2/everything?q=gaming&sortBy=publishedAt&language=en&apiKey=112eb229202747198a96e5eb69e15ad0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=10) as response:
                print(f"📡 استجابة الخبر: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('articles', [])
                    print(f"📰 عدد الأخبار المستلمة: {len(articles)}")
                    
                    if not articles:
                        print("⚠️ لم يتم العثور على أخبار جديدة من المصدر.")
                        return

                    for article in articles[:3]: # نأخذ أول 3 أخبار
                        title = article.get('title')
                        if title and title not in sent_news:
                            for guild in bot.guilds:
                                # البحث عن أي قناة فيها "news" أو "أخبار"
                                channel = next((c for c in guild.text_channels if "news" in c.name.lower() or "أخبار" in c.name), None)
                                
                                if channel:
                                    print(f"🎯 وجدت القناة: {channel.name}")
                                    embed = discord.Embed(title=f"📰 | {title}", description=f"{article['description'][:200]}...", url=article['url'], color=discord.Color.red())
                                    if article.get('urlToImage'): embed.set_image(url=article['urlToImage'])
                                    await channel.send(embed=embed)
                                    sent_news.append(title)
                                else:
                                    print(f"❌ لم أجد قناة باسم يحتوي على 'news' أو 'أخبار' في سيرفر {guild.name}")
                        else:
                            print(f"Skipping article: {title}")
                else:
                    print(f"❌ فشل الاتصال بمصدر الأخبار. كود الحالة: {response.status}")
        except Exception as e:
            print(f"❌ خطأ فادح في نظام الأخبار: {e}")

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
                                channel = next((c for c in guild.text_channels if "ألعاب" in c.name or "free" in c.name or "giveaway" in c.name), None)
                                if channel:
                                    embed = discord.Embed(title=f"🎁 | {title}", description=game['description'][:200], color=discord.Color.blue())
                                    embed.set_image(url=game['image'])
                                    embed.add_field(name="الرابط", value=f"[اضغط هنا للتحميل]({game['open_giveaway_url']})")
                                    await channel.send(content="@everyone", embed=embed)
                                    sent_games.append(title)
                                    print(f"🎁 تم إرسال لعبة مجانية: {title}")
        except Exception as e: print(f"❌ خطأ ألعاب: {e}")

@bot.command()
async def check(ctx):
    await ctx.send("🕵️‍♂️ جاري فحص جميع الأنظمة وإرسال التقارير للسجلات...")
    check_gaming_news.restart()
    check_free_games.restart()

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="ID", value=member.id)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 100):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ تمت النظافة!", delete_after=3)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)