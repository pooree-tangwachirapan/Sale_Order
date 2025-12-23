import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
from github import Github
import io
import os

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Mobile Sale System (GitDB)", layout="centered")

# ชื่อไฟล์ Database
FILE_ORDERS = "db_orders.csv"
FILE_CUSTOMERS = "db_customers.csv"
FILE_PRODUCTS = "db_products.csv"

# --- 2. GITHUB CONNECTION HELPER ---
def get_github_repo():
    """เชื่อมต่อ GitHub โดยใช้ Token จาก Secrets"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["GITHUB_REPO"]
        g = Github(token)
        return g.get_repo(repo_name)
    except Exception as e:
        st.error(f"เชื่อมต่อ GitHub ไม่สำเร็จ: {e}")
        st.stop()

def load_data_from_github(filename, columns):
    """ดึงไฟล์ CSV จาก GitHub"""
    repo = get_github_repo()
    try:
        # พยายามโหลดไฟล์
        contents = repo.get_contents(filename)
        decoded = contents.decoded_content.decode("utf-8")
        return pd.read_csv(io.StringIO(decoded))
    except:
        # ถ้าไม่มีไฟล์ ให้ส่งกลับเป็น DataFrame ว่างๆ
        return pd.DataFrame(columns=columns)

def save_data_to_github(df, filename, message="Update data"):
    """บันทึก DataFrame ทับไฟล์บน GitHub"""
    repo = get_github_repo()
    csv_content = df.to_csv(index=False)
    
    try:
        # เช็คว่ามีไฟล์เดิมไหม เพื่อดึง SHA (ID ไฟล์) มาอ้างอิง
        contents = repo.get_contents(filename)
        repo.update_file(contents.path, message, csv_content, contents.sha)
    except:
        # ถ้าไม่มีไฟล์เดิม ให้สร้างใหม่
        repo.create_file(filename, message, csv_content)

# --- โหลดข้อมูลเข้า Session State (ครั้งแรกครั้งเดียว) ---
if 'data_loaded' not in st.session_state:
    with st.spinner('กำลังดึงข้อมูลจาก GitHub...'):
        st.session_state.df_orders = load_data_from_github(FILE_ORDERS, ['order_id', 'date', 'customer', 'items', 'total_price', 'owner', 'note'])
        st.session_state.df_customers = load_data_from_github(FILE_CUSTOMERS, ['name', 'address', 'phone', 'tax_id', 'owner'])
        st.session_state.df_products = load_data_from_github(FILE_PRODUCTS, ['sku', 'name', 'price'])
        
        # ใส่ข้อมูลตัวอย่างถ้าสินค้าว่าง
        if st.session_state.df_products.empty:
            sample = pd.DataFrame([['P01', 'สินค้าทดสอบ', 100]], columns=['sku', 'name', 'price'])
            st.session_state.df_products = pd.concat([st.session_state.df_products, sample], ignore_index=True)
            # บันทึกตัวอย่างขึ้น GitHub ทันที
            save_data_to_github(st.session_state.df_products, FILE_PRODUCTS, "Init products")
            
        st.session_state.data_loaded = True

# --- 3. AUTHENTICATION (Login) ---
def check_login(username, password):
    users = {"sale01": "1234", "sale02": "1234", "admin": "admin"}
    return users.get(username) == password

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    st.markdown("## 🔐 เข้าสู่ระบบ (GitHub DB Mode)")
    with st.form("login"):
        usr = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login", type="primary"):
            if check_login(usr, pwd):
                st.session_state.logged_in = True
                st.session_state.user = usr
                st.rerun()
            else:
                st.error("Login ผิดพลาด")
    st.stop()

# --- 4. PDF GENERATOR ---
# ค้นหาบรรทัด def create_pdf(order_data, items_df): แล้วแก้ไส้ในทั้งหมดเป็นแบบนี้ครับ

def create_pdf(order_data, items_df):
    pdf = FPDF()
    pdf.add_page()
    
    # --- ส่วนจัดการฟอนต์ (แก้ไขใหม่) ---
    font_path = 'THSarabunNew.ttf'  # ต้องตรงกับชื่อไฟล์ใน GitHub เป๊ะๆ
    
    # เช็คว่ามีไฟล์ฟอนต์จริงไหม
    if os.path.exists(font_path):
        pdf.add_font('THSarabunNew', '', font_path)
        pdf.add_font('THSarabunNew', 'B', font_path)
        pdf.set_font('THSarabunNew', '', 16)
        has_font = True
    else:
        # ถ้าหาไฟล์ไม่เจอ ให้ใช้ฟอนต์อังกฤษ และแจ้งเตือนใน PDF
        pdf.set_font('Helvetica', '', 12)
        has_font = False
        st.error("ไม่พบไฟล์ฟอนต์ THSarabunNew.ttf ใน GitHub! ภาษาไทยจะไม่แสดง")

    # --- Header ---
    # ใช้ text=... เพื่อความปลอดภัยใน fpdf2
    pdf.cell(0, 10, text=f"SALE ORDER: {order_data['order_id']}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # --- Customer Info ---
    # ถ้าไม่มีฟอนต์ไทย ต้องแปลงชื่อลูกค้าเป็นอังกฤษ หรือเว้นว่างไว้เพื่อกัน Error
    cust_name = order_data['customer']
    if not has_font:
        # ถ้าไม่มีฟอนต์ไทยแต่ชื่อเป็นไทย โปรแกรมจะ Error ตรงนี้ ดังนั้นต้องดักไว้
        try:
            cust_name.encode('latin-1') # ลองทดสอบว่าเป็นอังกฤษล้วนไหม
        except UnicodeEncodeError:
            cust_name = "Customer Name (Thai Font Missing)" # ถ้าเป็นไทย ให้เปลี่ยนข้อความแทน
            
    pdf.cell(0, 8, text=f"Customer: {cust_name}", align='L', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # --- Items ---
    total = 0
    # Header ตาราง
    pdf.cell(100, 10, "Item", border=1)
    pdf.cell(30, 10, "Qty", border=1)
    pdf.cell(40, 10, "Price", border=1, new_x="LMARGIN", new_y="NEXT")
    
    for idx, row in items_df.iterrows():
        total += row['qty'] * row['price']
        
        # จัดการชื่อสินค้า (เผื่อเป็นภาษาไทย)
        item_name = str(row['name'])
        if not has_font:
             try:
                item_name.encode('latin-1')
             except UnicodeEncodeError:
                item_name = "Item (Thai Font Missing)"

        pdf.cell(100, 10, text=item_name, border=1)
        pdf.cell(30, 10, text=str(row['qty']), border=1)
        pdf.cell(40, 10, text=f"{row['price']}", border=1, new_x="LMARGIN", new_y="NEXT")
        
    # Grand Total
    pdf.cell(130, 10, "Total", border=1)
    pdf.cell(40, 10, f"{total:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()

# --- 5. MAIN UI ---
user = st.session_state.user
st.sidebar.write(f"User: {user}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# แยกแท็บ
tab1, tab2, tab3 = st.tabs(["🛒 ขาย", "👥 ลูกค้า", "📦 สินค้า"])

# --- Tab 1: ขาย ---
with tab1:
    st.subheader("เปิดบิลขาย")
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    # เลือกลูกค้าของตัวเอง
    my_cust = st.session_state.df_customers[st.session_state.df_customers['owner'] == user]
    cust_name = st.selectbox("ลูกค้า", [""] + my_cust['name'].tolist())
    
    # เลือกสินค้า
    prod_name = st.selectbox("สินค้า", st.session_state.df_products['name'].tolist())
    qty = st.number_input("จำนวน", 1, 100, 1)
    
    if st.button("เพิ่มรายการ"):
        p_price = st.session_state.df_products[st.session_state.df_products['name'] == prod_name].iloc[0]['price']
        st.session_state.cart.append({'name': prod_name, 'qty': qty, 'price': p_price})
        st.success("เพิ่มแล้ว")
    
    # แสดงตารางตะกร้า
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df)
        grand_total = (cart_df['qty'] * cart_df['price']).sum()
        st.write(f"ยอดรวม: {grand_total:,.2f}")
        
        if st.button("✅ บันทึกเข้า GitHub (ใช้เวลา 2-3 วิ)"):
            with st.spinner("กำลังบันทึกข้อมูลถาวรบน GitHub..."):
                # เตรียมข้อมูล
                new_id = f"INV-{len(st.session_state.df_orders)+1}"
                new_order = {
                    'order_id': new_id,
                    'date': str(datetime.now()),
                    'customer': cust_name,
                    'items': str(st.session_state.cart),
                    'total_price': grand_total,
                    'owner': user,
                    'note': ''
                }
                
                # 1. อัปเดต State
                st.session_state.df_orders = pd.concat([st.session_state.df_orders, pd.DataFrame([new_order])], ignore_index=True)
                
                # 2. บันทึกลง GitHub จริงๆ (เขียนไฟล์ db_orders.csv)
                save_data_to_github(st.session_state.df_orders, FILE_ORDERS, f"New order {new_id}")
                
                # 3. สร้าง PDF
                pdf_bytes = create_pdf(new_order, cart_df)
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="{new_id}.pdf">📥 ดาวน์โหลด PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                st.session_state.cart = [] # เคลียร์ตะกร้า
                st.success("บันทึกสำเร็จ! ข้อมูลอยู่บน GitHub แล้ว")

# --- Tab 2: ลูกค้า ---
with tab2:
    with st.form("new_cust"):
        c_name = st.text_input("ชื่อลูกค้า")
        c_addr = st.text_input("ที่อยู่")
        if st.form_submit_button("บันทึกลูกค้า"):
            new_c = pd.DataFrame([{'name': c_name, 'address': c_addr, 'phone': '', 'tax_id': '', 'owner': user}])
            st.session_state.df_customers = pd.concat([st.session_state.df_customers, new_c], ignore_index=True)
            
            # Save to GitHub
            with st.spinner("กำลังบันทึก..."):
                save_data_to_github(st.session_state.df_customers, FILE_CUSTOMERS, f"Add customer {c_name}")
            st.success("เพิ่มลูกค้าเรียบร้อย")
            st.rerun()

# --- Tab 3: สินค้า ---
with tab3:
    st.dataframe(st.session_state.df_products)
    with st.form("new_prod"):
        p_sku = st.text_input("SKU")
        p_name = st.text_input("ชื่อสินค้า")
        p_price = st.number_input("ราคา", 0.0)
        if st.form_submit_button("เพิ่มสินค้า"):
            new_p = pd.DataFrame([{'sku': p_sku, 'name': p_name, 'price': p_price}])
            st.session_state.df_products = pd.concat([st.session_state.df_products, new_p], ignore_index=True)
            
            # Save to GitHub
            with st.spinner("กำลังบันทึก..."):
                save_data_to_github(st.session_state.df_products, FILE_PRODUCTS, f"Add product {p_name}")
            st.success("เพิ่มสินค้าเรียบร้อย")
            st.rerun()


