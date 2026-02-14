import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
import re
from flask import Flask
from threading import Thread
import datetime

# --- إعداد خادم وهمي لإبقاء البوت حياً في Render ---
app = Flask('')
@app.route('/')
def home():
    return "The Ultimate Bot is Online!"

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
intents.members = True # مهم للإحصائيات ومعلومات الأعضاء

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ذاكرة البوت لمنع التكرار
sent_games = []
sent_news = []

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching, name="Gaming Trends 🚀")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    print(f'✅ نظام [ شلة المصافيق ] جاهز للعمل!')
    
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
            if not category:
                category = await guild.create_category(category_name, position=0)
            
            total_members = guild.member_count
            online_members = len([m for m in guild.members if m.status != discord.Status.offline])
            
            stats_channels = {
                "total": f"👤┃أعضاء السيرفر: {total_members}",
                "online": f"🟢┃المتواجدين الآن: {online_members}"
            }
            
            for key, name in stats_channels.items():
                existing_channel = None
                for vc in category.voice_channels:
                    if "أعضاء" in vc.name and key == "total": existing_channel = vc
                    if "المتواجدين" in vc.name and key == "online": existing_channel = vc
                
                if existing_channel:
                    if existing_channel.name != name: await existing_channel.edit(name=name)
                else:
                    overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False)}
                    await guild.create_voice_channel(name, category=category, overwrites=overwrites)
        except Exception as e:
            print(f"❌ خطأ الإحصائيات: {e}")

# 2. رادار أخبار الألعاب
@tasks.loop(hours=1)
async def check_gaming_news():
    global sent_news
    news_api_key = "112eb229202747198a96e5eb69e15ad0"
    url = f"https://newsapi.org/v2/everything?q=gaming&sortBy=publishedAt&language=en&apiKey={news_api_key}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('articles', [])[:2]
                    for article in articles:
                        title = article['title']
                        if title not in sent_news:
                            for guild in bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="📢┃الأخبار-news")
                                if channel:
                                    embed = discord.Embed(title=f"📰 | خبر عـاجـل: {title}", description=f"{article['description'][:300]}...", url=article['url'], color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
                                    if article.get('urlToImage'): embed.set_image(url=article['urlToImage'])
                                    embed.set_footer(text="Gaming News | شلة المصافيق")
                                    await channel.send(embed=embed)
                                    sent_news.append(title)
                                    if len(sent_news) > 50: sent_news.pop(0)
        except Exception as e: print(f"❌ خطأ الأخبار: {e}")

# 3. صياد الألعاب المجانية
@tasks.loop(hours=1)
async def check_free_games():
    global sent_games
    async with aiohttp.ClientSession() as session:
        url = "https://www.gamerpower.com/api/giveaways?type=game&sort-by=date"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for game in data:
                        title, platform = game['title'], game['platforms']
                        if ("Steam" in platform or "Epic" in platform) and title not in sent_games:
                            for guild in bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="📢┃الأخبار-news")
                                if channel:
                                    store = "STEAM 🎮" if "Steam" in platform else "EPIC GAMES 🔥"
                                    color = discord.Color.dark_blue() if "Steam" in platform else discord.Color.blue()
                                    embed = discord.Embed(title=f"🎁 | لـعـبـة مـجـانـيـة جـديـدة ({store})", description=f"**{title}**\n\n{game['description'][:300]}...", color=color)
                                    embed.set_image(url=game['image'])
                                    embed.add_field(name="الرابط", value=f"[اضغط هنا]({game['open_giveaway_url']})")
                                    await channel.send(content="@everyone", embed=embed)
                                    sent_games.append(title)
        except Exception as e: print(f"❌ خطأ الألعاب: {e}")

# --- 4. أوامر المعلومات والفعاليات 📊 (الجديدة) ---

@bot.command()
async def user(ctx, member: discord.Member = None):
    """يظهر معلومات العضو"""
    member = member or ctx.author
    roles = [role.name for role in member.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"👤 معلومات العضو: {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="الاسم الكامل", value=member, inline=True)
    embed.add_field(name="ID العضو", value=member.id, inline=True)
    embed.add_field(name="انضم للديسكورد", value=member.created_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="انضم للسيرفر", value=member.joined_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="الرتب", value=", ".join(roles) if roles else "لا توجد رتب", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    """يظهر إحصائيات السيرفر"""
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 إحصائيات سيرفر: {guild.name}", color=discord.Color.gold())
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="صاحب السيرفر", value=guild.owner, inline=True)
    embed.add_field(name="الأعضاء الكلي", value=guild.member_count, inline=True)
    embed.add_field(name="تاريخ التأسيس", value=guild.created_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="عدد القنوات", value=len(guild.channels), inline=True)
    embed.add_field(name="عدد الرتب", value=len(guild.roles), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    """يسوي تصويت سريع"""
    await ctx.message.delete()
    embed = discord.Embed(title="🗳️ تصويت جديد", description=f"**{question}**", color=discord.Color.blue())
    embed.set_footer(text=f"بواسطة: {ctx.author.display_name}")
    poll_msg = await ctx.send(embed=embed)
    await poll_msg.add_reaction("✅")
    await poll_msg.add_reaction("❌")

# أوامر الإدارة الأساسية
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 100):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ تم تنظيف **{amount}** رسالة."); await asyncio.sleep(3); await msg.delete()

@bot.command()
async def check(ctx):
    await ctx.send("🕵️‍♂️ جاري الفحص الفوري..."); check_free_games.restart(); check_gaming_news.restart()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if "discord.gg/" in message.content.lower() and not message.author.guild_permissions.manage_messages:
        await message.delete(); await message.channel.send(f"⚠️ {message.author.mention}، يمنع نشر الروابط!", delete_after=5)
    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)