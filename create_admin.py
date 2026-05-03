from flask_bcrypt import Bcrypt
from flask import Flask
import pymysql

app = Flask(__name__)
bcrypt = Bcrypt(app)

password = bcrypt.generate_password_hash('admin123').decode('utf-8')
db = pymysql.connect(unix_socket='/tmp/mysql.sock', user='root', password='root123', database='bookease', cursorclass=pymysql.cursors.DictCursor)
with db.cursor() as cur:
    cur.execute('INSERT INTO users (name, email, password, is_admin) VALUES (%s, %s, %s, %s)', ('Admin', 'admin@bookease.com', password, 1))
db.commit()
db.close()
print('Admin created successfully!')