from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os

# 註冊字型 (解決中文亂碼)
def register_fonts():
    font_dir = "fonts"
    try:
        pdfmetrics.registerFont(TTFont('NotoSans', os.path.join(font_dir, 'NotoSansTC-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('NotoSans-Bold', os.path.join(font_dir, 'NotoSansTC-Bold.ttf')))
    except:
        pass 

def create_quotation_pdf(data, show_stamp=True):
    register_fonts()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- 1. 頁首與 LOGO ---
    if os.path.exists("assets/LOGO.png"):
        c.drawImage("assets/LOGO.png", 30, height - 60, width=140, height=35, mask='auto')
    else:
        c.setFont("NotoSans-Bold", 18)
        c.drawString(30, height - 50, "士林電機 Shihlin Electric")

    c.setFont("NotoSans-Bold", 24)
    c.drawRightString(width - 30, height - 50, "報 價 單")
    
    c.setLineWidth(1)
    c.line(30, height - 70, width - 30, height - 70)

    # --- 2. 客戶與單號資訊 ---
    c.setFont("NotoSans", 11)
    text_y = height - 100
    c.drawString(30, text_y, f"客戶名稱：{data['client_name']}")
    c.drawString(30, text_y - 20, f"專案名稱：2401三菱PLC單次專案 (範例)") 
    
    c.drawString(350, text_y,     f"報價單號：{data['id']}")
    c.drawString(350, text_y - 20, f"報價日期：{data['date']}")
    c.drawString(350, text_y - 40, f"營 業 員：曾維崧") 

    # --- 3. 表格標題 ---
    table_y = height - 170
    c.setFillColor(colors.lightgrey)
    c.rect(30, table_y - 5, width - 60, 20, fill=1, stroke=0) 
    c.setFillColor(colors.black)
    
    c.setFont("NotoSans-Bold", 11)
    c.drawString(40, table_y, "項次")
    c.drawString(80, table_y, "品名 / 規格")
    c.drawString(320, table_y, "數量")
    c.drawString(380, table_y, "單價")
    c.drawString(480, table_y, "金額")
    
    # --- 4. 填入商品明細 ---
    y = table_y - 25
    c.setFont("NotoSans", 10)
    total_amount = 0
    
    for i, item in enumerate(data['items']):
        name = str(item['name'])
        try:
            price = float(item['price'])
            qty = int(item['qty'])
        except:
            price, qty = 0, 0
            
        subtotal = price * qty
        total_amount += subtotal
        
        # 換頁邏輯
        if y < 200: 
            c.drawString(width/2, 30, "- 接下頁 -")
            c.showPage()
            register_fonts()
            y = height - 50 
        
        c.drawString(40, y, str(i + 1))
        c.drawString(80, y, name) 
        c.drawString(320, y, str(qty))
        c.drawString(380, y, f"{price:,.0f}")
        c.drawString(480, y, f"{subtotal:,.0f}")
        c.line(30, y - 5, width - 30, y - 5)
        y -= 25

    # --- 5. 金額統計 (稅額計算) ---
    tax = total_amount * 0.05
    grand_total = total_amount + tax
    
    y -= 10
    c.setFont("NotoSans", 11)
    c.drawRightString(550, y, f"未稅金額合計： {total_amount:,.0f}")
    y -= 20
    c.drawRightString(550, y, f"營業稅 (5%)： {tax:,.0f}")
    y -= 20
    c.setFont("NotoSans-Bold", 12)
    c.drawRightString(550, y, f"報價金額總計： {grand_total:,.0f}")
    
    # --- 6. 頁尾條款與簽章 ---
    if y < 150:
        c.showPage()
        register_fonts()
        y = height - 50

    footer_y = 130
    c.setFont("NotoSans", 9)
    c.drawString(30, footer_y, "說明事項：")
    c.drawString(30, footer_y - 15, "1. 本報價單有效期限：15天。")
    c.drawString(30, footer_y - 30, "2. 交貨地點：國內卡車可達之地面，不含安裝。")
    
    # 蓋章區
    c.setFont("NotoSans-Bold", 10)
    c.drawString(350, footer_y, "士林電機廠股份有限公司")
    c.drawString(350, footer_y - 15, "負責人：許育瑞")
    c.drawString(350, footer_y - 30, "統一編號：11039306")
    
    if show_stamp and os.path.exists("assets/stamp.png"):
        c.drawImage("assets/stamp.png", 420, footer_y - 60, width=100, height=80, mask='auto')

    if os.path.exists("assets/qrcode.png"):
        c.drawImage("assets/qrcode.png", width - 80, 20, width=50, height=50)

    c.save()
    buffer.seek(0)
    return buffer