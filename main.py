import streamlit as st
import pandas as pd
import base64
import json
import time
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
import extra_streamlit_components as stx
from auth import load_users, verify_user


COOKIE_NAME = "vigyan_login"
COOKIE_EXPIRY_DAYS = 1

color_map = {
    "Budget": "#FFF3E3",       # Pink
    "Expenditure": "#BFECAC",   # Light green
    "IFD": "#ADD8E6"          # Light blue

}

BUDGET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLV_lAFz5evZVNPLdECqsOjD10jQN4ATlna5UdmUOz24mWTrkjbevk1qvn4u2GZAhssoc9B5Qp_TlC/pub?gid=1893274223&single=true&output=csv"
EXPENDITURE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLV_lAFz5evZVNPLdECqsOjD10jQN4ATlna5UdmUOz24mWTrkjbevk1qvn4u2GZAhssoc9B5Qp_TlC/pub?gid=564550770&single=true&output=csv"
IFD_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLV_lAFz5evZVNPLdECqsOjD10jQN4ATlna5UdmUOz24mWTrkjbevk1qvn4u2GZAhssoc9B5Qp_TlC/pub?gid=1809513698&single=true&output=csv"
INFO_URL = "https://docs.google.com/spreadsheets/d/1pUnsZ-OgPGgKeJbfoHkJUlR4i3fXoKa_i-LwhIzHwbk/export?format=csv&id=1pUnsZ-OgPGgKeJbfoHkJUlR4i3fXoKa_i-LwhIzHwbk&gid=780038585"
# Load users
users = load_users()

# Cookie manager
cookie_manager = stx.CookieManager()

def load_sheet(url, type_name):
    df = pd.read_csv(url)
    df["Type"] = type_name
    return df

def load_all_data():
    budget_df = load_sheet(BUDGET_URL, "Budget")
    exp_df = load_sheet(EXPENDITURE_URL, "Expenditure")
    ifd_df = load_sheet(IFD_URL, "IFD")

    # Align columns (intersection across all)
    common_cols = set(budget_df.columns) & set(exp_df.columns) & set(ifd_df.columns)
    budget_df = budget_df[list(common_cols)]
    exp_df = exp_df[list(common_cols)]
    ifd_df = ifd_df[list(common_cols)]

    # Combine
    final_df = pd.concat([budget_df, exp_df, ifd_df], ignore_index=True)

    # --- Reorder columns ---
    cols = list(final_df.columns)
    div_col = "DIVISION"
    total_col = "Grand Total"
    type_col = "Type"
    middle_cols = [c for c in cols if c not in [div_col, total_col, type_col]]
    ordered_cols = [div_col] + middle_cols + [total_col, type_col]
    final_df = final_df[ordered_cols]

    # --- Normalize division names (strip spaces, case-insensitive match) ---
    final_df[div_col] = final_df[div_col].astype(str).str.strip()

    # --- Separate totals and normal divisions ---
    total_mask = final_df[div_col].str.lower().eq("total")
    totals_df = final_df[total_mask].copy()
    normal_df = final_df[~total_mask].copy()

    # --- Define row order by Type ---
    type_order = {"Budget": 0, "IFD": 1, "Expenditure": 2}

    # Sort normal divisions
    normal_df = normal_df.sort_values(
        by=[div_col, type_col],
        key=lambda col: col.map(type_order) if col.name == "Type" else col
    )

    # Sort totals separately (only by Type)
    totals_df = totals_df.sort_values(
        by=[type_col],
        key=lambda col: col.map(type_order)
    )

    # --- Combine back (normals first, totals at bottom) ---
    final_df = pd.concat([normal_df, totals_df], ignore_index=True)

    return final_df

def load_info():
    """Load info sheet and return (updated_by, last_updated_on)."""
    try:
        info_df = pd.read_csv(INFO_URL, header=None)
        updated_by = str(info_df.iloc[0, 1])  # B1
        last_updated = str(info_df.iloc[1, 1])  # B2
        return updated_by, last_updated
    except Exception as e:
        return "Unknown", "Unknown"
    
def is_logged_in():
    cookies = cookie_manager.get_all()
    return COOKIE_NAME in cookies or 'username' in st.session_state

def set_login_cookie(user):
    expire_date = datetime.now(timezone.utc) + timedelta(days=COOKIE_EXPIRY_DAYS)
    cookie_manager.set(COOKIE_NAME, user, expires_at=expire_date)
    st.session_state['username'] = user

def clear_login_cookie():
    st.session_state.clear()
    try:
        cookie_manager.delete(COOKIE_NAME)
    except Exception as e:
        st.error(f"Error clearing cookie: {e}")

    time.sleep(4)
    st.success("Logged out successfully! Close the tab or refresh the page.")
    st.rerun()

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
def hide_zeros_and_nans(val):
    if val == 0 or pd.isna(val) or val == "-":
        return ""
    if isinstance(val, float):
        return f"{val:.2f}".rstrip('0').rstrip('.')  # e.g., 2.50 → 2.5, 2.00 → 2
    return str(val)



def color_rows(_, full_df, display_df):
    # Create empty style DataFrame aligned to display_df
    styles = pd.DataFrame('', index=display_df.index, columns=display_df.columns)

    # Loop through full_df rows
    for idx in display_df.index:
        if idx in full_df.index:
            row_type = full_df.loc[idx, "Type"]
            if row_type in color_map:
                styles.loc[idx] = ['background-color: ' + color_map[row_type]] * len(display_df.columns)
            else:
                styles.loc[idx] = ['background-color: white'] * len(display_df.columns)

    return styles

# --- Load data ---
def load_data():
    df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
    return df

def drop_empty_or_zero_column(df):
    for column_name in df.columns:
        # Replace NaN with 0 for checking purposes
        col_values = df[column_name].fillna(0)
        if (col_values == 0).all():
            df = df.drop(columns=[column_name])
        
    
    return df
def highlight_over_budget(df):
    """
    For each division, checks column-wise if
    Budget < Expenditure + IFD.
    If true, highlight only those three cells
    (Budget, Expenditure, IFD) in that column.
    """
    styles = pd.DataFrame('', index=df.index, columns=df.columns)

    # Process division by division
    for division in df['DIVISION'].unique():
        div_rows = df[df['DIVISION'] == division]

        try:
            budget_row = div_rows.loc[div_rows['Type'] == 'Budget'].iloc[0]
            exp_row = div_rows.loc[div_rows['Type'] == 'Expenditure'].iloc[0]
            ifd_row = div_rows.loc[div_rows['Type'] == 'IFD'].iloc[0]
        except IndexError:
            continue  # skip if missing

        # Check every column except identifiers
        for col in df.columns:
            if col in ['DIVISION', 'Type']:
                continue

            try:
                budget_val = pd.to_numeric(budget_row[col], errors='coerce')
                exp_val = pd.to_numeric(exp_row[col], errors='coerce')
                ifd_val = pd.to_numeric(ifd_row[col], errors='coerce')
            except Exception:
                continue

            if pd.notna(budget_val) and pd.notna(exp_val) and pd.notna(ifd_val):
                if (exp_val) > budget_val:
                    styles.loc[budget_row.name, col] = 'background-color: #FFCCCC'  # Light red background
                    styles.loc[exp_row.name, col] = 'background-color: #FFCCCC'
                    styles.loc[ifd_row.name, col] = 'background-color: #FFCCCC'

    return styles

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

    st.set_page_config(page_title="Vigyan Dhara - Expenditure data 2024-25",page_icon='📊', layout="wide")


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
                        <h2>Vigyan Dhara Expenditure Data 2024-25</h2>
                        <img src="data:image/png;base64, {logo_right}" />
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
        text-align: center;
    }
    .vertical-line {
        width: 1px;
        height: 30px;
        background-color: grey;
        align-self: center;
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
        df = load_all_data()
        updated_by, last_updated = load_info()
        if df.empty or df.shape[1] < 2:
            st.error("Sheet is empty or has less than two columns.")
        else:
            # --- Get unique values from 2nd column ---
            df = drop_empty_or_zero_column(df)
            second_col = df.columns[-1]
            unique_vals = sorted(df[second_col].dropna().unique())
            # --- Show checkboxes ---
            # st.subheader(f"Filter by `{second_col}`")
            st.subheader("Filter by :")

            # Create two rows of columns: first for filters + info
            filter_cols = st.columns([len(unique_vals), 2])  # wide for filters, narrow for info

            with filter_cols[0]:
                selected_filters = []
                cols = st.columns(len(unique_vals))
                for i, val in enumerate(unique_vals):
                    with cols[i]:
                        cb = st.checkbox(" ", key=f"cb_{val}", value=True)
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

            with filter_cols[1]:
                st.markdown(
                    f"""
                    <div style='text-align: right; font-size:16px; font-weight:bold;'>
                        Data Last Updated On: <span style="color:blue;">{last_updated}</span><br>
                        Updated By: <span style="color:green;">{updated_by}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # --- Filter data ---
            if selected_filters:
                filtered_df = df[df[second_col].isin(selected_filters)]

                # Make a copy for display
                display_df = filtered_df.copy()

                # Hide duplicate DIVISION values (only consecutive duplicates)
                display_df['DIVISION'] = display_df['DIVISION'].mask(display_df['DIVISION'].duplicated(), '')

                # Drop 'Type' column ONLY from the display copy
                if 'Type' in display_df.columns:
                    display_df = display_df.drop(columns=['Type'])

                # Apply formatting for hiding 0s/NaNs
                display_df = display_df.map(hide_zeros_and_nans)

                # Highlight over budget applied on filtered_df
                def highlight_display(_, full_df):
                    # Call your existing function, but align result to display_df
                    styles = highlight_over_budget(full_df)
                    if 'Type' in styles.columns:
                        styles = styles.drop(columns=['Type'])
                    return styles.reindex(columns=display_df.columns, index=display_df.index, fill_value='')

                # Build styled DataFrame
                styled_df = (
                    display_df.style
                    .set_properties(**{'font-weight': 'bold','font-size': '24px'}, subset=[display_df.columns[-1]])
                    .set_properties(**{'font-weight': 'bold','font-size': '24px'}, subset=[display_df.columns[0]])
                    .set_properties(**{'font-weight': 'bold','font-size': '24px'}, subset=(display_df.index[-1], slice(None)))
                    .set_properties(**{'font-weight': 'bold','font-size': '24px'}, subset=(display_df.index[-2], slice(None)))
                    .set_properties(**{'font-weight': 'bold','font-size': '24px'}, subset=(display_df.index[-3], slice(None)))
                    .set_table_styles([{'selector': 'th', 'props': [('font-size', '24px'), ('font-weight', 'bold')]}])
                    .apply(color_rows, axis=None, full_df=filtered_df, display_df=display_df)
                    .apply(highlight_display, axis=None, full_df=filtered_df)
                )

                st.dataframe(styled_df, use_container_width=True, height=len(display_df) * 35 + 50)


    except Exception as e:
        st.error(f"Failed to load or parse the CSV: {e}")


    if st.button("Logout"):
        clear_login_cookie()


if __name__ == "__main__":
    main()