import streamlit as st
st.title("AI Tutor")
prompt = st.chat_input(
    "Ask a question"
)
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        st.write(
            "This is a sample answer"
        )
