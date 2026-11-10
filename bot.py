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
            ("المقابل", self.mokaabel.value),
            ("اسم اللاعب", self.ingame_name.value),
        ],
    )


# د) استمارة الدعم الفني
class SupportModal(Modal, title="الدعم الفني"):

  def __init__(self):
    super().__init__()

  issue = TextInput(
      label="ما هي مشكلتك؟",
      style=TextStyle.paragraph,
      placeholder="اشرح مشكلتك بالتفصيل...",
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    global ticket_counters
    guild = interaction.guild
    num = ticket_counters["دعم"]
    ticket_counters["دعم"] += 1

    channel_name = f"تكت-دعم-{num:03d}"

    await create_ticket_channel(
        interaction,
        channel_name,
        "الدعم الفني",
        ROLE_IDS["دعم"],
        discord.Color.red(),
        [("وصف المشكلة", self.issue.value)],
    )


# ---------------------------------------------------------
# 6. دالة موحدة لإنشاء التكت مع العدادات والمنشن التلقائي
# ---------------------------------------------------------
async def create_ticket_channel(
    interaction: discord.Interaction,
    channel_name,
    service_type,
    role_id,
    embed_color,
    fields_list,
    second_member=None,
):
  guild = interaction.guild
  user = interaction.user

  role = guild.get_role(role_id)

  overwrites = {
      guild.default_role: discord.PermissionOverwrite(read_messages=False),
      user: discord.PermissionOverwrite(
          read_messages=True,
          send_messages=True,
          attach_files=True,
          embed_links=True,
      ),
      guild.me: discord.PermissionOverwrite(
          read_messages=True,
          send_messages=True,
          attach_files=True,
          embed_links=True,
      ),
  }

  if role:
    overwrites[role] = discord.PermissionOverwrite(
        read_messages=True,
        send_messages=True,
        attach_files=True,
        embed_links=True,
    )

  if second_member:
    overwrites[second_member] = discord.PermissionOverwrite(
        read_messages=True,
        send_messages=True,
        attach_files=True,
        embed_links=True,
    )

  ticket_channel = await guild.create_text_channel(
      name=channel_name, overwrites=overwrites
  )

  embed = discord.Embed(
      title=f"تفاصيل تذكرة: {service_type}", color=embed_color
  )
  embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
  embed.add_field(name="صاحب الطلب", value=user.mention, inline=False)

  for name, value in fields_list:
    embed.add_field(name=name, value=value, inline=False)

  mention_text = f"مرحباً {user.mention}"
  if second_member:
    mention_text += f" {second_member.mention}"
  if role:
    mention_text += f" | {role.mention}"

  await ticket_channel.send(
      content=mention_text, embed=embed, view=TicketControlView()
  )
  await interaction.response.send_message(
      f"✅ تم فتح التذكتك بنجاح في {ticket_channel.mention}", ephemeral=True
  )


# ---------------------------------------------------------
# 7. قائمة اختيار الخدمات الرئيسية
# ---------------------------------------------------------
class TicketTypeSelect(Select):

  def __init__(self):
    options = [
        discord.SelectOption(
            label="وسيط مضمون",
            value="وسيط",
            description="لفتح تكت وساطة وتداول بين طرفين",
            emoji="⚖️",
        ),
        discord.SelectOption(
            label="تطوير المابات",
            value="تطوير",
            description="لطلب خدمة تطوير مابات",
            emoji="📊",
        ),
        discord.SelectOption(
            label="تكت الهلاوين",
            value="هلاوين",
            description="لطلب خدمات وفعاليات الهلاوين",
            emoji="🎃",
        ),
        discord.SelectOption(
            label="التواصل مع الدعم الفني",
            value="دعم",
            description="لأي مشكلة أو استفسار",
            emoji="🎧",
        ),
    ]
    super().__init__(placeholder="اختر نوع التذكرة...", options=options)

  async def callback(self, interaction: discord.Interaction):
    val = self.values[0]
    if val == "وسيط":
      await interaction.response.send_modal(MiddlemanModal())
    elif val == "تطوير":
      await interaction.response.send_modal(DevelopmentModal())
    elif val == "هلاوين":
      await interaction.response.send_modal(HalloweenModal())
    elif val == "دعم":
      await interaction.response.send_modal(SupportModal())


class MainTicketView(View):

  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(TicketTypeSelect())


# ---------------------------------------------------------
# 8. أوامر السلاش (Slash Commands)
# ---------------------------------------------------------
@bot.tree.command(
    name="ticket", description="إنشاء بنل التكتات مع إمكانية إرفاق صورة"
)
@discord.app_commands.describe(
    image_url="ضع رابط الصورة المراد إضافتها في البنل (اختياري)"
)
async def slash_ticket_setup(
    interaction: discord.Interaction, image_url: str = None
):
  if not interaction.user.guild_permissions.administrator:
    await interaction.response.send_message(
        "❌ هذا الأمر مخصص للإدارة فقط!", ephemeral=True
    )
    return

  embed = discord.Embed(
      title=PANEL_CONFIG["title"],
      description=PANEL_CONFIG["description"],
      color=PANEL_CONFIG["color"],
  )

  if image_url:
    embed.set_image(url=image_url)

  await interaction.channel.send(embed=embed, view=MainTicketView())
  await interaction.response.send_message(
      "✅ تم إنشاء بنل التكتات بنجاح!", ephemeral=True
  )


@bot.tree.command(name="add", description="إضافة عضو إلى التكت الحالي")
@discord.app_commands.describe(member="العضو المراد إضافته")
async def slash_add(interaction: discord.Interaction, member: discord.Member):
  await interaction.channel.set_permissions(
      member,
      read_messages=True,
      send_messages=True,
      attach_files=True,
      embed_links=True,
  )
  await interaction.response.send_message(
      f"✅ تم إضافة {member.mention} إلى التكت وبإمكانه إرسال الصور والرسائل."
  )


@bot.tree.command(name="remove", description="إزالة عضو من التكت الحالي")
@discord.app_commands.describe(member="العضو المراد إزالته")
async def slash_remove(
    interaction: discord.Interaction, member: discord.Member
):
  await interaction.channel.set_permissions(member, overwrite=None)
  await interaction.response.send_message(
      f"🚫 تم إزالة {member.mention} من التكت."
  )


@bot.tree.command(name="rename", description="إعادة تسمية التكت الحالي")
@discord.app_commands.describe(new_name="اسم التكت الجديد")
async def slash_rename(interaction: discord.Interaction, new_name: str):
  await interaction.channel.edit(name=new_name)
  await interaction.response.send_message(
      f"✏️ تم تغيير اسم التكت إلى: `{new_name}`"
  )


@bot.tree.command(name="close", description="إغلاق وحذف التكت الحالي")
async def slash_close(interaction: discord.Interaction):
  if not interaction.user.guild_permissions.manage_channels:
    await interaction.response.send_message(
        "❌ عذراً، الإدارة فقط هي من تستطيع إغلاق التكت!", ephemeral=True
    )
    return
  await interaction.response.send_message(
      "🛑 سيتم حذف التكت خلال 3 ثوانٍ..."
  )
  await asyncio.sleep(3)
  await interaction.channel.delete()


@bot.tree.command(name="lock", description="قفل الروم الحالي")
async def slash_lock(interaction: discord.Interaction):
  if not interaction.user.guild_permissions.manage_channels:
    return
  await interaction.channel.set_permissions(
      interaction.guild.default_role, send_messages=False
  )
  await interaction.response.send_message("🔒 تم قفل الروم بنجاح.")


@bot.tree.command(name="unlock", description="فتح الروم الحالي")
async def slash_unlock(interaction: discord.Interaction):
  if not interaction.user.guild_permissions.manage_channels:
    return
  await interaction.channel.set_permissions(
      interaction.guild.default_role, send_messages=True
  )
  await interaction.response.send_message("🔓 تم فتح الروم بنجاح.")


@bot.tree.command(name="warn", description="تحذير عضو في السيرفر")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def slash_warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "غير محدد",
):
  if not interaction.user.guild_permissions.manage_messages:
    await interaction.response.send_message(
        "❌ لا تمتلك الصلاحية لاستخدام هذا الأمر.", ephemeral=True
    )
    return
  await interaction.response.send_message(
      f"⚠️ تم تحذير {member.mention} بسبب: {reason}"
  )


@bot.tree.command(name="prison", description="سجن عضو في السيرفر")
@discord.app_commands.describe(member="العضو المراد سجنه")
async def slash_prison(interaction: discord.Interaction, member: discord.Member):
  if not interaction.user.guild_permissions.manage_roles:
    await interaction.response.send_message(
        "❌ لا تمتلك صلاحية إدارة الرتب.", ephemeral=True
    )
    return
  prison_role = discord.utils.get(interaction.guild.roles, name="Prison")
  if not prison_role:
    prison_role = await interaction.guild.create_role(
        name="Prison", color=discord.Color.dark_gray()
    )
    for channel in interaction.guild.channels:
      await channel.set_permissions(prison_role, send_messages=False)
  await member.add_roles(prison_role)
  await interaction.response.send_message(f"🔒 تم سجن {member.mention} بنجاح!")


# ---------------------------------------------------------
# 9. تشغيل البوت
# ---------------------------------------------------------
@bot.event
async def on_ready():
  try:
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} slash commands successfully.")
  except Exception as e:
    print(e)
  print(f"Logged in as {bot.user.name} - Ready & Online!")


keep_alive()
TOKEN = os.environ.get("TOKEN")
bot.run(TOKEN)
