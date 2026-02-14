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
def home(): return "The Elite Bot is Online and Stable!"

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

# ذاكرة البوت لمنع التكرار
sent_games = []

@bot.event
async def on_ready():
    # تظاهر البوت بمشاهدة تريندات الألعاب
    activity = discord.Activity(type=discord.ActivityType.watching, name="Gaming Trends 🚀")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    print(f'✅ البوت قيد التشغيل: {bot.user}')

    # تشغيل المهام التلقائية (الألعاب والإحصائيات فقط)
    if not check_free_games.is_running(): check_free_games.start()
    if not update_server_stats.is_running(): update_server_stats.start()

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
            
            stats_channels = {
                "total": f"👤┃أعضاء السيرفر: {total_members}",
                "online": f"🟢┃المتواجدين الآن: {online_members}"
            }
            
            for key, name in stats_channels.items():
                existing = next((vc for vc in category.voice_channels if (key == "total" and "أعضاء" in vc.name) or (key == "online" and "المتواجدين" in vc.name)), None)
                if existing:
                    if existing.name != name: await existing.edit(name=name)
                else:
                    overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False)}
                    await guild.create_voice_channel(name, category=category, overwrites=overwrites)
        except Exception as e: print(f"❌ خطأ إحصائيات: {e}")

# 2. صياد الألعاب المجانية (المستقر 100%)
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
                        # البحث عن ألعاب Steam و Epic فقط
                        if ("Steam" in game['platforms'] or "Epic" in game['platforms']) and title not in sent_games:
                            for guild in bot.guilds:
                                channel = next((c for c in guild.text_channels if "ألعاب" in c.name or "free" in c.name), None)
                                if channel:
                                    embed = discord.Embed(
                                        title=f"🎁 | لـعـبـة مـجـانـيـة جـديـدة",
                                        description=f"سارع بالحصول على **{title}** الآن مجاناً!\n\n**الوصف:** {game['description'][:300]}...",
                                        color=discord.Color.blue()
                                    )
                                    embed.set_image(url=game['image'])
                                    embed.add_field(name="الرابط", value=f"[اضغط هنا للتحميل]({game['open_giveaway_url']})", inline=False)
                                    await channel.send(content="@everyone", embed=embed)
                                    sent_games.append(title)
        except Exception as e: print(f"❌ خطأ في فحص الألعاب: {e}")

# --- الأوامر التفاعلية ---

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! البوت مستقر وشغال 24 ساعة.")

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 معلومات العضو: {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="انضم للديسكورد", value=member.created_at.strftime("%Y/%m/%d"))
    embed.add_field(name="انضم للسيرفر", value=member.joined_at.strftime("%Y/%m/%d"))
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 إحصائيات سيرفر: {guild.name}", color=discord.Color.gold())
    embed.add_field(name="الأعضاء الكلي", value=guild.member_count)
    embed.add_field(name="تاريخ التأسيس", value=guild.created_at.strftime("%Y/%m/%d"))
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    await ctx.message.delete()
    embed = discord.Embed(title="🗳️ تصويت جديد", description=f"**{question}**", color=discord.Color.blue())
    embed.set_footer(text=f"بواسطة: {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 100):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ تمت النظافة بنجاح!"); await asyncio.sleep(3); await msg.delete()

@bot.command()
async def check(ctx):
    await ctx.send("🔍 جاري فحص الألعاب المجانية فوراً...")
    check_free_games.restart()

# --- حماية السيرفر ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # منع روابط الدعوات للأعضاء العاديين
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}، يمنع نشر الروابط!", delete_after=5)
            return

    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)