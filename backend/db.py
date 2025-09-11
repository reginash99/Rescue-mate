import psycopg
import dotenv
import os

dotenv.load_dotenv(dotenv_path="./.env")


def insert_record(timestamp, transcription):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("insert into transcription (timestamp,transcription) values (%s,%s);",(timestamp, transcription))
                conn.commit()
                print("inserted")
            else:
                print("table has to be created")
                

          


def delete_records():
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT")
    ) as conn:
        
        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("delete from transcription where timestamp < now() - interval '1 day';")
                conn.commit()
                print("deleted")
            else:
                print("table has to be created")
                

def select_records():
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        host=os.getenv("HOST"),
        port=os.getenv("PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("select * from transcription;")
                conn.commit()

                records = cur.fetchall()

                #create json from records
                json_data = []
                for row in records:
                    json_data.append({
                        'id': row[0],
                        'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                        'transcription': row[2]
                    })
    return json_data
    
#insert_record('2025-09-07 00:12:00', 'This is a test transcription.') # just a test that the inserting function works
#delete_records()