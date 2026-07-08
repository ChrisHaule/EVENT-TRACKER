import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from datetime import datetime

st.set_page_config(page_title="Event Guest Tracker", layout="centered")

st.title("🎉 Event Guest Tracker & Scanner")

# Temporary smartphone storage setup
if "guest_list" not in st.session_state:
    st.session_state.guest_list = pd.DataFrame(columns=["Guest Name", "Status", "Check-in Time"])

# --- SECTION 1: ADD GUESTS ---
st.subheader("➕ Add New Guest")
new_guest = st.text_input("Enter Guest Name:")
if st.button("Add to List"):
    if new_guest.strip() != "":
        if new_guest not in st.session_state.guest_list["Guest Name"].values:
            new_row = pd.DataFrame([{"Guest Name": new_guest, "Status": "Not Entered", "Check-in Time": "-"}])
            st.session_state.guest_list = pd.concat([st.session_state.guest_list, new_row], ignore_index=True)
            st.success(f"📌 {new_guest} added successfully!")
        else:
            st.warning("This guest is already on the list.")

# --- SECTION 2: LIVE SMARTPHONE SCANNER ---
st.subheader("📷 Scan QR Code")
st.write("Grant camera permission if prompted, then hold up a ticket:")

# This triggers the interactive scanner component
scanned_data = qrcode_scanner(key="qr_scanner")

if scanned_data:
    st.info(f"Scanned Ticket for: {scanned_data}")
    if scanned_data in st.session_state.guest_list["Guest Name"].values:
        idx = st.session_state.guest_list[st.session_state.guest_list["Guest Name"] == scanned_data].index[0]
        
        if st.session_state.guest_list.at[idx, "Status"] == "Not Entered":
            st.session_state.guest_list.at[idx, "Status"] = "Arrived"
            st.session_state.guest_list.at[idx, "Check-in Time"] = datetime.now().strftime("%H:%M:%S")
            st.balloons() 
            st.success(f"Welcome! {scanned_data} has been checked in.")
        else:
            st.warning(f"{scanned_data} has ALREADY entered!")
    else:
        st.error("🚨 UNKNOWN GUEST: Name not on the guest list!")

# --- SECTION 3: GUEST LIST & QR GENERATOR ---
st.subheader("📋 Current Guest List")
if not st.session_state.guest_list.empty:
    st.dataframe(st.session_state.guest_list, use_container_width=True)
    
    selected_guest = st.selectbox("Select a guest to view/save their QR Code:", st.session_state.guest_list["Guest Name"])
    
    if selected_guest:
        qr = qrcode.make(selected_guest)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.image(byte_im, caption=f"QR Code Ticket for {selected_guest}", width=200)
        st.download_button(label="Download QR Ticket", data=byte_im, file_name=f"{selected_guest}_ticket.png", mime="image/png")
else:
    st.write("No guests added yet.")
