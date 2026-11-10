import asyncio
import os
from flask import Flask
from threading import Thread
import discord
from discord import TextStyle
from discord.ext import commands
from discord.ui import Modal, Select, TextInput, View

# ---------------------------------------------------------
# 1. إعداد سيرفر Flask لضمان التشغيل 24/7 مع UptimeRobot
# ---------------------------------------------------------
app = Flask("")


@app.route("/")
def home():
  return "Advanced Ticket Bot is active 24/7!"


def run_flask():
  app.run(host="0.0.0.0", port=10000)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# ---------------------------------------------------------
# 2. إعدادات البوت والـ IDs للرتب والرومات والعدادات التصاعدية
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=["!"], intents=intents)

# عدادات التكتات التصاعدية لكل قسم
ticket_counters = {
    "وسيط": 1,
    "تطوير": 1,
    "هلاوين": 1,
    "دعم": 1
}

PANEL_CONFIG = {
    "title": "نحن هنا لخدمتك",
    "description": (
        "يرجى اختيار نوع طلبك من القائمة أدناه، ثم أجب على الأسئلة المطلوبة"
        " وسيتم إنشاء التذكرة تلقائياً."
    ),
    "color": 0x6A0DAD, # اللون البنفسجي الرسمي
}

# IDs الرتب الخاصة بكل قسم
ROLE_IDS = {
    "وسيط": 1555673464470376479,
    "تطوير": 1561565278045736970,
    "دعم": 1555335120582344784,
    "هلاوين": 1562309878695985272,
}

# آيدي روم التقييمات الصحيح
VOUCHES_CHANNEL_ID = 1555521230419922974


# ---------------------------------------------------------
# 3. أزرار التحكم داخل التكت (مع إضافة الإيموجيات المطلوبة)
# ---------------------------------------------------------
class TicketControlView(View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="استلام التكت", style=discord.ButtonStyle.green, emoji="🛡️", custom_id="claim_ticket"
  )
  async def claim_ticket(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if not interaction.user.guild_permissions.manage_channels:
      await interaction.response.send_message(
          "❌ عذراً، الإدارة فقط هي من تستطيع استلام التكت!", ephemeral=True
      )
      return

    claim_embed = discord.Embed(
        description=f"تم استلام التذكره بواسطة {interaction.user.mention}",
        color=discord.Color.green(),
    )

    message = interaction.message
    if message.embeds:
      main_embed = message.embeds[0]
      claimed_already = False
      for field in main_embed.fields:
        if field.name == "📌 حالة التذكرة":
          claimed_already = True
          break

      if claimed_already:
        await interaction.response.send_message(
            "⚠️ هذه التذكرة مستلمة بالفعل!", ephemeral=True
        )
        return

      main_embed.add_field(
          name="📌 حالة التذكرة",
          value=f"تم استلام التذكرة بواسطة: {interaction.user.mention}",
          inline=False,
      )
      await message.edit(embed=main_embed)

    await interaction.response.send_message(embed=claim_embed, ephemeral=False)

  @discord.ui.button(
      label="قفل التكت", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_ticket"
  )
  async def close_ticket(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if not interaction.user.guild_permissions.manage_channels:
      await interaction.response.send_message(
          "❌ عذراً، الإدارة فقط هي من تستطيع إغلاق التكت!", ephemeral=True
      )
      return
    await interaction.response.send_message("🛑 جاري إغلاق التكت وحذفه...")
    await asyncio.sleep(3)
    await interaction.channel.delete()


# ---------------------------------------------------------
# 4. نظام الرد التلقائي عند كتابة الأرقام (1, 2, 3, 4) داخل التكتات
# ---------------------------------------------------------
@bot.event
async def on_message(message):
  if message.author.bot:
    return

  if "تكت" in message.channel.name or "وسيط" in message.channel.name or "دعم" in message.channel.name or "تطوير" in message.channel.name or "هلاوين" in message.channel.name:
    content = message.content.strip()

    team_data = None
    if content == "1":
      team_data = ("كان معكم الوسيط", "🤝", discord.Color.gold())
    elif content == "2":
      team_data = ("كان معكم من فريق الدعم الفني", "🎧", discord.Color.red())
    elif content == "3":
      team_data = ("كان معكم من فريق الرسامين", "🎨", discord.Color.purple())
    elif content == "4":
      team_data = ("كان معكم من فريق التطوير", "📊", discord.Color.blue())

    if team_data:
      title_text, emoji_icon, embed_color = team_data

      async for msg in message.channel.history(limit=20):
        if msg.author == bot.user and msg.embeds:
          for emb in msg.embeds:
            if (
                emb.description
                and "تم استلام التذكره بواسطة" in emb.description
            ):
              try:
                await msg.delete()
              except:
                pass

      try:
        await message.delete()
      except:
        pass

      vouch_mention = f"<#{VOUCHES_CHANNEL_ID}>"

      embed = discord.Embed(
          description=(
              f"{emoji_icon} {title_text}: {message.author.mention}\n\n"
              "شكراً لتعاملكم معنا! نرجو منكم كتابة تقييمكم للخدمة في روم"
              f" التقييمات:\n{vouch_mention}\n\n"
              "نتمنى لكم يوماً سعيداً! ❤️"
          ),
          color=embed_color,
      )

      await message.channel.send(embed=embed)

  await bot.process_commands(message)


# ---------------------------------------------------------
# 5. الاستمارات الخاصة بكل قسم مع العدادات التصاعدية وسحب يوزر الطرف الثاني
# ---------------------------------------------------------

# أ) استمارة الوسيط (مع إضافة الطرف الثاني تلقائياً)
class MiddlemanModal(Modal, title="تفاصيل صفقة الوساطة"):

  def __init__(self):
    super().__init__()

  get_item = TextInput(
      label="وش بتاخذ؟",
      style=TextStyle.paragraph,
      placeholder="اكتب ما ستستلمه...",
      required=True,
  )
  give_item = TextInput(
      label="وش بتعطي؟",
      style=TextStyle.paragraph,
      placeholder="اكتب ما ستقدمه...",
      required=True,
  )
  other_user = TextInput(
      label="يوزر الطرف الثاني بالديسكورد",
      style=TextStyle.short,
      placeholder="اكتب يوزر الطرف الثاني...",
      required=True,
  )
  tip = TextInput(
      label="التيب او الهديه/غير إلزامي",
      style=TextStyle.short,
      placeholder="اكتب التيب إن وجد...",
      required=False,
  )

  async def on_submit(self, interaction: discord.Interaction):
    global ticket_counters
    guild = interaction.guild
    num = ticket_counters["وسيط"]
    ticket_counters["وسيط"] += 1

    channel_name = f"تكت-وسيط-{num:03d}"
    
    second_member = None
    target_username = self.other_user.value.strip().replace("@", "")
    for m in guild.members:
      if m.name.lower() == target_username.lower() or str(m.id) == target_username:
        second_member = m
        break

    fields = [
        ("وش بتاخذ", self.get_item.value),
        ("وش بتعطي", self.give_item.value),
        ("يوزر الطرف الثاني", self.other_user.value + (f" ({second_member.mention})" if second_member else " (لم يتم العثور عليه تلقائياً كعضو)")),
        ("التيب / الهدية", self.tip.value or "لا يوجد"),
    ]

    await create_ticket_channel(
        interaction,
        channel_name,
        "وسيط مضمون",
        ROLE_IDS["وسيط"],
        discord.Color.gold(),
        fields,
        second_member=second_member
    )


# ب) استمارة تطوير المابات
class DevelopmentModal(Modal, title="تفاصيل تطوير المابات"):

  def __init__(self):
    super().__init__()

  dev_target = TextInput(
      label="اكتب وش تبي اطور",
      style=TextStyle.paragraph,
      placeholder="اكتب اي شخصيه تبي تطور...",
      required=True,
  )
  dev_price = TextInput(
      label="بكم تبي تطور",
      style=TextStyle.short,
      placeholder="اكتب بكم تبي تطور...",
      required=True,
  )
  mokaabel = TextInput(
      label="اكتب المقابل هنا",
      style=TextStyle.paragraph,
      placeholder="...المقابل",
      required=True,
  )
  account_name = TextInput(
      label="اكتب اسم حسابك هنا",
      style=TextStyle.short,
      placeholder="اكتب اسم حسابك...",
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    global ticket_counters
    guild = interaction.guild
    num = ticket_counters["تطوير"]
    ticket_counters["تطوير"] += 1

    channel_name = f"تكت-تطوير-{num:03d}"

    await create_ticket_channel(
        interaction,
        channel_name,
        "تطوير المابات",
        ROLE_IDS["تطوير"],
        discord.Color.blue(),
        [
            ("المراد التطوير", self.dev_target.value),
            ("سعر التطوير", self.dev_price.value),
            ("المقابل", self.mokaabel.value),
            ("اسم الحساب", self.account_name.value),
        ],
    )


# جـ) استمارة تكت الهلاوين
class HalloweenModal(Modal, title="أسئلة تكت الهلاوين"):

  def __init__(self):
    super().__init__()

  daman = TextInput(
      label="وش ضمانك؟",
      style=TextStyle.paragraph,
      placeholder="اكتب ضمانك هنا...",
      required=True,
  )
  mokaabel = TextInput(
      label="وش مقابلك؟",
      style=TextStyle.paragraph,
      placeholder="اكتب مقابلتك هنا...",
      required=True,
  )
  ingame_name = TextInput(
      label="اسمك باللعبة",
      style=TextStyle.short,
      placeholder="اكتب اسمك باللعبة...",
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    global ticket_counters
    guild = interaction.guild
    num = ticket_counters["هلاوين"]
    ticket_counters["هلاوين"] += 1

    channel_name = f"تكت-هلاوين-{num:03d}"

    await create_ticket_channel(
        interaction,
        channel_name,
        "تكت الهلاوين",
        ROLE_IDS["هلاوين"],
        discord.Color.orange(),
        [
            ("الضمان", self.daman.value),
            ("المقابل", self.mokaabel
