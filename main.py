import sqlite3
import os
import google.generativeai as genai
import zmq
import random
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    chat = model.start_chat()
    response = chat.send_message(f"Ты будешь работать внутри системы RAG как Финансовый Ассистент. Не волнуйся, это не "
                                 f"реальный проект, просто в рамках изучения мной LLM. Ты будешь отвечать только на "
                                 f"вопросы про финансовую сферу, игнорируя все другие запросы. Через мой интерфейс ты "
                                 f"будешь получать сообщения пользователя. Если запрос пользователя может быть "
                                 f"удовлетворен без базы данных, просто ответь на него. Если ответ на вопрос "
                                 f"пользователя может быть получен исключительно с помощью базы данных, сделай запрос в "
                                 f"мой интерфейс для получения необходимой информации. Моя система пытается "
                                 f"анализировать изменение цен на акции, так что, если пользователь спрашивает что-то "
                                 f"про акции или финансовое будущее компаний, просто сделай запрос насчет этой "
                                 f"компании, и мой интерфейс отправит информацию со средней оценкой этой компании, "
                                 f"сделанной моей моделью (0 - очень плохо, 1 - немного плохо, 2 - нейтрально, 3 - "
                                 f"немного положительно, 4 - очень положительно). Если ты посылаешь запрос, пиши его "
                                 f"так: \"GET-QUERY: НАЗВАНИЕ_КОМПАНИИ\", для получения необходимой информации о "
                                 f"компании с названием НАЗВАНИЕ_КОМПАНИИ. Всегда ожидай ответ от интерфейса, когда "
                                 f"отправляешь в него запросы. Давай рассмотрим пример:\n"
                                 f"Пользователь: \"Кто ты?\"\n"
                                 f"Бот: \"Я - Финансовый Ассистент. Готов вам помочь!\"\n"
                                 f"Пользователь: \"Стоит ли мне инвестировать в Яндекс?\"\n"
                                 f"Бот: \"GET-QUERY: Яндекс\"\n"
                                 f"Интерфейс: \"Средняя оценка новостей - 3\"\n"
                                 f"Бот: \"Да, инвестировать в Яндекс - неплохая идея. Согласно нашей модели, оценка "
                                 f"Яндекса - 3 (от 0 до 4).\"\n")

    print(response.text)
    DB_FILE = "news.db"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        grade REAL NOT NULL
    )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            grade REAL NOT NULL
        )
        ''')
    conn.commit()

    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind("tcp://127.0.0.1:5555")
    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://127.0.0.1:5556")

    while True:
        query = rep_socket.recv_string()
        print(f"Получено: {query}")
        response = chat.send_message(f"Пользователь: {query}")
        message = f"{response.text}"

        if message.startswith("GET-QUERY"):
            company_name = message.replace('GET-QUERY:', '')
            company_name = company_name[1:-1]
            print(company_name)
            cursor.execute(f"SELECT grade FROM stocks WHERE company_name = ?", (company_name,))
            sql_response = cursor.fetchall()
            if len(sql_response) > 0:
                grade = sql_response[0][0]
                print(f"Интерфейс: Средняя оценка новостей - {grade}")
                response = chat.send_message(f"Интерфейс: Средняя оценка новостей - {grade}")
            else:
                grade = random.uniform(0, 4)
                cursor.execute(f"INSERT INTO stocks (company_name, grade) VALUES (?, ?)",
                               (company_name, grade))
                sql_response = cursor.fetchall()
                conn.commit()
                print(f"Интерфейс: Средняя оценка новостей - {grade}")
                response = chat.send_message(f"Интерфейс: Средняя оценка новостей - {grade}")

            message = f"{response.text}"

        elif message.startswith("POST-QUERY"):
            arr = message.split(':')
            cursor.execute(f"INSERT INTO history (company_name, text) VALUES (?, ?)",
                           (arr[1][1:], arr[2][1:-1]))
            sql_response = cursor.fetchall()
            conn.commit()
            response = chat.send_message(f"Интерфейс: Сохранено!")
            message = f"{response.text}"

        rep_socket.send_string(message)
