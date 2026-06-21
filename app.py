from flask import *
import sqlite3
import os
import cv2
import numpy as np
import qrcode
import random
import zipfile
from cryptography.fernet import Fernet
from flask import send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import os

def load_key():

    key=os.getenv("FERNET_KEY")

    return key.encode()

def encrypt_file(filepath):

    key = load_key()

    cipher = Fernet(key)

    with open(filepath, "rb") as file:
        data = file.read()

    encrypted_data = cipher.encrypt(data)

    filename = os.path.basename(filepath)

    encrypted_path = os.path.join(
        "encrypted_images",
        filename + ".enc"
    )

    with open(encrypted_path, "wb") as file:
        file.write(encrypted_data)

    return encrypted_path
def decrypt_file(encrypted_path, output_path):

    key = load_key()

    cipher = Fernet(key)

    with open(encrypted_path, "rb") as file:
        encrypted_data = file.read()

    decrypted_data = cipher.decrypt(encrypted_data)

    with open(output_path, "wb") as file:
        file.write(decrypted_data)
def save_log(user_id, action, filename=""):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO activity_logs
        (user_id, action, filename)

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            action,
            filename
        )
    )

    conn.commit()
    conn.close()
app = Flask(__name__)
os.makedirs(
    "encrypted_images",
    exist_ok=True
)

os.makedirs(
    "backups",
    exist_ok=True
)

os.makedirs(
    "static/uploads",
    exist_ok=True
)

os.makedirs(
    "static/enhanced",
    exist_ok=True
)

os.makedirs(
    "static/segmented",
    exist_ok=True
)

os.makedirs(
    "static/qr",
    exist_ok=True
)
# 5 MB upload limit
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

import os

app.secret_key=os.getenv(
    "SECRET_KEY",
    "secureproject123"
)
@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (fullname,username,email,password)
                VALUES(?,?,?,?)
                """,
                (
                    fullname,
                    username,
                    email,
                    hashed_password
                )
            )

            conn.commit()

            return redirect('/login')
        except Exception as e:
            return str(e)

        

    return render_template('register.html')
@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()

        if user:

            if check_password_hash(
                user[4],
                password
            ):

                session['user_id'] = user[0]
                session['username'] = user[2]
                session['role'] = user[5]
                session.pop('current_image', None)

                return redirect('/dashboard')

        return "Invalid Login"

    return render_template('login.html')
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT filename
        FROM images
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session['user_id'],)
    )

    images = cursor.fetchall()
    current_image = session.get('current_image')

    return render_template(
        'dashboard.html',
        username=session['username'],
        current_image=current_image
    )

    
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/upload', methods=['POST'])
def upload():

    if 'user_id' not in session:
        return redirect('/login')

    file = request.files['image']

    if file:

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        file.save(filepath)

        # Encrypt uploaded image
        encrypt_file(filepath)

        session['current_image'] = filename

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO images
            (user_id, filename)
            VALUES (?,?)
            """,
            (
                session['user_id'],
                filename
            )
        )

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return "Upload Failed"
@app.route('/enhance/<filename>', methods=['GET', 'POST'])
def enhance(filename):

    original_path = os.path.join(
        'static/uploads',
        filename
    )

    enhanced_path = os.path.join(
        'static/enhanced',
        'enhanced_' + filename
    )

    if request.method == 'POST':

        brightness = int(
            request.form['brightness']
        )

        contrast = float(
            request.form['contrast']
        )

        blur = int(
            request.form['blur']
        )
        sharpness = float(
            request.form['sharpness']
        )

        saturation = float(
             request.form['saturation']
        )

        pixelation = int(
            request.form['pixelation']
        )

        image = cv2.imread(original_path)

        enhanced = cv2.convertScaleAbs(
            image,
            alpha=contrast,
            beta=brightness
        )
        hsv = cv2.cvtColor(
            enhanced,
            cv2.COLOR_BGR2HSV
        )

        hsv[:,:,1] = np.clip(
            hsv[:,:,1] * saturation,
            0,
            255
        )

        enhanced = cv2.cvtColor(
            hsv,
            cv2.COLOR_HSV2BGR
        )
        if sharpness > 1:

            kernel = np.array([
                [0,-1,0],
                [-1,5,-1],
                [0,-1,0]
            ])

            for i in range(int(sharpness)):

                enhanced = cv2.filter2D(
                enhanced,
                -1,
                kernel
            )
        if pixelation > 1:

            h, w = enhanced.shape[:2]

            temp = cv2.resize(
                enhanced,
                (
                    max(1, w // pixelation),
                    max(1, h // pixelation)
                ),
                interpolation=cv2.INTER_LINEAR
            )

            enhanced = cv2.resize(
                temp,
                (w, h),
                interpolation=cv2.INTER_NEAREST
            )

        if blur > 0:

            k = blur * 2 + 1

            enhanced = cv2.GaussianBlur(
                enhanced,
                (k, k),
                0
            )

        cv2.imwrite(
            enhanced_path,
            enhanced
        )

        return render_template(
            'enhance.html',
            filename=filename,
            original_image=original_path,
            enhanced_image=enhanced_path
        )

    return render_template(
        'enhance.html',
        filename=filename,
        original_image=original_path
    )
@app.route('/segment/<filename>', methods=['GET', 'POST'])
def segment(filename):

    enhanced_path = os.path.join(
        'static/enhanced',
        'enhanced_' + filename
    )

    segmented_path = os.path.join(
        'static/segmented',
        'segmented_' + filename
    )

    if request.method == 'POST':

        method = request.form['method']

        image = cv2.imread(enhanced_path)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        if method == "otsu":

            _, segmented = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY +
                cv2.THRESH_OTSU
            )

        elif method == "edge":

            segmented = cv2.Canny(
                gray,
                100,
                200
            )

        cv2.imwrite(
            segmented_path,
            segmented
        )

        return render_template(
            'segment.html',
            filename=filename,
            enhanced_image=enhanced_path,
            segmented_image=segmented_path
        )

    return render_template(
        'segment.html',
        filename=filename,
        enhanced_image=enhanced_path
    )
@app.route('/generate_qr/<filename>')
def generate_qr(filename):

    image_id = "IMG" + str(
        random.randint(
            100000,
            999999
        )
    )

    otp = str(
        random.randint(
            100000,
            999999
        )
    )

    access_url = (
        f"http://127.0.0.1:5000/access/{image_id}"
    )

    qr = qrcode.make(
        access_url
    )

    qr_path = os.path.join(
        'static/qr',
        image_id + '.png'
    )

    qr.save(qr_path)

    conn = sqlite3.connect(
        "database.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO image_access
        (
            image_id,
            otp,
            filename
        )
        VALUES (?,?,?)
        """,
        (
            image_id,
            otp,
            filename
        )
    )

    conn.commit()

    return render_template(
        'qr.html',
        image_id=image_id,
        otp=otp,
        qr_image=qr_path,
        filename=filename
    )
@app.route(
    '/access/<image_id>',
    methods=['GET','POST']
)
def access(image_id):

    conn = sqlite3.connect(
        "database.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT otp,
               filename
        FROM image_access
        WHERE image_id=?
        """,
        (image_id,)
    )

    data = cursor.fetchone()

    if not data:

        return "Invalid QR"

    correct_otp = data[0]

    filename = data[1]

    if request.method == 'POST':

        entered_otp = request.form['otp']

        if entered_otp == correct_otp:

            return render_template(
                'view_image.html',
                filename=filename
            )

        return "Wrong OTP"

    return render_template(
        'verify.html',
        image_id=image_id
    )
@app.route('/enhancement')
def enhancement_page():

    filename = session.get('current_image')

    if not filename:
        return redirect('/dashboard')

    return redirect(f'/enhance/{filename}')
@app.route('/segmentation')
def segmentation_page():

    filename = session.get('current_image')

    if not filename:
        return redirect('/dashboard')

    return redirect(f'/segment/{filename}')
@app.route('/qr_otp')
def qr_otp_page():

    filename = session.get('current_image')

    if not filename:
        return redirect('/dashboard')

    return redirect(f'/generate_qr/{filename}')
@app.route('/download_zip/<filename>')
def download_zip(filename):

    zip_path = f"static/zip/{filename}.zip"

    with zipfile.ZipFile(zip_path, 'w') as zipf:

        upload_file = f"static/uploads/{filename}"

        enhanced_file = f"static/enhanced/enhanced_{filename}"

        segmented_file = f"static/segmented/segmented_{filename}"

        qr_file = f"static/qr/qr_{filename}.png"

        if os.path.exists(upload_file):
            zipf.write(upload_file)

        if os.path.exists(enhanced_file):
            zipf.write(enhanced_file)

        if os.path.exists(segmented_file):
            zipf.write(segmented_file)

        if os.path.exists(qr_file):
            zipf.write(qr_file)

    return send_file(
        zip_path,
        as_attachment=True
    )
@app.route('/history')
def history():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute(
    """
    SELECT filename,
           action,
           created_at

    FROM history

    WHERE user_id=?

    ORDER BY created_at DESC
    """,
    (session['user_id'],)
    )

    data = cursor.fetchall()

    return render_template(
        'history.html',
        data=data
    )
@app.route('/backup')
def backup():

    if session.get('role') != 'admin':
        return "Access Denied"

    # Create backup folder if it doesn't exist
    os.makedirs("backup_storage", exist_ok=True)

    backup_path = os.path.join(
        "backup_storage",
        "system_backup.zip"
    )

    with zipfile.ZipFile(
        backup_path,
        'w',
        zipfile.ZIP_DEFLATED
    ) as backup_zip:

        # Database
        if os.path.exists("database.db"):
            backup_zip.write("database.db")

        folders = [
            "encrypted_images",
            "static/uploads",
            "static/enhanced",
            "static/segmented",
            "static/qr"
        ]

        for folder in folders:

            if os.path.exists(folder):

                for root, dirs, files in os.walk(folder):

                    for file in files:

                        file_path = os.path.join(
                            root,
                            file
                        )

                        backup_zip.write(file_path)

    return send_file(
        os.path.abspath(backup_path),
        as_attachment=True,
        download_name="system_backup.zip"
    )
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route('/')
def home():
    return render_template('index.html')
if __name__ == '__main__':
    app.run()
