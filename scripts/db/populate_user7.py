import datetime
from config import get_db_connection

def populate():
    c = get_db_connection()
    cursor = c.cursor()
    cursor.execute('DELETE FROM ats_history WHERE user_id=7 AND ats_score!=36')
    for i, s in enumerate([45, 55, 68, 80, 92]):
        ts = datetime.datetime.now() - datetime.timedelta(days=10-i)
        cursor.execute('INSERT INTO ats_history (user_id, scan_type, ats_score, scan_timestamp) VALUES (7, "ATS_CHECKER", %s, %s)', (s, ts))
    c.commit()
    c.close()
    print('Done!')

if __name__ == '__main__':
    populate()
