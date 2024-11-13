import psycopg2
import dj_database_url
import time

db_conf = dj_database_url.config()

while True:
    try:
        conn = psycopg2.connect(
            database=db_conf.get('NAME'),
            host=db_conf.get('HOST'),
            user=db_conf.get('USER'),
            password=db_conf.get('PASSWORD'),
            port=db_conf.get('PORT'),
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        break

    except Exception as e:
        print('Database not available yet. Message:', e)
        print('Retrying...')
        time.sleep(2)
