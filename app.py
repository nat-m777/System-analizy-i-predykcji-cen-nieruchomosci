import streamlit as st
import time

from src.auth import (
    login_user,
    register_user,
    init_auth_db,
    check_auth,
    login_session,
    logout_session
)

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="System Analizy",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------
# INIT
# ---------------------------------------------------

init_auth_db()

if 'lang' not in st.session_state:
    st.session_state.lang = "PL"

# ---------------------------------------------------
# LANG
# ---------------------------------------------------

st.sidebar.radio(
    "Language / Język",
    options=["PL", "EN"],
    key="lang_selector",
    on_change=lambda:
        st.session_state.update({
            "lang":
                st.session_state.lang_selector
        })
)

# ---------------------------------------------------
# AUTH
# ---------------------------------------------------

logged = check_auth()

# ---------------------------------------------------
# LOGIN SCREEN
# ---------------------------------------------------

if not logged:

    st.title("🔐 System Analizy Nieruchomości")

    tab_l, tab_r = st.tabs([
        "Logowanie",
        "Rejestracja"
    ])

    # LOGIN
    with tab_l:

        u = st.text_input(
            "Login",
            key="login_u"
        )

        p = st.text_input(
            "Hasło",
            type="password",
            key="login_p"
        )

        if st.button(
            "Zaloguj",
            use_container_width=True
        ):

            if login_user(u, p):

                login_session(u)

                st.success(
                    "Zalogowano pomyślnie!"
                )

                time.sleep(0.5)

                st.rerun()

            else:

                st.error(
                    "Błędny login lub hasło"
                )

    # REGISTER
    with tab_r:

        nu = st.text_input(
            "Nowy Login",
            key="reg_u"
        )

        np = st.text_input(
            "Nowe Hasło",
            type="password",
            key="reg_p"
        )

        if st.button(
            "Utwórz konto",
            use_container_width=True
        ):

            if register_user(nu, np):

                st.success(
                    "Konto utworzone!"
                )

            else:

                st.error(
                    "Użytkownik istnieje."
                )

    st.stop()

# ---------------------------------------------------
# APP
# ---------------------------------------------------

st.sidebar.success(
    f"Zalogowano jako: "
    f"{st.session_state['username']}"
)

if st.sidebar.button("Wyloguj"):
    logout_session()

st.title(
    f"Witaj "
    f"{st.session_state['username']} 👋"
)

st.info(
    "Sesja utrzymuje się po F5 i restarcie przeglądarki."
)