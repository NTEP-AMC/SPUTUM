import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- PDF Generation Libraries ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- Page Config ---
st.set_page_config(page_title="AMC Sputum Dashboard", layout="wide")

# ==========================================
# 1. LOGIN SYSTEM (ID/PASSWORD)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.target = ""

# Load users.csv
try:
    users_df = pd.read_csv("users.csv")
except Exception as e:
    st.error("⚠️ 'users.csv' ફાઇલ પ્રોજેક્ટમાં મળી નથી. કૃપા કરીને GitHub પર અપલોડ કરો.")
    st.stop()

# જો લોગીન ન હોય તો લોગીન સ્ક્રીન બતાવો
if not st.session_state.logged_in:
    st.title("🔒 AMC Sputum Dashboard - Login")
    st.markdown("કૃપા કરીને આગળ વધવા માટે તમારું યુઝરનેમ અને પાસવર્ડ દાખલ કરો.")
    
    with st.form("login_form"):
        uname = st.text_input("Username (યુઝરનેમ)")
        pwd = st.text_input("Password (પાસવર્ડ)", type="password")
        submit_login = st.form_submit_button("લૉગિન કરો")
        
        if submit_login:
            user_match = users_df[(users_df['Username'] == uname) & (users_df['Password'] == pwd)]
            
            if not user_match.empty:
                st.session_state.logged_in = True
                st.session_state.username = user_match.iloc[0]['Username']
                st.session_state.role = user_match.iloc[0]['Role']
                st.session_state.target = user_match.iloc[0]['Target']
                st.success("લોગીન સફળ!")
                st.rerun()
            else:
                st.error("❌ ખોટો આઈડી અથવા પાસવર્ડ! કૃપા કરીને ફરી પ્રયાસ કરો.")
    st.stop()

# ==========================================
# 2. MAIN APP (After Login)
# ==========================================

st.sidebar.title(f"સ્વાગત છે, {st.session_state.username}")
st.sidebar.info(f"Role: {st.session_state.role} | Target: {st.session_state.target}")
if st.sidebar.button("લૉગઆઉટ (Logout)"):
    st.session_state.logged_in = False
    st.rerun()

# --- Google Sheets Connection ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JQULxVA1XMk_1PEAmMYTJ-I3T4uMpobx1LCKAuXkTV4/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

ZONES = ["WEST", "SOUTH", "SOUTH WEST", "NORTH WEST", "CENTRAL", "EAST", "NORTH"]

@st.cache_data(ttl=5)
def load_transporters():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="TRANSPORTER_NAME")
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"⚠️ ગૂગલ શીટ (TRANSPORTER_NAME) કનેક્ટ કરવામાં ભૂલ: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=5)
def load_entries():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="ENTRY_DATA")
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"⚠️ ગૂગલ શીટ (ENTRY_DATA) કનેક્ટ કરવામાં ભૂલ: {e}")
        return pd.DataFrame()

transporter_df = load_transporters()
entries_df = load_entries()

# --- ટ્રાન્સપોર્ટર સિલેક્શન લિસ્ટ (નામ + એકાઉન્ટ નંબર) ---
transporter_list = []
if not transporter_df.empty and "NAME OF TRANSPORTER" in transporter_df.columns:
    if "ACCOUNT NUMBER" in transporter_df.columns:
        # નામ અને એકાઉન્ટ નંબર જોડીને ડ્રોપડાઉન માટે લિસ્ટ બનાવો
        transporter_df["Display_Name"] = transporter_df["NAME OF TRANSPORTER"].astype(str) + " - (A/c: " + transporter_df["ACCOUNT NUMBER"].astype(str) + ")"
        transporter_list = transporter_df["Display_Name"].tolist()
    else:
        transporter_list = transporter_df["NAME OF TRANSPORTER"].tolist()

# --- PDF Functions ---
def generate_pdf(phi_name, tb_unit, month_name, approved_df):
    pdf_filename = "Approved_Sputum_Report.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    try:
        pdfmetrics.registerFont(TTFont('Shruti', 'shruti.ttf'))
        font_name = 'Shruti'
    except:
        font_name = 'Helvetica'

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(name='HeaderStyle', fontName=font_name, fontSize=12, leading=16)
    elements.append(Paragraph(f"<b>NAME OF PHI....</b> {phi_name}", header_style))
    elements.append(Paragraph(f"<b>NAME OF TB UNIT.</b> {tb_unit}", header_style))
    elements.append(Paragraph(f"<b>MONTH</b> {month_name}", header_style))
    elements.append(Spacer(1, 20))
    
    table_data = [["તારીખ", "સ્પુટમ ટ્રાન્સપોટર નું નામ", "લેબ નંબર", "સ્પુટમ ક્યા મોક્લ્યા", "સ્પુટમની સંખ્યા"]]
    for index, row in approved_df.iterrows():
        table_data.append([str(row["Date"]), str(row["Transporter_Name"]), str(row["Lab_Number"]), str(row["Route"]), str(row["Sample_Count"])])
        
    table = Table(table_data, colWidths=[70, 150, 70, 150, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.teal), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,-1), font_name), ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black), ('BOTTOMPADDING', (0,0), (-1,0), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 50))
    
    footer_data = [["L.T.", "S.T.L.S.", "M.O.PHI", "M.O.SUPERVISOR"]]
    footer_table = Table(footer_data, colWidths=[130, 130, 130, 130])
    footer_table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), font_name), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(footer_table)
    doc.build(elements)
    return pdf_filename

def generate_summary_pdf(tb_unit, month_name, approved_df):
    pdf_filename = "Summary_Sputum_Report.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    try:
        pdfmetrics.registerFont(TTFont('Shruti', 'shruti.ttf'))
        font_name = 'Shruti'
    except:
        font_name = 'Helvetica'

    title_style = ParagraphStyle(name='TitleStyle', fontName=font_name, fontSize=16, textColor=colors.teal, alignment=0)
    summary_style = ParagraphStyle(name='SummaryStyle', fontName=font_name, fontSize=22, alignment=1, spaceAfter=20)
    header_style = ParagraphStyle(name='HeaderStyle', fontName=font_name, fontSize=12, leading=16)

    elements.append(Paragraph("<b>DMC સ્પુટમ ટ્રાન્સપોર્ટેશન રજિસ્ટર</b>", title_style))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>SUMMARY</b>", summary_style))
    elements.append(Paragraph(f"<b>MONTH:</b> {month_name} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>TU & DMC:</b> {tb_unit}", header_style))
    elements.append(Spacer(1, 20))
    
    table_data = [["ક્રમ", "સ્પુટમ ટ્રાન્સપોટરનું નામ", "કેટલા સ્પુટમ મોકલ્યા", "રકમ રૂ."]]
    
    approved_df['Sample_Count'] = pd.to_numeric(approved_df['Sample_Count'], errors='coerce').fillna(0)
    summary_df = approved_df.groupby("Transporter_Name")["Sample_Count"].sum().reset_index()
    
    for index, row in summary_df.iterrows():
        table_data.append([str(index + 1), str(row["Transporter_Name"]), str(int(row["Sample_Count"])), ""])
        
    table = Table(table_data, colWidths=[50, 200, 150, 100])
    table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), font_name), ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black), ('BOTTOMPADDING', (0,0), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 60))
    
    footer_data = [["LT", "STLS", "M.O", "MO. SUP"]]
    footer_table = Table(footer_data, colWidths=[120, 120, 120, 120])
    footer_table.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), font_name), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(footer_table)
    doc.build(elements)
    return pdf_filename

# ==========================================
# 3. ROLE BASED DASHBOARD
# ==========================================

# ------------------------------------------
# TB_UNIT ROLE (STAFF ENTRY)
# ------------------------------------------
if st.session_state.role in ["TB_UNIT", "ADMIN"]:
    st.title("📝 સ્ટાફ એન્ટ્રી ફોર્મ")
    
    with st.expander("➕ લિસ્ટમાં નવો ટ્રાન્સપોર્ટર ઉમેરો"):
        with st.form("add_transporter", clear_on_submit=True):
            st.markdown("**નવા સ્ટાફની વિગતો ભરો:**")
            col_a, col_b = st.columns(2)
            with col_a:
                new_name = st.text_input("નવા ટ્રાન્સપોર્ટરનું નામ *")
                new_ac = st.text_input("ખાતા નંબર *")
                new_ifsc = st.text_input("IFSC CODE")
            with col_b:
                new_mobile = st.text_input("MOBILE NUMBER")
                new_tb_unit = st.text_input("TB UNIT")
                new_phi = st.text_input("PHI")
                
            if st.form_submit_button("ઉમેરો"):
                if new_name and new_ac:
                    new_row = pd.DataFrame({"NAME OF TRANSPORTER": [new_name.upper().strip()], "ACCOUNT NUMBER": [new_ac.strip()], "IFSC CODE": [new_ifsc.strip().upper()], "MOBILE NUMBER": [new_mobile.strip()], "TB UNIT": [new_tb_unit.strip().upper()], "PHI": [new_phi.strip().upper()]})
                    updated_transporters = pd.concat([transporter_df, new_row], ignore_index=True)
                    conn.update(worksheet="TRANSPORTER_NAME", data=updated_transporters)
                    st.success(f"✅ {new_name} સફળતાપૂર્વક ઉમેરાઈ ગયું છે!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("⚠️ કૃપા કરીને નામ અને ખાતા નંબર ફરજિયાત ભરો.")

    with st.form("data_entry_form", clear_on_submit=True):
        st.markdown("**નવી એન્ટ્રી:**")
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("તારીખ", date.today())
            t_name_display = st.selectbox("સ્પુટમ ટ્રાન્સપોર્ટરનું નામ અને એકાઉન્ટ નંબર પસંદ કરો", transporter_list)
            l_num = st.text_input("લેબ નંબર")
        with col2:
            zone = st.selectbox("તમારો ઝોન પસંદ કરો", ZONES)
            route = st.text_input("સ્પુટમ ક્યાંથી ક્યાં મોકલ્યા")
            s_count = st.number_input("સ્પુટમની સંખ્યા", min_value=1)
            
        if st.form_submit_button("સાચવો (Save as Pending)"):
            if t_name_display and l_num:
                # ડ્રોપડાઉનમાંથી માત્ર નામ અલગ કરવા માટે
                actual_t_name = t_name_display.split(" - (A/c:")[0] if " - (A/c:" in t_name_display else t_name_display
                
                new_entry = pd.DataFrame({"Date": [entry_date.strftime("%d-%m-%Y")], "Zone": [zone], "Transporter_Name": [actual_t_name], "Lab_Number": [l_num], "Route": [route], "Sample_Count": [s_count], "Status": ["Pending"]})
                updated_entries = pd.concat([entries_df, new_entry], ignore_index=True)
                conn.update(worksheet="ENTRY_DATA", data=updated_entries)
                st.success("એન્ટ્રી M.O. ના અપ્રૂવલ માટે મોકલાઈ ગઈ છે!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("માહિતી પૂરી ભરો.")
    st.divider()

# ------------------------------------------
# ZONE / ADMIN ROLE (M.O. APPROVAL)
# ------------------------------------------
if st.session_state.role in ["ZONE", "ADMIN"]:
    st.title("✅ M.O. અપ્રૂવલ અને PDF જનરેશન")
    
    if st.session_state.role == "ZONE":
        mo_zone = st.session_state.target
        st.info(f"તમે **{mo_zone}** ઝોન માટે લોગીન કર્યું છે.")
    else:
        mo_zone = st.selectbox("📌 અપ્રૂવલ માટે તમારો ઝોન પસંદ કરો:", ZONES)
    
    st.subheader(f"1. {mo_zone} ઝોનની પેન્ડિંગ એન્ટ્રીઓ")
    if not entries_df.empty and "Status" in entries_df.columns:
        pending_df = entries_df[(entries_df["Status"] == "Pending") & (entries_df["Zone"] == mo_zone)].copy()
        
        if not pending_df.empty:
            pending_df.insert(0, "Approve", False)
            edited_df = st.data_editor(pending_df, hide_index=True, use_container_width=True)
            
            if st.button("✔ પસંદ કરેલ એન્ટ્રીઓ Approve કરો"):
                approved_indices = edited_df[edited_df["Approve"] == True].index
                if not approved_indices.empty:
                    entries_df.loc[approved_indices, "Status"] = "Approved"
                    conn.update(worksheet="ENTRY_DATA", data=entries_df)
                    st.success(f"{len(approved_indices)} એન્ટ્રીઓ Approve થઈ ગઈ છે!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("કોઈ એન્ટ્રી સિલેક્ટ કરી નથી.")
        else:
            st.info(f"હાલમાં {mo_zone} ઝોનમાં કોઈ પેન્ડિંગ એન્ટ્રી નથી.")
            
    st.divider()
    
    st.subheader(f"2. {mo_zone} ઝોનનો રિપોર્ટ જનરેટ કરો")
    if not entries_df.empty and "Status" in entries_df.columns:
        approved_data = entries_df[(entries_df["Status"] == "Approved") & (entries_df["Zone"] == mo_zone)]
        
        if not approved_data.empty:
            st.dataframe(approved_data.drop(columns=["Status"]), hide_index=True, use_container_width=True)
            col1, col2, col3 = st.columns(3)
            with col1: phi = st.text_input("NAME OF PHI")
            with col2: tb = st.text_input("NAME OF TB UNIT")
            with col3: month = st.text_input("MONTH")
            
            st.write("---")
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("📄 Generate Detailed PDF"):
                    if phi and tb and month:
                        pdf_file_path = generate_pdf(phi, tb, month, approved_data)
                        with open(pdf_file_path, "rb") as pdf_file:
                            st.download_button(label="⬇️ વિગતવાર PDF ડાઉનલોડ કરો", data=pdf_file, file_name=f"{mo_zone}_Detailed_Report_{month}.pdf", mime="application/pdf")
                    else:
                        st.error("કૃપા કરીને PHI, TB UNIT અને MONTH ની વિગતો ભરો.")
                        
            with col_btn2:
                if st.button("📊 Generate SUMMARY PDF"):
                    if tb and month:
                        pdf_file_path = generate_summary_pdf(tb, month, approved_data.copy())
                        with open(pdf_file_path, "rb") as pdf_file:
                            st.download_button(label="⬇️ SUMMARY PDF ડાઉનલોડ કરો", data=pdf_file, file_name=f"{mo_zone}_Summary_{month}.pdf", mime="application/pdf")
                    else:
                        st.error("કૃપા કરીને TB UNIT અને MONTH ની વિગતો ભરો.")
