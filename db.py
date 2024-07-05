import sqlite3
from datetime import datetime, timedelta
import random

# # Kết nối đến cơ sở dữ liệu SQLite
# conn = sqlite3.connect('database.db')
# cur = conn.cursor()

# # Lấy danh sách các email từ bảng users (giả sử đã có bảng users)
# cur.execute('SELECT username FROM users')
def get_login_data(filter_type='month'):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    if filter_type == 'month':
        today = datetime.now()
        first_day_of_this_month = today.replace(day=1)
        last_day_of_prev_month = first_day_of_this_month - timedelta(days=1)
        first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
        cur.execute('''
            SELECT email, login_time, logout_time FROM login_activity 
            WHERE login_time >= ? AND login_time <= ?
        ''', (first_day_of_prev_month.strftime('%Y-%m-%d 00:00:00'), last_day_of_prev_month.strftime('%Y-%m-%d 23:59:59')))
    else:
        cur.execute('SELECT email, login_time, logout_time FROM login_activity')
    
    login_activities = cur.fetchall()
    
    daily_login_counts = {}
    total_duration = 0
    count = 0
    
    for activity in login_activities:
        login_time = datetime.strptime(activity[1], '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.strptime(activity[2], '%Y-%m-%d %H:%M:%S')
        duration = (logout_time - login_time).total_seconds()
        
        date_str = login_time.strftime('%Y-%m-%d')
        if date_str not in daily_login_counts:
            daily_login_counts[date_str] = 0
        daily_login_counts[date_str] += 1
        
        total_duration += duration
        count += 1
    
    avg_login_duration = total_duration / count if count > 0 else 0

    conn.close()
    print('daily_login_counts', daily_login_counts,'avg_login_duration', avg_login_duration)
    
get_login_data(filter_type='month')
# conn.commit()
# conn.close()

print('Dữ liệu mẫu cho tháng 4 năm 2024 đã được thêm vào bảng login_activity.')