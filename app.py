import zmq
import sys
import streamlit as st
import subprocess
import google.generativeai as genai


def send_query():
    query = st.session_state.user_input
    st.session_state.history.append(f"Пользователь: {query}")
    req_socket.send_string(query)
    response = req_socket.recv_string()
    st.session_state.history.append(f"Бот: {response}")
    st.session_state.user_input = ""


if __name__ == '__main__':
    subprocess.Popen([sys.executable, "main.py"])
    context = zmq.Context()
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect("tcp://127.0.0.1:5555")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    req_socket = context.socket(zmq.REQ)
    req_socket.connect("tcp://127.0.0.1:5556")

    if "history" not in st.session_state:
        st.session_state.history = []

    st.title("Финансовый Ассистент")

    user_input = st.text_input("Напишите сообщение (ответ бота может прийти с задержкой):",
                               key="user_input", on_change=send_query)
    for message in reversed(st.session_state.history):
        st.write(message)
