import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread
import datetime

# --- إعداد خادم ريندر (مصلح لمشكلة "الإخراج كبير") ---
app = Flask('')
@app.route('/')
def home():
    return "OK", 200 # رد مختصر جداً مع حالة نجاح 200

def run():
    port = int(os.environ.get("PORT", 8080))
    # إيقاف رسائل التفاصيل المزعجة في السيرفر لتقليل حجم البيانات
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

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
    print(f'⏳ جاري تجهيز بيانات البوت لـ {bot.user}...')
    try:
        activity = discord.Activity(type=discord.ActivityType.watching, name="Gaming Trends 🚀")
        await bot.change_presence(status=discord.Status.online, activity=activity)
        print('✅ تم تحديث حالة البوت (Online).')

        if not check_free_games.is_running(): 
            check_free_games.start()
            print('🎮 تم تشغيل نظام الألعاب المجانية.')
            
        if not update_server_stats.is_running(): 
            update_server_stats.start()
            print('📊 تم تشغيل نظام الإحصائيات.')
            
        print(f'🚀 البوت الآن جاهز تماماً لاستقبال الأوامر في {len(bot.guilds)} سيرفر!')
    except Exception as e:
        print(f'❌ خطأ في مرحلة البدء: {e}')

# 1. نظام إحصائيات السيرفر (يتحدث كل 30 دقيقة لتجنب الحظر)
@tasks.loop(minutes=30)
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

# 2. صياد الألعاب المجانية
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
async def ping(ctx): await ctx.send("🏓 Pong! البوت شغال ومستقر.")

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
    await ctx.send("🔍 جاري فحص الألعاب المجانية فوراً...")
    check_free_games.restart()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # منع روابط الدعوات
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            return

    await bot.process_commands(message)

@bot.command()
@commands.is_owner() # للتأكد أنك أنت فقط من تستطيع تشغيل هذا الأمر
async def setup_server(ctx):
    guild = ctx.guild
    await ctx.send("⏳ جاري ضبط السيرفر حسب طلبك...")

    # 1. إعداد رتبة Founder (كل الصلاحيات ماعدا الإدارة العليا والتحكم بالبوت)
    founder_perms = discord.Permissions(
        kick_members=True, ban_members=True, manage_messages=True, 
        manage_nicknames=True, mute_members=True, deafen_members=True, 
        move_members=True, view_audit_log=True, manage_expressions=True,
        request_to_speak=True, send_messages=True, view_channel=True,
        read_message_history=True, connect=True, speak=True, stream=True,
        use_application_commands=True, embed_links=True, attach_files=True,
        add_reactions=True, use_external_emojis=True, mention_everyone=True
    )
    # نلاحظ أن administrator=False و manage_roles=False و manage_guild=False لمنعهم من التحكم بالبوت
    
    founder_role = discord.utils.get(guild.roles, name="Founder")
    if not founder_role:
        founder_role = await guild.create_role(name="Founder", permissions=founder_perms, color=discord.Color.red(), hoist=True)
        await ctx.send("✅ تم إنشاء رتبة Founder بصلاحيات قوية ولكن محدودة.")
    else:
        await founder_role.edit(permissions=founder_perms)
        await ctx.send("✅ تم تحديث صلاحيات Founder.")

    # 2. إعداد رتبة "ذا كرو"
    crew_role = discord.utils.get(guild.roles, name="ذا كرو")
    if not crew_role:
        crew_role = await guild.create_role(name="ذا كرو", color=discord.Color.blue(), hoist=True)
        await ctx.send("✅ تم إنشاء رتبة ذا كرو.")

    # 3. إعداد قسم الإدارة (لك أنت فقط)
    admin_category = discord.utils.get(guild.categories, name="الادارة")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False), # إخفاء عن الكل
        founder_role: discord.PermissionOverwrite(view_channel=False),        # إخفاء عن الفاوندر
        guild.me: discord.PermissionOverwrite(view_channel=True)              # إظهار للبوت (عشان يقدر يخدمك)
    }
    
    if not admin_category:
        admin_category = await guild.create_category("الادارة", overwrites=overwrites)
        await guild.create_text_channel("سجل-الادارة", category=admin_category)
        await ctx.send("🔒 تم إنشاء قسم الادارة (مخفي عن الجميع حتى الفاوندر).")
    else:
        await admin_category.edit(overwrites=overwrites)
        await ctx.send("🔒 تم تحديث خصوصية قسم الادارة.")

    await ctx.send("✨ تم الانتهاء من ضبط السيرفر بنجاح!")

if __name__ == "__main__":
    print("🚀 جاري بدء تشغيل نظام الـ Keep Alive...")
    keep_alive()
    print("🤖 جاري محاولة تسجيل دخول البوت...")
    try:
        if TOKEN:
            bot.run(TOKEN)
        else:
            print("❌ خطأ: TOKEN مفقود!")
    except Exception as e:
        print(f"❌ فشل البوت في العمل: {e}")