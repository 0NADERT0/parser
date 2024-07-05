import requests
import telebot
import random
import time
import json
import psycopg2
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent


API_KEY = '7224936403:AAEHjcgytSsJWwz4Wy9rlJloN5rJz6rEBbw'

conn = psycopg2.connect(database="postgres",
                        host="172.17.0.1",
                        user="postgres",
                        password="postgres",
                        port="5432")

cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS resume(id INT, name VARCHAR(255), salary INT, age INT, ref VARCHAR(255))")
conn.commit()

def get_links(text):
    ua = UserAgent()
    data = requests.get(url=f"https://hh.ru/search/resume?text={text}&area=1&isDefaultArea=true&ored_clusters=true&order_by=relevance&search_period=0&logic=normal&pos=full_text&exp_period=all_time&page=1",
                        headers={"user-agent": ua.random}
    )
    if data.status_code != 200:
        return
    soup = bs(data.content, "lxml")
    try:
        page_count = int(soup.find("div", attrs={"class":"pager"}).find_all("span", recursive=False)[-1].find("a").find("span").text)
    except:
        return
    for page in range(page_count):
        try:
            data = requests.get(url=f"https://hh.ru/search/resume?text={text}&area=1&isDefaultArea=true&ored_clusters=true&order_by=relevance&search_period=0&logic=normal&pos=full_text&exp_period=all_time&page={page}",
            headers={"user-agent": ua.random}
            )
            if data.status_code != 200:
                continue
            soup = bs(data.content, "lxml")
            for a in soup.find_all("a", attrs={"data-qa": "serp-item__title"}):
                yield f"https://hh.ru{a.attrs['href'].split('?')[0]}"
        except Exception as e:
            print(f"{e}")
        #time.sleep(1)

def get_resume(link):
    ua = UserAgent()
    data = requests.get(url=link,
                        headers={"user-agent": ua.random}
    )
    if data.status_code != 200:
        return
    soup = bs(data.content, "lxml")
    try:
        name = soup.find(attrs={"class": "resume-block__title-text"}).text
    except:
        name = ""
    try:
        salary = int(soup.find(attrs={"class": "resume-block__salary"}).text.replace("\u2009", "").replace("\xa0", "").replace("₽ наруки", "").replace("₽ in hand", ""))
    except:
        salary = None
    try:
        age = int(soup.find(attrs={"data-qa": "resume-personal-age"}).text.replace("\xa0лет", " ").replace("\xa0года", " "))
    except:
        age = None
    try:
        tags = [tag.text for tag in soup.find(attrs={"class":"bloko-tag-list"}).find_all("span",attrs={"class":"bloko-tag__section_text"})]
    except:
        tags = []
    resume = {
        "name": name,
        "salary": salary,
        "age": age,
        "tags": tags,
        "link": link
    }
    return resume

data = []

mx_cnt = 10

#for a in get_links("Python"):
    #data.append(get_resume(a))
    #print(get_resume(a))
    #time.sleep(1)
    #mx_cnt -= 1
    #if mx_cnt == 0:
    #    break
    #with open("data.json", "w", encoding="utf-8") as f:
        #json.dump(data, f, indent = 4, ensure_ascii=False)

bot = telebot.TeleBot(API_KEY)

job_name = ""
now = -1
is_looking = False
data = []
data_cnt = 0
mn_age_bound = -1
mx_age_bound = 101
sal_max = 2e9
sal_min = -1
cur.execute("DELETE FROM resume")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Напишите название профессии, чтобы найти резюме")

@bot.message_handler(commands=['restart', 'new'])
def new_search(message):
    global now
    global is_looking
    global data
    global mn_age_bound
    global mx_age_bound
    global job_name
    global sal_max
    global sal_min
    job_name = ""
    mn_age_bound = -1
    mx_age_bound = 101
    sal_max = 2e9
    sal_min = -1
    data = []
    is_looking = False
    now = -1
    cur.execute("DELETE FROM resume")
    bot.send_message(message.chat.id, "Напишите название профессии, чтобы найти резюме")

#добавлять резюме в базу данных и при запросе телеграмм бота нужно выводить
#добавить вывод всех резюме из базы данных
#добавить фильтры при выводе резюме
#делать запросы из бд

@bot.message_handler(func=lambda message: True)
def bot_logic(message):
    global job_name
    global mn_age_bound
    global mx_age_bound
    global sal_min
    global sal_max
    if job_name == "":
        bot.send_message(message.chat.id, "Введите нижнюю границу возраста кандидата: ")
        job_name = message.text
        return
    if mn_age_bound == -1:
        bot.send_message(message.chat.id, "Введите верхнюю границу возраста кандидата: ")
        mn_age_bound = int(message.text)
        return
    if mx_age_bound == 101:
        bot.send_message(message.chat.id, "Введите нижнюю границу зарплаты кандидата: ")
        mx_age_bound = int(message.text)
        return
    if sal_min == -1:
        bot.send_message(message.chat.id, "Введите верхнюю границу зарплаты кандидата: ")
        sal_min = int(message.text)
        return
    if sal_max == 2e9:
        sal_max = int(message.text)
    global now
    global is_looking
    global data
    global data_cnt
    now += 1
    response = ""
    if is_looking == False:
        bot.send_message(message.chat.id, "Бот ищет подходящие резюме...")
        
        mx_cnt = 10

        for a in get_links(job_name):
            temp = get_resume(a)
            data.append(temp)
            temp_data = {
                'id': data_cnt,
                'name': temp['name'],
                'salary': temp['salary'],
                'age': temp['age'],
                'ref': temp['link']
            }
            cur.execute("INSERT INTO resume (id, name, salary, age, ref) VALUES (%(id)s, %(name)s, %(salary)s, %(age)s, %(ref)s)", temp_data)
            conn.commit()
            print(get_resume(a))
            data_cnt += 1
            mx_cnt -= 1
            if mx_cnt == 0:
                break
        is_looking = True
        #print(mn_age_bound)
        #print(mx_age_bound)
        #cur.execute("SELECT * FROM resume")
        cur.execute("SELECT * FROM resume WHERE age > %s AND age < %s AND salary > %s AND salary < %s", (mn_age_bound, mx_age_bound, sal_min, sal_max))
        rows = cur.fetchall()
        response = "Data from the database:\n"
        was = 0
        for row in rows:
            response += "name: " + str(row[1]) + "\n"
            response += "salary: " + str(row[2]) + "\n"
            response += "age: " + str(row[3]) + "\n"
            response += "ref: " + str(row[4]) + "\n"
            was += 1
            if was == 1:
                was = 0
                bot.send_message(message.chat.id, response)
                response = ""
    
    if message.text == "all":
        cur.execute("SELECT * FROM resume")
        rows = cur.fetchall()
        print(rows)
        response = "Data from the database:\n"
        was = 0
        for row in rows:
            response += "name: " + str(row[1]) + "\n"
            response += "salary: " + str(row[2]) + "\n"
            response += "age: " + str(row[3]) + "\n"
            response += "ref: " + str(row[4]) + "\n"
            was += 1
            if was == 5:
                was = 0
                bot.send_message(message.chat.id, response)
                response = ""
    
bot.polling()