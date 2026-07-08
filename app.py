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

# Read the latest spreadsheet data live
@st.fragment
def load_data():
    return conn.read(worksheet="Sheet1", ttl=0)

try:
    df_guests = load_data()
except Exception:
    st.error("⚠️ Could not read your Google Sheet. Please double-check your Streamlit Secrets setting!")
    st.stop()

# --- SECTION 1: ADD GUESTS ---
st.subheader("➕ Add New Guest")
new_guest = st.text_input("Enter Guest Name:")
if st.button("Add to List"):
    if new_guest.strip() != "":
        if new_guest not in df_guests["Guest Name"].values:
            # Create a row for the new guest
            new_row = pd.DataFrame([{"Guest Name": new_guest, "Status": "Not Entered", "Check-in Time": "-"}])
            updated_df = pd.concat([df_guests, new_row], ignore_index=True)
            # Push changes to Google Sheets
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success(f"📌 {new_guest} successfully saved to Google Sheets!")
            st.rerun()
        else:
            st.warning("This guest is already on the list.")

# --- SECTION 2: LIVE SMARTPHONE SCANNER ---
st.subheader("📷 Scan QR Code")
st.write("Grant camera permission if prompted, then hold up a ticket:")

scanned_data = qrcode_scanner(key="qr_scanner")

if scanned_data:
    st.info(f"Scanned Ticket for: {scanned_data}")
    if scanned_data in df_guests["Guest Name"].values:
        idx = df_guests[df_guests["Guest Name"] == scanned_data].index[0]
        
        if df_guests.at[idx, "Status"] == "Not Entered":
            df_guests.at[idx, "Status"] = "Arrived"
            df_guests.at[idx, "Check-in Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save check-in back to Google Sheets
            conn.update(worksheet="Sheet1", data=df_guests)
            st.balloons() 
            st.success(f"Welcome! {scanned_data} has been checked in.")
            st.rerun()
        else:
            st.warning(f"{scanned_data} has ALREADY entered!")
    else:
        st.error("🚨 UNKNOWN GUEST: Name not on the guest list!")

# --- SECTION 3: GUEST LIST & QR GENERATOR ---
st.subheader("📋 Current Guest List")
if not df_guests.empty:
    st.dataframe(df_guests, use_container_width=True)
    
    selected_guest = st.selectbox("Select a guest to view/save their QR Code:", df_guests["Guest Name"])
    
    if selected_guest:
        qr = qrcode.make(selected_guest)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.image(byte_im, caption=f"QR Code Ticket for {selected_guest}", width=200)
        st.download_button(label="Download QR Ticket", data=byte_im, file_name=f"{selected_guest}_ticket.png", mime="image/png")
else:
    st.write("No guests found in your Google Sheet.")
