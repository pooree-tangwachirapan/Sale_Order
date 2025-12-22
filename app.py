import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
import os

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Mobile Sale System", layout="centered")

# ชื่อไฟล์ Database (CSV)
FILE_ORDERS = "db_orders.csv"
FILE_CUSTOMERS = "db_customers.csv"
FILE_PRODUCTS = "db_products.csv"

# --- 2. HELPER FUNCTIONS (จัดการฐานข้อมูล) ---
def load_data(filename, columns):
    """โหลดข้อมูลจาก CSV ถ้าไม่มีไฟล์ให้สร้างใหม่"""
    if not os.path.exists(filename):
        df = pd.DataFrame(columns=columns)
        df.to_csv(filename, index=False)
        return df
    return pd.read_csv(filename)

def save_data(df, filename):
    """บันทึกข้อมูลลง CSV"""
    df.to_csv(filename, index=False)

# โหลดข้อมูลเข้า Session State
if 'data_loaded' not in st.session_state:
    st.session_state.df_orders = load_data(FILE_ORDERS, ['order_id', 'date', 'customer', 'items', 'total_price', 'owner', 'note'])
    st.session_state.df_customers = load_data(FILE_CUSTOMERS, ['name', 'address', 'phone', 'tax_id', 'owner'])
    st.session_state.df_products = load_data(FILE_PRODUCTS, ['sku', 'name', 'price'])
    
    # ถ้าสินค้ายังว่าง ให้ใส่ตัวอย่างไปก่อน
    if st.session_state.df_products.empty:
        sample_products = pd.DataFrame([
            ['P001', 'สินค้าตัวอย่าง A', 100],
            ['P002', 'สินค้าตัวอย่าง B', 250]
        ], columns=['sku', 'name', 'price'])
        st.session_state.df_products = pd.concat([st.session_state.df_products, sample_products], ignore_index=True)
        save_data(st.session_state.df_products, FILE_PRODUCTS)
    
    st.session_state.data_loaded = True

# --- 3. AUTHENTICATION (Login) ---
def check_login(username, password):
    users = {
        "sale01": "1234",
        "sale02": "1234",
        "admin": "admin"
    }
    return users.get(username) == password

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# หน้า Login
if not st.session_state.logged_in:
    st.markdown("## 🔐 เข้าสู่ระบบขาย (Mobile Sale)")
    with st.form("login"):
        usr = st.text_input("Username", placeholder="เช่น sale01")
        pwd = st.text_input("Password", type="password", placeholder="เช่น 1234")
        btn = st.form_submit_button("Login", type="primary")
        if btn:
            if check_login(usr, pwd):
                st.session_state.logged_in = True
                st.session_state.user = usr
                st.rerun()
            else:
                st.error("Username หรือ Password ผิดพลาด")
    st.stop()

# --- 4. PDF GENERATOR (ปรับปรุงสำหรับ fpdf2) ---
def create_pdf(order_data, items_df):
    pdf = FPDF()
    pdf.add_page()
    
    # *** ตรวจสอบฟอนต์ไทย ***
    font_path = 'THSarabunNew.ttf' 
    has_font = os.path.exists(font_path)
    
    if has_font:
        # fpdf2 ไม่ต้องใช้ uni=True
        pdf.add_font('THSarabunNew', '', font_path)
        pdf.add_font('THSarabunNew', 'B', font_path) # ใช้ไฟล์เดิมแทนตัวหนาไปก่อน
        pdf.set_font('THSarabunNew', '', 16)
    else:
        pdf.set_font('Helvetica', '', 12)
    
    # Header
    pdf.cell(0, 10, text=f"SALE ORDER / ใบสั่งขาย", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Customer Info
    pdf.cell(0, 8, text=f"NO: {order_data['order_id']}  |  Date: {order_data['date']}", align='R', new_x="LMARGIN", new_y="NEXT")
    
    if has_font:
        pdf.cell(0, 8, text=f"Customer: {order_data['customer']}", align='L', new_x="LMARGIN", new_y="NEXT")
        cust_info = st.session_state.df_customers[st.session_state.df_customers['name'] == order_data['customer']]
        if not cust_info.empty:
            address = cust_info.iloc[0]['address']
            pdf.multi_cell(0, 8, text=f"Address: {address}")
    else:
         pdf.cell(0, 8, text=f"Customer: {order_data['customer']} (Thai font missing)", align='L', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 10, "Description", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Price", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Total", border=1, align='C', fill=True, new_x="LMARGIN", new_y="NEXT")
    
    # Items
    total = 0
    for idx, row in items_df.iterrows():
        name = row['name']
        qty = row['qty']
        price = row['price']
        line_total = qty * price
        total += line_total
        
        pdf.cell(100, 10, text=f"{name}", border=1)
        pdf.cell(30, 10, text=f"{qty}", border=1, align='C')
        pdf.cell(30, 10, text=f"{price:,.0f}", border=1, align='R')
        pdf.cell(30, 10, text=f"{line_total:,.2f}", border=1, align='R', new_x="LMARGIN", new_y="NEXT")
        
    # Grand Total
    pdf.ln(5)
    if has_font:
        pdf.set_font('THSarabunNew', 'B', 16)
    else:
        pdf.set_font('Helvetica', 'B', 12)
    
    pdf.cell(160, 10, "GRAND TOTAL", border=0, align='R')
    pdf.cell(30, 10, f"{total:,.2f}", border=1, align='R', new_x="LMARGIN", new_y="NEXT")
    
    # Footer
    pdf.ln(20)
    if has_font:
        pdf.set_font('THSarabunNew', '', 16)
    else:
        pdf.set_font('Helvetica', '', 12)
        
    pdf.cell(90, 10, "____________________", align='C')
    pdf.cell(10, 10, "", align='C') # Space
    pdf.cell(90, 10, "____________________", align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(90, 5, "Authorized Signature", align='C')
    pdf.cell(10, 5, "", align='C') # Space
    pdf.cell(90, 5, "Customer Signature", align='C', new_x="LMARGIN", new_y="NEXT")

    # Output as bytes directly (fpdf2)
    return pdf.output()

# --- 5. MAIN APP UI ---
user = st.session_state.user
st.sidebar.title(f"👤 {user}")
if st.sidebar.button("Logout", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()

# กรองข้อมูลเฉพาะ User นี้ (Data Isolation)
my_customers = st.session_state.df_customers[st.session_state.df_customers['owner'] == user]
all_products = st.session_state.df_products 

tab_sale, tab_cust, tab_prod, tab_hist = st.tabs(["🛒 เปิดบิล", "👥 ลูกค้า", "📦 สินค้า", "📜 ประวัติ"])

# === TAB 1: เปิดบิล ===
with tab_sale:
    st.subheader("สร้างใบสั่งขายใหม่")
    
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    # 1. เลือกลูกค้า
    cust_list = my_customers['name'].tolist()
    selected_cust = st.selectbox("1. เลือกลูกค้า", [""] + cust_list)
    
    if selected_cust:
        cust_data = my_customers[my_customers['name'] == selected_cust].iloc[0]
        st.info(f"📍 {cust_data['address']} (โทร: {cust_data['phone']})")

    # 2. เลือกสินค้า
    st.write("---")
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        prod_name = st.selectbox("2. เลือกสินค้า", all_products['name'].tolist())
    with c2:
        qty = st.number_input("จำนวน", 1, 100, 1)
    with c3:
        st.write("")
        st.write("")
        add_btn = st.button("➕ เพิ่ม")

    if add_btn and prod_name:
        p_price = all_products[all_products['name'] == prod_name].iloc[0]['price']
        st.session_state.cart.append({'name': prod_name, 'qty': qty, 'price': p_price})
        st.toast(f"เพิ่ม {prod_name} แล้ว")

    # 3. สรุปรายการ
    if st.session_state.cart:
        st.write("---")
        cart_df = pd.DataFrame(st.session_state.cart)
        cart_df['Total'] = cart_df['qty'] * cart_df['price']
        
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        grand_total = cart_df['Total'].sum()
        st.metric("ยอดรวมสุทธิ", f"{grand_total:,.2f} บาท")
        
        note = st.text_area("หมายเหตุ", height=60)
        
        if st.button("✅ บันทึกและสร้าง PDF", type="primary", use_container_width=True):
            order_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{len(st.session_state.df_orders)+1:03d}"
            
            new_order = {
                'order_id': order_id,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'customer': selected_cust,
                'items': str(st.session_state.cart),
                'total_price': grand_total,
                'owner': user,
                'note': note
            }
            st.session_state.df_orders = pd.concat([st.session_state.df_orders, pd.DataFrame([new_order])], ignore_index=True)
            save_data(st.session_state.df_orders, FILE_ORDERS)
            
            try:
                # สร้าง PDF ด้วยฟังก์ชันใหม่
                pdf_bytes = create_pdf(new_order, cart_df)
                
                # แปลงเป็น Base64 โดยตรง (ไม่ต้อง encode 'latin-1')
                b64 = base64.b64encode(pdf_bytes).decode()
                
                st.success("บันทึกข้อมูลเรียบร้อย!")
                
                col_d, col_e = st.columns(2)
                with col_d:
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{order_id}.pdf" style="text-decoration:none;"><button style="width:100%;padding:10px;background:green;color:white;border:none;border-radius:5px;">📥 โหลด PDF</button></a>'
                    st.markdown(href, unsafe_allow_html=True)
                with col_e:
                    subject = f"ใบสั่งซื้อ {order_id}"
                    body = f"เรียน {selected_cust},%0D%0A%0D%0Aแนบใบสั่งซื้อ {order_id} ยอดรวม {grand_total:,.2f} บาท%0D%0A%0D%0Aขอบคุณครับ"
                    mail_href = f'<a href="mailto:?subject={subject}&body={body}" target="_blank" style="text-decoration:none;"><button style="width:100%;padding:10px;background:orange;color:white;border:none;border-radius:5px;">📧 ส่งอีเมล</button></a>'
                    st.markdown(mail_href, unsafe_allow_html=True)
                    
                st.session_state.cart = []
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")

# === TAB 2, 3, 4 (คงเดิม) ===
with tab_cust:
    st.subheader("จัดการลูกค้า")
    with st.expander("➕ เพิ่มลูกค้าใหม่"):
        with st.form("add_cust"):
            n_name = st.text_input("ชื่อลูกค้า/บริษัท")
            n_addr = st.text_area("ที่อยู่")
            n_phone = st.text_input("เบอร์โทร")
            n_tax = st.text_input("เลขผู้เสียภาษี")
            if st.form_submit_button("บันทึก"):
                new_c = pd.DataFrame([{
                    'name': n_name, 'address': n_addr, 'phone': n_phone, 
                    'tax_id': n_tax, 'owner': user
                }])
                st.session_state.df_customers = pd.concat([st.session_state.df_customers, new_c], ignore_index=True)
                save_data(st.session_state.df_customers, FILE_CUSTOMERS)
                st.success(f"เพิ่ม {n_name} แล้ว")
                st.rerun()
    st.dataframe(my_customers, hide_index=True, use_container_width=True)

with tab_prod:
    st.subheader("รายการสินค้า (ส่วนกลาง)")
    with st.expander("➕ เพิ่มสินค้าใหม่"):
        with st.form("add_prod"):
            p_sku = st.text_input("รหัสสินค้า (SKU)")
            p_name = st.text_input("ชื่อสินค้า")
            p_price = st.number_input("ราคา", 0.0)
            if st.form_submit_button("บันทึก"):
                new_p = pd.DataFrame([{'sku': p_sku, 'name': p_name, 'price': p_price}])
                st.session_state.df_products = pd.concat([st.session_state.df_products, new_p], ignore_index=True)
                save_data(st.session_state.df_products, FILE_PRODUCTS)
                st.success("บันทึกสินค้าแล้ว")
                st.rerun()
    st.dataframe(all_products, hide_index=True, use_container_width=True)

with tab_hist:
    st.subheader("ประวัติการขาย")
    my_orders = st.session_state.df_orders[st.session_state.df_orders['owner'] == user]
    my_orders = my_orders.sort_values(by='date', ascending=False)
    
    if not my_orders.empty:
        st.dataframe(my_orders[['order_id', 'date', 'customer', 'total_price']], hide_index=True, use_container_width=True)
        csv = my_orders.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Backup ประวัติการขาย (CSV)", csv, "my_sales_history.csv", "text/csv")
    else:
        st.info("ยังไม่มีรายการขาย")
