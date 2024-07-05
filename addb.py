import sqlite3

# Kết nối tới database
conn = sqlite3.connect('database.db')
cur = conn.cursor()

# Xóa bảng notifications nếu tồn tại
cur.execute('DROP TABLE IF EXISTS login_activity')

# Lưu thay đổi và đóng kết nối
conn.commit()
conn.close()