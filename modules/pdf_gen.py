from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# 註冊字型
def register_fonts():
    font_dir = "fonts"
    try:
        # 嘗試註冊一般體與粗體
        pdfmetrics.registerFont(TTFont('NotoSans', os.path.join(font_dir, 'NotoSansTC-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('NotoSans-Bold', os.path.join(font_dir, 'NotoSansTC-Bold.ttf')))
    except Exception as e:
        print(f"Font Error: {e}")

def create_quotation_pdf(data, show_stamp=True):
    register_fonts()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 設定字型
    c.setFont("NotoSans-Bold", 24)
    
    # 1. 標題與 LOGO
    # c.drawImage("assets/LOGO.png", 30, height - 70, width=120, height=30, mask='auto') # 暫時註解，避免您沒放圖檔報錯
    c.drawString(30, height - 50, "士林電機 - 報價單")
    
    # 2. 客戶資訊
    c.setFont("NotoSans", 12)
    c.drawString(30, height - 90, f"報價單號: {data['id']}")
    c.drawString(300, height - 90, f"日期: {data['date']}")
    c.drawString(30, height - 110, f"客戶名稱: {data['client_name']}")
    
    # 3. 表格線條
    y = height - 140
    c.line(30, y, 550, y)
    c.drawString(30, y + 5, "品名")
    c.drawString(300, y + 5, "單價")
    c.drawString(400, y + 5, "數量")
    c.drawString(480, y + 5, "小計")
    
    # 4. 填入商品
    total = 0
    for item in data['items']:
        y -= 25
        name = str(item['name'])
        price = float(item['price'])
        qty = int(item['qty'])
        subtotal = price * qty
        total += subtotal
        
        c.drawString(30, y, name)
        c.drawString(300, y, f"{price:,.0f}")
        c.drawString(400, y, f"{qty}")
        c.drawString(480, y, f"{subtotal:,.0f}")
        
    # 5. 總計與印章
    y -= 40
    c.line(30, y+30, 550, y+30)
    c.setFont("NotoSans-Bold", 14)
    c.drawString(400, y, f"總計: {total:,.0f} 元")
    
    if show_stamp:
        try:
            c.drawImage("assets/stamp.png", 400, y-50, width=100, height=80, mask='auto')
        except:
            pass # 沒圖就不畫
            
    c.save()
    buffer.seek(0)
    return buffer