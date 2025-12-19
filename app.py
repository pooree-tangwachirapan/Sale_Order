import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# --- 1. ตั้งค่า Config และจำลองฐานข้อมูล (Mock Database) ---
st.set_page_config(page_title="Mobile Sale Pro", layout="centered")

# จำลองไฟล์ CSV ฐานข้อมูล (ในใช้งานจริง ส่วนนี้จะโหลดจาก GitHub/File)
if 'db_orders' not in st.session_state:
    # สมมติว่ามีข้อมูลเก่าอยู่แล้ว และมีคอลัมน์ 'owner' เพื่อระบุเจ้าของ
    data = {
        'order_id': ['ORD-001', 'ORD-002'],
        'customer': ['บริษัท ก จำกัด', 'ร้าน ข ขายดี'],
        'items': ['สินค้า A (10)', 'สินค้า C (5)'],
        'total': [1000, 2500],
        'date': ['2023-10-01', '2023-10-02'],
        'owner': ['sale01', 'sale02'] # <--- Key User แยกข้อมูล
    }
    st.session_state.db_orders = pd.DataFrame(data)

if 'db_customers' not in st.session_state:
    data_cust = {
        'name': ['บริษัท ก จำกัด', 'ร้าน ข ขายดี', 'ลูกค้าทั่วไป'],
        'address': ['123 กทม.', '456 เชียงใหม่', '789 ภูเก็ต'],
        'owner': ['sale01', 'sale02', 'sale01'] # ลูกค้าของใครของมัน
    }
    st.session_state.db_customers = pd.DataFrame(data_cust)

# --- 2. ระบบ Login (Simple Authentication) ---
def check_login(username, password):
    # ในใช้งานจริงควรเก็บ Password ที่ Hash แล้ว หรือดึงจากไฟล์ users.csv
    valid_users = {
        "sale01": "1234",
        "sale02": "1234",
        "manager": "admin"
    }
    if username in valid_users and valid_users[username] == password:
        return True
    return False

# ตรวจสอบ Session การล็อกอิน
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = ""

# --- 3. หน้าจอ Login ---
if not st.session_state.logged_in:
    st.header("🔐 เข้าสู่ระบบ (Sale Login)")
    
    with st.form("login_form"):
        username_input = st.text_input("Username (ลองใช้ sale01)")
        password_input = st.text_input("Password (ลองใช้ 1234)", type="password")
        submit_login = st.form_submit_button("Login")
        
        if submit_login:
            if check_login(username_input, password_input):
                st.session_state.logged_in = True
                st.session_state.user_id = username_input
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun() # รีโหลดหน้าเพื่อเข้าสู่โปรแกรมหลัก
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    st.stop() # หยุดการทำงานไม่ให้โชว์ส่วนอื่นถ้ายังไม่ล็อกอิน

# ==========================================
#  🌟 ส่วนโปรแกรมหลัก (เข้าถึงได้เฉพาะหลัง Login)
# ==========================================

current_user = st.session_state.user_id
st.sidebar.write(f"👤 ผู้ใช้งาน: **{current_user}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.title(f"📱 เปิดบิลขาย ({current_user})")

# กรองข้อมูลเฉพาะของ User คนนั้น (Key User Logic)
my_orders = st.session_state.db_orders[st.session_state.db_orders['owner'] == current_user]
my_customers = st.session_state.db_customers[st.session_state.db_customers['owner'] == current_user]

# Tabs เมนู
tab1, tab2, tab3 = st.tabs(["🛒 เปิดบิล", "📜 ประวัติบิล", "👥 ลูกค้า"])

# --- Tab 1: เปิดบิล (Create Order) ---
with tab1:
    st.subheader("สร้างรายการใหม่")
    
    # 1. เลือกลูกค้า (เห็นเฉพาะลูกค้าของตัวเอง)
    cust_options = my_customers['name'].tolist()
    if not cust_options:
        st.warning("ยังไม่มีข้อมูลลูกค้า กรุณาเพิ่มในแท็บลูกค้า")
        selected_cust = None
    else:
        selected_cust = st.selectbox("เลือกลูกค้า", cust_options)
        # แสดงที่อยู่ลูกค้าอัตโนมัติ
        if selected_cust:
            cust_addr = my_customers.loc[my_customers['name'] == selected_cust, 'address'].values[0]
            st.caption(f"📍 ที่อยู่: {cust_addr}")

    st.divider()

    # 2. เลือกสินค้า (Mockup)
    col1, col2 = st.columns([2, 1])
    with col1:
        item_name = st.selectbox("สินค้า", ["สินค้า A (100.-)", "สินค้า B (200.-)", "สินค้า C (500.-)"])
    with col2:
        qty = st.number_input("จำนวน", 1, 100, 1)

    # คำนวณราคาง่ายๆ (ในโค้ดจริงต้องดึงจาก DB สินค้า)
    price_map = {"สินค้า A (100.-)": 100, "สินค้า B (200.-)": 200, "สินค้า C (500.-)": 500}
    unit_price = price_map[item_name]
    total_price = unit_price * qty
    
    st.info(f"💰 ยอดรวมรายการนี้: {total_price:,.2f} บาท")
    
    if st.button("✅ บันทึกและสร้าง PDF", use_container_width=True, type="primary"):
        # 1. บันทึกลง Database (Session State -> CSV)
        new_order = {
            'order_id': f"ORD-{len(st.session_state.db_orders)+1:03d}",
            'customer': selected_cust,
            'items': f"{item_name} x {qty}",
            'total': total_price,
            'date': datetime.now().strftime("%Y-%m-%d"),
            'owner': current_user # <--- 🔑 Key สำคัญ: แปะชื่อเจ้าของ
        }
        # เพิ่มข้อมูลใหม่ลงใน DataFrame กลาง
        st.session_state.db_orders = pd.concat([st.session_state.db_orders, pd.DataFrame([new_order])], ignore_index=True)
        
        st.success("บันทึกข้อมูลเรียบร้อย!")
        
        # 2. สร้าง PDF (จำลอง)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12) # *หมายเหตุ: ต้องลง font ไทยเพิ่มถ้าจะใช้ภาษาไทยใน PDF
        pdf.cell(200, 10, txt=f"Order ID: {new_order['order_id']}", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Customer: {selected_cust} (User: {current_user})", ln=2, align='L')
        pdf.cell(200, 10, txt=f"Item: {new_order['items']}", ln=3, align='L')
        pdf.cell(200, 10, txt=f"Total: {total_price} THB", ln=4, align='R')
        
        # แปลงเป็น Binary เพื่อดาวน์โหลด
        pdf_content = pdf.output(dest='S').encode('latin-1')
        b64 = base64.b64encode(pdf_content).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="order_{new_order["order_id"]}.pdf" style="text-decoration:none;"><button style="width:100%;padding:10px;background-color:red;color:white;border:none;border-radius:5px;">📥 ดาวน์โหลด PDF</button></a>'
        st.markdown(href, unsafe_allow_html=True)

# --- Tab 2: ประวัติบิล (History) ---
with tab2:
    st.subheader(f"ประวัติการขายของ {current_user}")
    # แสดงเฉพาะ Order ของ User นี้เท่านั้น
    st.dataframe(my_orders[['order_id', 'date', 'customer', 'total']], hide_index=True, use_container_width=True)

# --- Tab 3: จัดการลูกค้า (Customers) ---
with tab3:
    st.subheader("เพิ่มลูกค้าใหม่")
    with st.form("add_cust_form"):
        new_cust_name = st.text_input("ชื่อลูกค้า")
        new_cust_addr = st.text_area("ที่อยู่")
        submitted = st.form_submit_button("บันทึกลูกค้า")
        
        if submitted and new_cust_name:
            new_cust_data = {
                'name': new_cust_name,
                'address': new_cust_addr,
                'owner': current_user # <--- 🔑 แปะชื่อเจ้าของ
            }
            st.session_state.db_customers = pd.concat([st.session_state.db_customers, pd.DataFrame([new_cust_data])], ignore_index=True)
            st.success(f"เพิ่มลูกค้า {new_cust_name} แล้ว")
            st.rerun()
            
    st.divider()
    st.write("รายชื่อลูกค้าของคุณ:")
    st.dataframe(my_customers[['name', 'address']], hide_index=True, use_container_width=True)
