from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify,flash
import sqlite3
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from datetime import date
import zipfile
# import webview 

app = Flask(__name__)
def add_comma(num_str):
    if len(num_str) <= 3:
        return num_str

    num_str_reversed = num_str[::-1]
    parts = []

    # Process the first three digits
    parts.append(num_str_reversed[:3])

    # Process the remaining digits in groups of two
    for i in range(3, len(num_str_reversed), 2):
        parts.append(num_str_reversed[i:i+2])

    # Combine parts with commas and reverse back
    result = ','.join(parts)[::-1]
    return result

def number_to_words(num):
    under_20 = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 
                'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    above_100 = {100: 'Hundred', 1000: 'Thousand', 100000: 'Lakh', 10000000: 'Crore'}

    if num < 20:
        return under_20[num]

    if num < 100:
        return tens[num // 10 - 2] + ('' if num % 10 == 0 else ' ' + under_20[num % 10])
    pivot = max([key for key in above_100.keys() if key <= num])
    return number_to_words(num // pivot) + ' ' + above_100[pivot] + ('' if num % pivot == 0 else ' ' + number_to_words(num % pivot))

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a real secret key

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INTEGER PRIMARY KEY,
            name TEXT,
            account_no TEXT UNIQUE,
            bank_name TEXT,
            branch TEXT,
            ifsc_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM beneficiaries')
    beneficiaries = c.fetchall()
    conn.close()
    return render_template('index.html', beneficiaries=beneficiaries)

@app.route('/add_beneficiary', methods=['POST'])
def add_beneficiary():
    name = request.form.get('name', '')
    account_no = request.form.get('account_no', '')
    bank_name = request.form.get('bank_name', '')
    branch = request.form.get('branch', '')
    ifsc_code = request.form.get('ifsc_code', '')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO beneficiaries (name, account_no, bank_name, branch, ifsc_code) VALUES (?, ?, ?, ?, ?)',
                  (name, account_no, bank_name, branch, ifsc_code))
        conn.commit()
        flash('Beneficiary added successfully!', 'success')
    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Error: Account number already exists. Please use a unique account number.', 'error')
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete_beneficiary', methods=['POST'])
def delete_beneficiary():
    beneficiary_id = request.form['beneficiary_id']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM beneficiaries WHERE id = ?', (beneficiary_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/search_beneficiaries', methods=['POST'])
def search_beneficiaries():
    search_term = request.form['search_term']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, name, account_no, bank_name
        FROM beneficiaries
        WHERE name LIKE ? OR account_no LIKE ? OR bank_name LIKE ?
    ''', ('%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%'))
    results = c.fetchall()
    conn.close()
    
    return jsonify(results)

@app.route('/get_beneficiary_details', methods=['POST'])
def get_beneficiary_details():
    beneficiary_id = request.form['beneficiary_id']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM beneficiaries WHERE id = ?', (beneficiary_id,))
    beneficiary = c.fetchone()
    conn.close()
    
    if beneficiary:
        return jsonify({
            'id': beneficiary[0],
            'name': beneficiary[1],
            'account_no': beneficiary[2],
            'bank_name': beneficiary[3],
            'branch': beneficiary[4],
            'ifsc_code': beneficiary[5]
        })
    else:
        return jsonify({}), 404

@app.route('/generate_form', methods=['POST'])
def generate_form():
    beneficiary_id = request.form['beneficiary']
    amount = request.form['amount']
    amount_n = amount
    amount = add_comma(amount)
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM beneficiaries WHERE id = ?', (beneficiary_id,))
    beneficiary = c.fetchone()
    conn.close()
    
    amount_in_words = number_to_words(int(float(amount_n))) + " Rupees Only"
    if '.' in amount:
        decimal_part = amount.split('.')[1]
        if int(decimal_part) > 0:
            amount_in_words += " and " + number_to_words(int(decimal_part)) + " Paise"
    pass

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    background_path = "3.jpg"
    background = ImageReader(background_path)
    p.drawImage(background, 0, 0, width=width, height=height)
    today = date.today().strftime("%d/%m/%Y")
    p.drawString(430, 695, today)
    p.drawString(187, 645, f"41150083569") #sd
    p.drawString(190, 610, f"CA") #ac
    p.drawString(235, 580, f"{beneficiary[1]}") #Beneficiary Name
    p.setFont("Helvetica-Bold",14)
    p.drawString(235, 562, f"{beneficiary[2]}") #Ac no
    p.setFont("Helvetica",12)
    p.drawString(235, 545, f"{beneficiary[3]}") #Bank Name
    p.drawString(235, 527, f"{beneficiary[4]}")
    p.setFont("Helvetica-Bold",12)
    p.drawString(240, 505, f"{beneficiary[5]}") #IFSC Code
    p.setFont("Helvetica",10)
    p.drawString(180, 455, f"{amount_in_words}/-")
    p.setFont("Helvetica-Bold",12)
    p.drawString(300, 438, f"{amount}/-")
    p.drawString(300, 397, f"{amount}/-")
    p.setFont("Helvetica",12)
    p.drawString(150, 80, f"{beneficiary[1]}") #Beneficiary Name
    p.drawString(150, 62, f"{beneficiary[2]}") #Ac no
    p.drawString(150, 45, f"{beneficiary[3]}") #Bank Name
    p.drawString(150, 25, f"{beneficiary[4]}")
    p.save()
    buffer.seek(0)
    # return send_file(buffer, as_attachment=True, download_name=f'RTGS_for_{beneficiary[1]}_{amount}.pdf', mimetype='application/pdf')
    
    check_buffer = io.BytesIO()
    p_check = canvas.Canvas(check_buffer, pagesize=letter)
    # check_background_path = "2.jpg" 
    # check_background = ImageReader(check_background_path)
    # # Move the background image to the top of the page
    # p_check.drawImage(check_background, 0, letter[1] - 99*mm, width=210*mm, height=99*mm)
    p_check.setFont("Helvetica", 12)

    def draw_spaced_text(p, text, start_x, y, char_spacing):
        for char in text:
            if char == '/':
                continue
            p.drawString(start_x, y, char)
            start_x += char_spacing
    
    # p_check.saveState()
    p_check.setStrokeColorRGB(0, 0, 0)  
    p_check.setLineWidth(1)  
    p_check.line(10*mm, letter[1] - 7*mm, 50*mm, letter[1] - 7*mm)
    p_check.line(10*mm, letter[1] - 13*mm, 50*mm, letter[1] - 13*mm)
    p_check.setFont("Helvetica-Bold", 10)
    p_check.drawString(40, letter[1] - 11*mm, "AC PAYEE ONLY")
    # p_check.restoreState()
    
    
    p_check.setFont("Helvetica", 12)
    today = date.today().strftime("%d/%m/%Y")
    draw_spaced_text(p_check, today, 161*mm, letter[1] - 10*mm, 15)

# Adjust the y-coordinates for the payee name and amount in words
    # p_check.drawString(10, letter[1] - 5*mm, "AC PAYEE ONLY")
    p_check.drawString(20*mm, letter[1] - 24*mm, f"Y/S Pay {beneficiary[1]}")  # Payee Name
    p_check.setFont("Helvetica", 11)
    p_check.drawString(35*mm, letter[1] - 34*mm, f"{amount_in_words}/-")  # Amount in words
    p_check.setFont("Helvetica-Bold", 15)
# Adjust the y-coordinate for the amount in figures
    p_check.drawString(165*mm, letter[1] - 41*mm, f"{amount}/-")  # Amount in figures
    p_check.save()
    check_buffer.seek(0)
    # return send_file(check_buffer, as_attachment=True, download_name=f'cheque_for_{beneficiary[1]}_{amount}.pdf', mimetype='application/pdf')
    back_buffer = io.BytesIO()
    p_back = canvas.Canvas(back_buffer, pagesize=letter)
    p_back.setFont("Helvetica-Bold", 15)        
    p_back.drawString(75*mm, letter[1] - 24*mm, f"Pay To {beneficiary[1]}")  # Payee Name
    p_back.save()
    back_buffer.seek(0)
    # return send_file(back_buffer, as_attachment=True, download_name=f'cheque_for_{beneficiary[1]}_{amount}.pdf', mimetype='application/pdf')
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        zipf.writestr('RTGS_NEFT_Form.pdf', buffer.getvalue())
        zipf.writestr('SBI_Check.pdf', check_buffer.getvalue())
        zipf.writestr('SBI_Check_back.pdf', back_buffer.getvalue())
    zip_buffer.seek(0)

    return send_file(zip_buffer, as_attachment=True, download_name=f"RTGS_for_{beneficiary[1]}_{amount}.zip", mimetype='application/zip')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    # webview.start()