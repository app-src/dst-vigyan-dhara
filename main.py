import streamlit as st
import pandas as pd
import base64
import json
import time
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
import extra_streamlit_components as stx
from auth import load_users, verify_user
from fastapi import Response


COOKIE_NAME = "vigyan_login"
COOKIE_EXPIRY_DAYS = 1

color_map = {
    "Budget": "#FFF3E3",       # Pink
    "Expenditure": "#BFECAC",   # Light green
    "IFD": "#ADD8E6"          # Light blue

}

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLV_lAFz5evZVNPLdECqsOjD10jQN4ATlna5UdmUOz24mWTrkjbevk1qvn4u2GZAhssoc9B5Qp_TlC/pub?gid=0&single=true&output=csv"

# Load users
users = load_users()

# Cookie manager
cookie_manager = stx.CookieManager()


def is_logged_in():
    cookies = cookie_manager.get_all()
    return COOKIE_NAME in cookies or 'username' in st.session_state

def set_login_cookie(user):
    # expire_date = datetime.now(timezone.utc) + timedelta(days=COOKIE_EXPIRY_DAYS)
    expire_date = datetime.now(timezone.utc) + timedelta(seconds=30)
    cookie_manager.set(COOKIE_NAME, user, expires_at=expire_date)
    st.session_state['username'] = user

def clear_login_cookie():
    st.session_state.clear()
    try:
        cookie_manager.delete(COOKIE_NAME)
    except Exception as e:
        st.error(f"Error clearing cookie: {e}")

    time.sleep(1)
    st.stop()
    st.rerun()

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
def hide_zeros_and_nans(val):
    if pd.isna(val) or val == 0:
        return ""
    return val

def colorCodeRows(row):
    last_col_value = row[row.index[-1]]
    if last_col_value in color_map:
        return ['background-color: ' + color_map[last_col_value]] * len(row)
    else:
        return ['background-color: white'] * len(row)
# --- Load data ---
@st.cache_data
def load_data():
    df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
    return df

def main():
    if not is_logged_in():
        st.title("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if verify_user(username, password, users):
                set_login_cookie(username)
                st.success("Login successful! Refreshing...")
            else:
                st.error("Invalid credentials")

        st.stop()

    st.set_page_config(page_title="Vigyan Dhara - Expenditure data",page_icon='📊', layout="wide")


    logo_left = get_base64_image("dsu.png")
    logo_right = get_base64_image("dst.png")



    st.markdown("""
        <style>
            header {visibility: hidden;}
            .block-container {
                padding-top: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
                    <style>
                        .custom-header {
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            background-color: #f0f0f0;
                            padding: 10px 30px;
                            z-index: 9999;
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            border-bottom: 1px solid #ccc;
                        }
                        .custom-header h2 {
                            margin: 0;
                            color: #333;
                        }
                        .custom-header img {
                            height: 100%;
                        }
                        .block-container {
                            padding-top: 80px; /* Push page content below fixed header */
                        }
                    </style>"""+f"""

                    <div class="custom-header">
                        <img src="data:image/png;base64, {logo_left}" />
                        <h2>Vigyan Dhara Expenditure Data</h2>
                        <img s src="data:image/png;base64, {logo_right}" />
                    </div>
                """, unsafe_allow_html=True)





    custom_footer = """
    <style>
    #MainMenu {visibility: hidden;}
    .custom-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #F0F0F0;
        text-align: center;
        align-items: left
        padding: 20px;
        font-size: 14px;
        z-index: 99999;
    }

    .footer-banner {
        display: flex;
        justify-content: center;
        color: white;
        gap: 20px;
        padding: 10px;
        flex-wrap: wrap;
    }
    .vertical-line {
        width: 1px;
        height: 30px;
        background-color: grey;
        align-self: center;
    }

    .footer-banner div {
        text-align: center;
    }
    </style>

    <div class="custom-footer">
        <div  class="footer-banner">
            <div>
                <div style="text-align: right; color: blue; font-weight: bold;">भारत सरकार</div>
                <div style="text-align: right; color: blue; font-weight: bold;">GOVERNMENT OF INDIA</div>
            </div>
            <div class="vertical-line"></div>
            <div>
                <div style="text-align: left; font-weight: bold; color: grey;">विज्ञान और प्रौद्योगिकी मंत्रालय</div>
                <div style="text-align: left; font-weight: bold; color: grey;">MINISTRY OF SCIENCE AND TECHNOLOGY</div>
            </div>
        </div>
    </div>
    """

    st.markdown(custom_footer, unsafe_allow_html=True)

    try:
        df = load_data()
        if df.empty or df.shape[1] < 2:
            st.error("Sheet is empty or has less than two columns.")
        else:
            # --- Get unique values from 2nd column ---
            second_col = df.columns[-1]
            unique_vals = sorted(df[second_col].dropna().unique())
            # --- Show checkboxes ---
            # st.subheader(f"Filter by `{second_col}`")
            st.subheader(f"Filter by :")
            selected_filters = []
            cols = st.columns(len(unique_vals))
            for i, val in enumerate(unique_vals):
                with cols[i]:
                    # Create checkbox with no label
                    cb = st.checkbox(" ", key=f"cb_{val}", value=True)

                    # Add a custom styled label next to the checkbox
                    label_html = f"""
                    <label style='
                        display: inline-block;
                        background-color: {color_map.get(val, "#eee")};
                        padding: 4px 10px;
                        border-radius: 5px;
                        font-weight: bold;
                        margin-top: -28px;
                        margin-left: 30px;
                        position: relative;
                        top: -12px;
                    '>{val}</label>
                    """
                    st.markdown(label_html, unsafe_allow_html=True)

                    if cb:
                        selected_filters.append(val)

            # --- Filter data ---
            if selected_filters:
                filtered_df = df[df[second_col].isin(selected_filters)]
                # Apply row coloring and zero null filter
                styled_df = filtered_df.style.format(hide_zeros_and_nans).apply(colorCodeRows, axis=1)
                st.markdown(
                            f"""
                            <div style='max-height:{len(df) * 35 + 50}px; overflow-y:auto;'>
                                <style>table {{margin: 0 auto;}}</style>
                                {styled_df.to_html()}
                            </div>
                            """,
                            unsafe_allow_html=True
                            )
            else:
                st.warning("Select at least one option to view data.")

    except Exception as e:
        st.error(f"Failed to load or parse the CSV: {e}")


    if st.button("Logout"):
        clear_login_cookie()


if __name__ == "__main__":
    main()