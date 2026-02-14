import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread

# --- إعداد خادم وهمي لإبقاء البوت حياً في Render المجاني ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run():
    # Render يطلب بوابة معينة، هنا نخليه يسمع لكلامه
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

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# لتخزين الألعاب المرسلة (عشان ما يكرر)
sent_games = []

@bot.event
async def on_ready():
    # تاق البوت
    activity = discord.Game(name="Steam & Epic Tracker 🎁")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    print(f'✅ البوت شغال الآن: مراقب (Steam & Epic) فقط!')
    print(f'--- سيرفر: شلة المصافيق ---')
    
    # تشغيل مهمة البحث التلقائي
    if not check_free_games.is_running():
        check_free_games.start()

@tasks.loop(hours=1)
async def check_free_games():
    global sent_games
    async with aiohttp.ClientSession() as session:
        # البحث عن عروض الألعاب
        url = "https://www.gamerpower.com/api/giveaways?type=game&sort-by=date"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for game in data:
                        title = game['title']
                        platform = game['platforms']
                        
                        # الفلترة: ستيم وإيبك فقط
                        is_steam = "Steam" in platform
                        is_epic = "Epic Games Store" in platform
                        
                        if (is_steam or is_epic) and title not in sent_games:
                            for guild in bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="📢┃الأخبار-news")
                                if channel:
                                    # إعدادات الشكل حسب المتجر
                                    if is_steam:
                                        store_label = "STEAM 🎮"
                                        store_color = discord.Color.dark_blue()
                                    else:
                                        store_label = "EPIC GAMES �"
                                        store_color = discord.Color.blue()

                                    embed = discord.Embed(
                                        title=f"🎁 | لـعـبـة مـجـانـيـة جـديـدة عـلـى {store_label}",
                                        description=f"سـارع بـالـحـصـول عـلـى **{title}** الآن مـجـانـاً!\n\n**الوصف:** {game['description'][:300]}...",
                                        color=store_color
                                    )
                                    embed.set_image(url=game['image'])
                                    embed.add_field(name="الـمـتـجـر", value=store_label, inline=True)
                                    embed.add_field(name="الـرابـط", value=f"[اضغط هنا للتحميل]({game['open_giveaway_url']})", inline=True)
                                    embed.set_footer(text="Steam & Epic Tracker | شلة المصافيق")
                                    
                                    await channel.send(content="@everyone", embed=embed)
                                    sent_games.append(title)
                                    print(f"✅ تم إرسال لعبة من {store_label}: {title}")
                                    await asyncio.sleep(5)
                else:
                    print(f"❌ مشكلة في التحديث: {response.status}")
        except Exception as e:
            print(f"❌ خطأ: {e}")

@bot.command()
async def check(ctx):
    await ctx.send("🔍 جاري فحص (Steam & Epic) فوراً...")
    check_free_games.restart()

keep_alive() # تشغيل الخادم الوهمي
bot.run(TOKEN)