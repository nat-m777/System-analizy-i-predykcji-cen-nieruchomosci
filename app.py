import streamlit as st
import time

from src.auth import (
    check_auth,
    init_auth_db,
    login_session,
    login_user,
    logout_session,
    register_user
)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="System Analizy",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# INIT
# =========================================================

init_auth_db()

# =========================================================
# AUTH
# =========================================================

logged = check_auth()

# =========================================================
# LOGIN SCREEN
# =========================================================

if not logged:

    st.title(
        "🔐 System Analizy Nieruchomości"
    )

    tab1, tab2 = st.tabs([
        "Logowanie",
        "Rejestracja"
    ])

    # LOGIN
    with tab1:

        username = st.text_input(
            "Login"
        )

        password = st.text_input(
            "Hasło",
            type="password"
        )

        if st.button(
            "Zaloguj",
            use_container_width=True
        ):

            if login_user(
                username,
                password
            ):

                login_session(username)

                st.success(
                    "Zalogowano!"
                )

                time.sleep(1)

                st.rerun()

            else:

                st.error(
                    "Błędny login lub hasło"
                )

    # REGISTER
    with tab2:

        new_user = st.text_input(
            "Nowy login"
        )

        new_pass = st.text_input(
            "Nowe hasło",
            type="password"
        )

        if st.button(
            "Utwórz konto",
            use_container_width=True
        ):

            if register_user(
                new_user,
                new_pass
            ):

                st.success(
                    "Konto utworzone"
                )

            else:

                st.error(
                    "Użytkownik istnieje"
                )

    st.stop()

# =========================================================
# APP
# =========================================================

st.sidebar.success(
    f"Zalogowano jako: "
    f"{st.session_state.username}"
)

if st.sidebar.button("Wyloguj"):

    logout_session()

    st.rerun()

st.title(
    f"Witaj "
    f"{st.session_state.username} 👋"
)
