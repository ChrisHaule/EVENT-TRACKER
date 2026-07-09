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

if "guest" in query_params and "action" in query_params:
    guest_name = query_params["guest"]
    action_choice = query_params["action"]
    status_text = "Attending" if action_choice == "yes" else "Declined"
    try:
        # Read the latest data
        df = conn.read(worksheet="Sheet1", ttl=0)
        df.columns = df.columns.str.strip()
        
        if "Guest Name" in df.columns:
            matched_rows = df[df["Guest Name"] == guest_name]
            if not matched_rows.empty:
                row_idx = matched_rows.index[0]
                
                # Correctly grab the underlying gspread client and URL
                gc = conn.client
                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
                sh = gc.open_by_url(spreadsheet_url)
                worksheet = sh.worksheet("Sheet1")
                
                # Column 5 is 'Confirmation' (E)
                worksheet.update_cell(row_idx + 2, 5, status_text)
                
                if action_choice == "yes":
                    st.success(f"🎉 Thank you, {guest_name}! Your response has been recorded as **Attending**.")
                else:
                    st.info(f"✉️ Thank you, {guest_name}. Your response has been recorded as **Declined**.")
                
                st.rerun()
            else:
                st.error("Guest name not found in sheet records.")
    except Exception as e:
        st.error(f"Error logging response automatically: {e}")
  
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
# --- EMAIL SENDER FUNCTION ---
def send_invite_email(guest_name, guest_email):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["app_password"]
    base_url = st.secrets["email"]["base_url"]
    
    yes_url = f"{base_url}/?guest={guest_name}&action=yes"
    no_url = f"{base_url}/?guest={guest_name}&action=no"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Exclusive Invitation for {guest_name}"
    msg["From"] = f"Event Management <{sender}>"
    msg["To"] = guest_email
    
    text = f"Hello {guest_name},\n\nYou are cordially invited! Confirm attendance:\n\nI'm Coming: {yes_url}\nCan't Make It: {no_url}"
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333;">
        <h2 style="color: #2E4053;">Hello {guest_name},</h2>
        <p>You are cordially invited to our event. Please let us know if you will be joining us by choosing an option below:</p>
        <br>
        <p>
          <a href="{yes_url}" style="background-color: #27AE60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 15px;">👍 I'm Coming</a>
          <a href="{no_url}" style="background-color: #E74C3C; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">👎 Can't Make It</a>
        </p>
        <br>
        <p>We look forward to hearing from you!</p>
        <hr style="border: 0; border-top: 1px solid #EEEEEE;">
        <p style="font-size: 12px; color: #777777;">Sent via Event Management System.</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, guest_email, msg.as_string())


# --- MAIN INTERFACE BUTTON PANEL ---
st.markdown("---")
st.subheader("📩 Send Digital Invites")
st.write("Click below to automatically email confirmation links to all pending guests with valid emails:")

if st.button("🚀 Blast Invites to All Guests", use_container_width=True):
    try:
        df_guests = conn.read(worksheet="Sheet1", ttl=0)
        df_guests.columns = df_guests.columns.str.strip()
        
        sent_count = 0
        for idx, row in df_guests.iterrows():
            name = row.get("Guest Name")
            email = row.get("Email")
            confirmation = row.get("Confirmation")
            
            # Check if a valid email is present
            if email and str(email).strip() != "" and str(email).lower() not in ["none", "nan"]:
                # Catch empty text, missing values, or python 'nan' markers
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
