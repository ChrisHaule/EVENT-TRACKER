import streamlit as st
import pandas as pd
import numpy as np
import cv2
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set up page config
st.set_page_config(page_title="Event Management System", layout="centered")

def send_invite_email(guest_name, guest_email):
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    app_url = st.secrets["email"]["base_url"]
    yes_url = f"{app_url}?guest={guest_name.replace(' ', '%20')}&action=yes"
    no_url = f"{app_url}?guest={guest_name.replace(' ', '%20')}&action=no"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Exclusive Invitation for {guest_name}"
    msg["From"] = f"Event Management <{sender}>"
    msg["To"] = guest_email

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; padding: 20px; text-align: center;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #1e1e1e; padding: 30px; border-radius: 10px; border: 1px solid #333;">
            <h2 style="color: #ffffff; margin-bottom: 20px;">Hello {guest_name},</h2>
            <p style="font-size: 16px; color: #b3b3b3; line-height: 1.5;">You are cordially invited to our event. Please let us know if you will be joining us by choosing an option below:</p>
            
            <div style="margin: 30px 0;">
                <a href="{yes_url}" style="background-color: #198754; color: white; padding: 12px 25px; text-decoration: none; font-weight: bold; border-radius: 5px; margin-right: 15px; display: inline-block;">👍 I'm Coming</a>
                <a href="{no_url}" style="background-color: #dc3545; color: white; padding: 12px 25px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">👎 Can't Make It</a>
            </div>
            <hr style="border: 0; border-top: 1px solid #333; margin: 20px 0;">
            <p style="font-size: 14px; color: #777;">We look forward to hearing from you!</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, guest_email, msg.as_string())
    except Exception as e:
        st.error(f"Failed to email {guest_name}: {e}")

# Initialize Spreadsheet Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HANDLE INBOUND GUEST CONFIRMATIONS ---
query_params = st.query_params
is_guest_view = False  # Track if a guest is using the link

if "guest" in query_params and "action" in query_params:
    guest_name = query_params["guest"]
    action_choice = query_params["action"]
    status_text = "Attending" if action_choice == "yes" else "Declined"
    is_guest_view = True  # Hide the admin panel for them
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df.columns = df.columns.str.strip()
        
        if "Guest Name" in df.columns:
            matched_rows = df[df["Guest Name"] == guest_name]
            if not matched_rows.empty:
                row_idx = matched_rows.index[0]
                
                # FIX APPLIED HERE: Added ._client to access open_by_url correctly
                gc = conn.client._client
                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                sh = gc.open_by_url(spreadsheet_url)
                worksheet = sh.worksheet("Sheet1")
                
                worksheet.update_cell(row_idx + 2, 5, status_text)
                
                st.balloons()
                st.markdown("<h1 style='text-align: center;'>✨ Response Recorded! ✨</h1>", unsafe_allow_html=True)
                st.markdown("---")
                if action_choice == "yes":
                    st.success(f"### 🎉 Thank you, {guest_name}!\nYour response has been recorded as **Attending**.")
                else:
                    st.info(f"### ✉️ Thank you for letting us know, {guest_name}.\nYour response has been recorded as **Declined**.")
            else:
                st.error("Guest name not found in sheet records.")
    except Exception as e:
        st.error(f"Error logging response automatically: {e}")

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
                    # FIX APPLIED HERE: Added ._client to access open_by_url correctly
                    gc = conn.client._client
                    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    sh = gc.open_by_url(spreadsheet_url)
                    worksheet = sh.worksheet("Sheet1")
                    
                    worksheet.append_row([new_guest.strip(), "Not entered", "", "", "", new_email.strip()])
                    st.success(f"Added {new_guest} to the guest list!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add guest: {e}")
            else:
                st.warning("Please enter a valid name.")

        st.markdown("---")

        # --- SECTION 2: SCAN QR CODE (NATIVE CAMERA INTERFACE) ---
        st.subheader("📷 Scan QR Code")
        st.write("Take a picture of the ticket's QR code below:")

        camera_image = st.camera_input("Scan Ticket")

        if camera_image is not None:
            try:
                # Convert camera bytes into a computer vision image array
                file_bytes = np.asarray(bytearray(camera_image.read()), dtype=np.uint8)
                opencv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                # Detect and decode QR code
                detector = cv2.QRCodeDetector()
                qrcode_data, _, _ = detector.detectAndDecode(opencv_img)
                
                if qrcode_data:
                    guest_name = qrcode_data.strip()
                    st.info(f"Detected QR Code Data: {guest_name}")
                    
                    if "Guest Name" in df_guests.columns:
                        matched_rows = df_guests[df_guests["Guest Name"].str.strip().str.lower() == guest_name.lower()]
                        
                        if not matched_rows.empty:
                            row_idx = matched_rows.index[0]
                            current_status = matched_rows.iloc[0]["Status"]
                            
                            if current_status == "Arrived":
                                st.warning(f"⚠️ {guest_name} has ALREADY checked in!")
                            else:
                                from datetime import datetime
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # FIX APPLIED HERE: Added ._client to access open_by_url correctly
                                gc = conn.client._client
                                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                                sh = gc.open_by_url(spreadsheet_url)
                                worksheet = sh.worksheet("Sheet1")
                                
                                worksheet.update_cell(row_idx + 2, 2, "Arrived")
                                worksheet.update_cell(row_idx + 2, 3, now_str)
                                
                                st.success(f"✅ Success! {guest_name} checked in at {now_str}")
                                st.balloons()
                                st.rerun()
                        else:
                            st.error(f"❌ Error: '{guest_name}' is not on the guest list.")
                else:
                    st.warning("🤖 Couldn't catch a sharp QR code reading. Hold it steady!")
            except Exception as e:
                st.error(f"Camera tracking parsing issue: {e}")

        st.markdown("---")

        # --- SECTION 3: GUEST LIST DIRECTORY ---
        st.subheader("📋 Live Guest Directory")
        st.dataframe(df_guests, use_container_width=True)
st.markdown("---")
st.subheader("🎫 Generate Guest QR Ticket")

if not df_guests.empty:
    guest_list = df_guests["Guest Name"].tolist()
    selected_guest = st.selectbox("Select a guest to view their QR code ticket:", guest_list)
    
    if selected_guest:
        encoded_name = selected_guest.replace(" ", "%20")
        qr_url = f"https://quickchart.io/qr?text={encoded_name}&size=300"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(qr_url, caption=f"Scan Ticket for {selected_guest}", use_container_width=True)
            st.info(f"💡 Tip: You can long-press the QR code to save it or send it to {selected_guest}!")
else:
    st.warning("No guests found in the directory yet to generate tickets for.")

        # --- SECTION 4: MAIN INTERFACE BUTTON PANEL ---
        st.markdown("---")
        st.subheader("📩 Send Digital Invites")
        st.write("Click below to automatically email confirmation links to all pending guests:")

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
