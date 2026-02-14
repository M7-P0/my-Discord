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
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- دالة الطباعة الفورية ---
def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

# --- الإعدادات ---
TOKEN = os.getenv('BOT_TOKEN')
PREFIX = '!'

intents = discord.Intents.all() # سنفعل كل شيء للتأكد من العمل
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    log(f'✅ البوت دخل بنجاح باسم: {bot.user}')
    log(f'� ID البوت: {bot.user.id}')
    
    # فحص القنوات المتاحة
    for guild in bot.guilds:
        log(f'🏠 السيرفر المشترك فيه: {guild.name}')
        channels = [c.name for c in guild.text_channels]
        log(f'📺 القنوات التي أراها: {channels}')
        
        # محاولة إرسال رسالة ترحيب في أول قناة يجدها
        for channel in guild.text_channels:
            try:
                await channel.send("🚀 **نظام التشخيص: البوت يعمل الآن ويسمعكم!**")
                log(f"✅ تم إرسال رسالة ترحيب في {channel.name}")
                break
            except: continue

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    log(f"📩 رسالة مستلمة من [{message.author}]: {message.content}")
    
    # الرد المباشر للتأكد من الاستجابة
    if message.content.startswith('!ping'):
        await message.channel.send("🏓 Pong! استلمت إشارتك يا أسطورة.")
    
    await bot.process_commands(message)

@bot.command()
async def check(ctx):
    await ctx.send("🔍 جاري جلب الأخبار...")
    # هنا سنعيد إضافة كود الأخبار بعد التأكد من أن البوت يسمعنا
    log("تم طلب فحص الأخبار يدوياً")

keep_alive()
bot.run(TOKEN)