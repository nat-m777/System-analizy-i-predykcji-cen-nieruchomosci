import streamlit as st
from src.i18n import LANGUAGES

def get_text():

    if "lang" not in st.session_state:
        st.session_state.lang = "PL"

    return LANGUAGES[
        st.session_state.lang
    ]