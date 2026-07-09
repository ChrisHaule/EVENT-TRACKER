import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Chris Events Management", layout="centered")

st.title("🎉 CHRIS EVENTS AND WEDDINGS MANAGEMENT")

# Establish connection to your Google Sheet database
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HANDLE INBOUND GUEST CONFIRMATIONS ---
query_params = st.query_params
is_guest_view = False  # Track if a guest is using the link

if "guest" in query_params and "action" in query_params:
    guest_name = query_params["guest"]
    action_choice = query_params["action"]
    status_text = "Attending" if action_choice == "yes" else "Declined"
    is_guest_view = True  # Hide everything else for them!
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df.columns = df.columns.str.strip()
        
        if "Guest Name" in df.columns:
            matched_rows = df[df["Guest Name"] == guest_name]
            if not matched_rows.empty:
                row_idx = matched_rows.index[0]
                
                # Connect using your existing 'spreadsheet' secret key cleanly
                gc = conn.client
                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                sh = gc.open_by_url(spreadsheet_url)
                worksheet = sh.worksheet("Sheet1")
                
                # Column 5 is 'Confirmation' (E)
                worksheet.update_cell(row_idx + 2, 5, status_text)
                
# --- ONLY SHOW THE MANAGEMENT APP IF IT IS NOT A GUEST LINK ---
if not is_guest_view:
    st.title("🎉 CHRIS EVENTS AND WEDDINGS MANAGEMENT")

    # Read the latest spreadsheet data live
    @st.fragment
    def load_data():
        try:
            df = conn.read(worksheet="Sheet1", ttl=0)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error reading data: {e}")
            return None

    df_guests = load_data()

    if df_guests is not None:
        # --- SECTION 1: ADD NEW GUEST ---
        st.subheader("➕ Add New Guest")
        new_guest = st.text_input("Enter Guest Name:", key="new_guest_input")
        new_email = st.text_input("Enter Guest Email (Optional):", key="new_email_input")

        if st.button("Add to List"):
            if new_guest.strip() != "":
                try:
                    gc = conn.client
                    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    sh = gc.open_by_url(spreadsheet_url)
                    worksheet = sh.worksheet("Sheet1")
                    
                    # Append new row: Name, Status, Check-in Time, Payment, Confirmation, Email
                    worksheet.append_row([new_guest.strip(), "Not entered", "", "", "", new_email.strip()])
                    st.success(f"Added {new_guest} to the guest list!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add guest: {e}")
            else:
                st.warning("Please enter a valid name.")

        st.markdown("---")

        # --- SECTION 2: SCAN QR CODE ---
        st.subheader("📷 Scan QR Code")
        st.write("Grant camera permission if prompted, then hold up the ticket:")

        qrcode = st_qrcode_scanner(key="qr_scanner")

        if qrcode:
            st.info(f"Detected QR Code Data: {qrcode}")
            guest_name = qrcode.strip()
            
            if "Guest Name" in df_guests.columns:
                matched_rows = df_guests[df_guests["Guest Name"].str.strip().str.lower() == guest_name.lower()]
                
                if not matched_rows.empty:
                    row_idx = matched_rows.index[0]
                    current_status = matched_rows.iloc[0]["Status"]
                    
                    if current_status == "Arrived":
                        st.warning(f"⚠️ {guest_name} has ALREADY checked in!")
                    else:
                        try:
                            from datetime import datetime
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            gc = conn.client
                            spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                            sh = gc.open_by_url(spreadsheet_url)
                            worksheet = sh.worksheet("Sheet1")
                            
                            # Row indices in gspread are 1-based, and headers take row 1
                            worksheet.update_cell(row_idx + 2, 2, "Arrived")
                            worksheet.update_cell(row_idx + 2, 3, now_str)
                            
                            st.success(f"✅ Success! {guest_name} checked in at {now_str}")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update spreadsheet: {e}")
                else:
                    st.error(f"❌ Error: '{guest_name}' is not on the guest list.")
            else:
                st.error("Error: 'Guest Name' column missing from sheet layout.")

        st.markdown("---")

        # --- SECTION 3: GUEST LIST DIRECTORY ---
        st.subheader("📋 Live Guest Directory")
        st.dataframe(df_guests, use_container_width=True)

        # --- SECTION 4: MAIN INTERFACE BUTTON PANEL ---
        st.markdown("---")
        st.subheader("📩 Send Digital Invites")
        st.write("Click below to automatically email confirmation links to all pending guests with valid emails:")

        if st.button("🚀 Blast Invites to All Guests", use_container_width=True):
            try:
                sent_count = 0
                for idx, row in df_guests.iterrows():
                    name = row.get("Guest Name")
                    email = row.get("Email")
                    confirmation = row.get("Confirmation")
                    
                    if email and str(email).strip() != "" and str(email).lower() not in ["none", "nan"]:
                        is_pending = pd.isna(confirmation) or str(confirmation).strip() == "" or str(confirmation).lower() in ["none", "nan"]
                        
                        if is_pending:
                            send_invite_email(name, str(email).strip())
                            sent_count += 1
                        
                if sent_count > 0:
                    st.success(f"Successfully broadcasted {sent_count} invitations!")
                else:
                    st.info("No pending guests found with an email address.")
                    
            except Exception as e:
                st.error(f"Failed to broadcast invites: {e}")

