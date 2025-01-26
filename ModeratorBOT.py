import discord
import mariadb
from discord.ext import commands
from discord import app_commands
import os, datetime, asyncio, json, random, aioshutil, json, uuid
from discord_webhook import DiscordWebhook


def db_connect(autocommit=True):
    try:
        conn = mariadb.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            autocommit=autocommit,
            connect_timeout=5
        )

        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")


def db_request_get(request, fetchtype):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(request)
    if fetchtype == "one":
        data = cursor.fetchone()
    else:
        data = cursor.fetchall()
    conn.close()
    return data


def db_request_post(request):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(request)
    conn.close()
    return



def read_config():
    with open('config.json', encoding="utf-8") as config:
        return json.load(config)

def read_cache():
    with open('cache.json') as cache_f:
        return json.load(cache_f)

def safe_cache():
    with open('cache.json', "w") as cache_f:
        cache_f.write(str(cache).replace("\'", "\""))

config = read_config()

cache = read_cache()

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False
intents.guild_messages = True
bot = commands.Bot(command_prefix=config["main"]["prefix"], intents=intents)


def check_if_mod(interaction: discord.Interaction):
    for x in interaction.user.roles:
        if x.id in config["mod"]["ids_moder_role"]:
            return True
    return interaction.user.guild_permissions.manage_guild

def check_if_mod_usually(ctx):
    for x in ctx.message.author.roles:
        if x.id in config["mod"]["ids_moder_role"]:
            return True
    return ctx.message.author.guild_permissions.manage_guild

def check_if_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.manage_guild


def not_me(msg):
    if msg.author.id == bot.user.id:
        return False
    else: return True


@bot.event
async def on_ready():
    # await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=f'by kotikvorkotik', type=discord.ActivityType.playing))
    print("Bot logged as", bot.user.name)
    await bot.tree.sync()
@bot.event
async def on_error(error):
    print(error)

@bot.event
async def on_reaction_add(reaction, user):
    channel = bot.get_channel(config["mod"]["reaction_log_channel"])
    await channel.send(f"`{user.name} поставил реакцию` {reaction} `в канале` <#{reaction.message.channel.id}>")


@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        pass
    elif message.content.startswith("*newticket"):
        if str(message.channel.type) == "private":
            author_command = message.author.id
            dm_id = message.channel.id
            for ticket in cache["tickets"]["open"]:
                if ticket["dm_id"] == dm_id:
                    await message.channel.send("Тикет уже создан!")
                    return
            def check_ticket(m):
                return m.author.id == author_command and m.channel.id == dm_id
            await message.channel.send("Здравствуйте! Здесь Вы можете подать жалобу или апелляцию. Пишите Ваше обращение чётко и подробно!\n\n*У Вас есть 5 минут, иначе этот тикет закроется, так и не открывшись!*")
            try: msg = await bot.wait_for("message", check=check_ticket, timeout=300)
            except: await message.channel.send("Время истекло!")
            else:
                await message.channel.send("Диалог начат! Вам скоро ответят.\n*Вы всегда можете добавить какую-либо информацию написав ещё сообщения*")
                with open(f'{config["mod"]["tickets_logs_path"]}/{cache["tickets"]["next_id"]}.html', "w",encoding="UTF-8") as log_file:
                    log_file.write('<meta charset="UTF-8">')
                await new_ticket(msg)

        else: await message.delete()

    elif str(message.channel.type) == "private":
        for i in range(len(cache["tickets"]["open"])):
            if cache["tickets"]["open"][i]["dm_id"] == message.channel.id:
                t_ch = bot.get_channel(cache["tickets"]["open"][i]["ticket_channel"])
                msg = message.content
                imgs = []
                imgs_chat = []
                for foto in message.attachments:
                    img = await save_tickets_img(foto)
                    imgs.append(img)
                    imgs_chat.append(await foto.to_file())
                if not imgs:
                    imgs = None
                await t_ch.send(f"**{message.author.name} >>** " + msg, files=imgs_chat)
                await ticket_log(cache["tickets"]["open"][i]["id"], f"{message.author.name} отправляет сообщение цысу: {msg}", imgs)
                break

    elif message.channel.category.id == config["mod"]["tickets_category"]:
        if message.content.startswith("*r"):
            pass
        else:
            for i in range(len(cache["tickets"]["open"])):
                if cache["tickets"]["open"][i]["ticket_channel"] == message.channel.id:
                    msg = message.content
                    imgs = []
                    for foto in message.attachments:
                        img = await save_tickets_img(foto)
                        imgs.append(img)
                    if not imgs:
                        imgs = None
                    await ticket_log(cache["tickets"]["open"][i]["id"], f"{message.author.name} >> {msg}", imgs)
                    break

    await bot.process_commands(message)

async def ticket_log(id, text, imgs = None):
    with open(f'{config["mod"]["tickets_logs_path"]}/{id}.html', "a", encoding="UTF-8") as log_file:
        time = datetime.datetime.now()
        log_file.write(f"<a>({time:%d.%m.%y %H:%M:%S}) {text}</a><br>\n")
        if imgs:
            for img in imgs:
                log_file.write(f'<img src={img} height="-50%">')
            log_file.write("<br>")

async def save_tickets_img(img):
    path = f"images/{uuid.uuid4()}.png"
    await img.save(f'{config["mod"]["tickets_logs_path"]}/{path}')
    return path

async def new_ticket(msg):
    await ticket_log(cache["tickets"]["next_id"], f"{msg.author.name} ({msg.author.id}) начинает новый тикет!")
    teamcis_guild = await bot.fetch_guild(config["main"]["guild_id"])
    ticket_channel = await teamcis_guild.create_text_channel(f'{msg.author.name}', category=await bot.fetch_channel(config["mod"]["tickets_category"]))
    ticket_js = {
        "id": cache["tickets"]["next_id"],
        "user_id": msg.author.id,
        "dm_id": msg.channel.id,
        "ticket_channel": ticket_channel.id
    }
    cache["tickets"]["open"].append(ticket_js)
    cache["tickets"]["next_id"] += 1
    safe_cache()
    await ticket_channel.send(f'<@&1218259053830996029> Новое обращение от <@{msg.author.id}>!\nАйди пользователя: {msg.author.id}. Айди тикета **{cache["tickets"]["next_id"]-1}**')

    msg_by_user = f"**{msg.author.name} >>** " + msg.content
    imgs = []
    imgs_chat = []
    for foto in msg.attachments:
        img = await save_tickets_img(foto)
        imgs.append(img)
        imgs_chat.append(await foto.to_file())
    if not imgs:
        imgs = None
    await ticket_channel.send(msg_by_user, files=imgs_chat)
    await ticket_log(cache["tickets"]["next_id"]-1, f"{msg.author.name} отправляет сообщение цысу: {msg.content}", imgs)

@bot.command(name='r')
@commands.check(check_if_mod_usually)
async def r(ctx,*,text = " "):
    for i in range(len(cache["tickets"]["open"])):
        if cache["tickets"]["open"][i]["ticket_channel"] == ctx.channel.id:
            user = await bot.fetch_user(cache["tickets"]["open"][i]["user_id"])
            msg = text
            imgs = []
            imgs_chat = []
            imgs_chat_ticket = []
            for foto in ctx.message.attachments:
                img = await save_tickets_img(foto)
                imgs.append(img)
                imgs_chat.append(await foto.to_file())
                imgs_chat_ticket.append(await foto.to_file())
            await user.send("**TeamCIS >>** " + msg, files=imgs_chat)
            await ticket_log(cache["tickets"]["open"][i]["id"], f"{ctx.message.author.name} отправляет сообщение пользователю: {msg}", imgs)
            await ctx.channel.send(f"**TeamCIS ({ctx.message.author.name}) >>** " + msg, files=imgs_chat_ticket)
            await ctx.message.delete()
            break


@bot.tree.command()
@app_commands.check(check_if_admin)
async def close_ticket(interaction: discord.Interaction):
    await interaction.response.send_message("Закрываю...")
    for i in range(len(cache["tickets"]["open"])):
        if cache["tickets"]["open"][i]["ticket_channel"] == interaction.channel.id:
            channel = bot.get_channel(interaction.channel.id)
            await channel.delete()
            user = await bot.fetch_user(cache["tickets"]["open"][i]["user_id"])
            await user.send("Тикет был закрыт!\nЕсли у вас возникнут ещё вопросы, то Вы всегда можете создать новый командой `*newticket`")

            channel = bot.get_channel(config["mod"]["mod_log_channel"])
            await channel.send(f'{interaction.user.name} закрыл тикет (id = {cache["tickets"]["open"][i]["id"]})\nАрхив: https://buildtheearth.ru/mod/tickets/{cache["tickets"]["open"][i]["id"]}.html')
            await ticket_log(cache["tickets"]["open"][i]["id"], f"{interaction.user.name} закрыл тикет!")
            cache["tickets"]["open"].remove(cache["tickets"]["open"][i])
            safe_cache()

            break



@bot.tree.command()
@app_commands.check(check_if_mod)
@app_commands.describe(amount="N сообщений")
async def clear(interaction: discord.Interaction, amount: int):
    '''Удалить последние N сообщений в канале'''
    await interaction.response.send_message("Удаляю...", ephemeral=True)
    try:
        channel = bot.get_channel(config["mod"]["mod_log_channel"])
        deleted = await interaction.channel.purge(limit=amount)
        with open(f'{config["mod"]["purge_logs_path"]}/log_{datetime.date.today()}.html', "a+", encoding="utf-8") as log_file:
            deleted.reverse()
            log_file.write('<meta charset="UTF-8">\n<p>')
            for msg in deleted:
                log_file.write(f"""({(msg.created_at + datetime.timedelta(hours=3)).time():%H:%M:%S}) Канал <b>{msg.channel.name}</b> от <b>{msg.author.name}</b> >> {msg.content}<br>""")
            log_file.write("</p>")
            log_file.write("<br><br>")

        await interaction.edit_original_response(content=f"Удалено **{len(deleted)} сообщений**\nМожно посмотреть [**здесь**](https://buildtheearth.ru/mod/purged/log_{datetime.date.today()}.html)")
        await channel.send(f"Удалено **{len(deleted)} сообщений** пользователем {interaction.user.name} в канале <#{interaction.channel.id}>\nЛоги можете посмотреть [**здесь**](https://buildtheearth.ru/mod/purged/log_{datetime.date.today()}.html)")
    except Exception as error:
        print("Ошибка")
        print(error)
        await interaction.edit_original_response(content=f"Ошибка: {error}")





@bot.tree.command()
@app_commands.check(check_if_mod)
async def ping(interaction: discord.Interaction):
    '''Ping bot'''
    await interaction.response.send_message("Фыромяу", ephemeral=False)

@ping.error
async def ping_error(interaction: discord.Interaction, error):
    print(error)
    await interaction.response.send_message("У вас. Нет. Прав.", ephemeral=True)












while True:
    try:
        bot.run(config["main"]["bot_token"])
        print(bot)
    except Exception as error:
        with open(f'error.txt', "w", encoding='utf-8') as file:
            file.write(f'{error}')
        file.close()
        webhook = DiscordWebhook(url="https://discord.com/api/webhooks/1205940394026602528/Ih6Pjrif04uIcbTLDb1CSqMDIkkNA1oBFCvzkYuePfwISF4D7tqKvNP1Lvtc0BOlk1li", content=f"<@674990047405015040>\nAllChecker сдох\nПричина:\n{error}")
        response = webhook.execute()