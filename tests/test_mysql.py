import pymysql

try:
    conn = pymysql.connect(
        host="kodama.proxy.rlwy.net",
        port=21117,
        user="root",
        password="NmqLxnCFOxTMKYMaWRMJFdeALYtdBPAu",
        database="railway",
        connect_timeout=30
    )

    print("CONNECTED")

    with conn.cursor() as c:
        c.execute("SHOW TABLES")
        print(c.fetchall())

except Exception as e:
    print("ERROR:", repr(e))
