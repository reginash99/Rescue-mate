import psycopg
import dotenv
import os

dotenv.load_dotenv()


def insert_record(timestamp, transcription,status):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("insert into transcription (timestamp,final_transcription,successful_transcription) values (%s,%s,%s);",(timestamp, transcription,status,))
                conn.commit()
                print("inserted")
            else:
                print("table has to be created")
                

          
def delete_records():
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
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
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("select id, timestamp,final_transcription,successful_transcription from transcription order by id desc;")
                conn.commit()

                records = cur.fetchall()

                #create json from records
                json_data = []
                for row in records:
                    json_data.append({
                        'id': row[0],
                        'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                        'transcription': row[2],
                        'status': row[3]
                    })
    return json_data

def select_record(id):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("select * from transcription where id = %s;", (id,))
                conn.commit()

                records = cur.fetchall()
                row = records[0]
                #create json from records

                if not records:
                    return {}
                
                json_data = {
                        'id': row[0],
                        'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                        'transcription': row[2],
                        'status': row[3]
                    }
    return json_data

def get_id(timestamp, transcription,status):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("select id from transcription where timestamp = %s and final_transcription = %s and successful_transcription = %s;", (timestamp, transcription,status,))
                conn.commit()

                id = cur.fetchall()

                
    return id[0][0]

def get_latest_id():
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                cur.execute("select max(id) from transcription;")
                conn.commit()

                id = cur.fetchall()

                
    return id[0][0]    

def insert_intermediate_record(transcription, column_index,id):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:
         with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))

            match column_index:
                case 0:
                    cur.execute("update transcription set final_transcription = %s                      where id = %s", (transcription,id,))
                case 1:
                    cur.execute("update transcription set raw_transcr = %s                              where id = %s", (transcription,id,))
                case 2:
                    cur.execute("update transcription set bp_preemp_transcr = %s                        where id = %s", (transcription,id,))
                case 3:
                    cur.execute("update transcription set mamba_bp_transcr  = %s                        where id = %s", (transcription,id,))
                case 4:
                    cur.execute("update transcription set mamba_bp_preemp_transcr = %s                  where id = %s", (transcription,id,))
                case 5:
                    cur.execute("update transcription set mamba_bp_preemp_deepfilternet_transcrp = %s   where id = %s", (transcription,id,))
                case 6:
                    cur.execute("update transcription set bp_transcr = %s                               where id = %s", (transcription,id,))
                case _:
                    print("No valid column index provided.")
                    return
                
def create_new_record():
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:
         with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))

            cur.execute("insert into transcription (timestamp) values (now());")
            conn.commit()

# status is boolean: Either True or False
def set_success_status(id,status):
    print("status ", status)
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:
         with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))

            cur.execute("update transcription set successful_transcription = %s where id = %s", (status,id,))

def add_audio_path(id, path, path_flag):
     with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:
         with conn.cursor() as cur:
            match path_flag:
                case 0:
                    cur.execute("update transcription set input_audio_path = %s where id = %s", (path,id,))
                case 1:
                    cur.execute("update transcription set output_audio_path = %s where id = %s", (path,id,))

def select_intermediate_result(id, column_index):
    with psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    ) as conn:

        with conn.cursor() as cur:
            table_name = 'transcription'
            cur.execute("select exists(select from information_schema.tables where table_name=%s)",(table_name,))
            
     
            if cur.fetchone()[0]:
                print("table exists")
                match column_index:
                    case 0:
                        cur.execute("select final_transcription,successful_transcription from transcription where id = %s;", (id,))
                    case 1:
                        cur.execute("select raw_transcr,successful_transcription from transcription where id = %s;", (id,))
                    case 2:
                        cur.execute("select bp_preemp_transcr,successful_transcription from transcription where id = %s;", (id,))
                    case 3:
                        cur.execute("select mamba_bp_transcr,successful_transcription from transcription where id = %s;", (id,))
                    case 4:
                        cur.execute("select mamba_bp_preemp_transcr,successful_transcription from transcription where id = %s;", (id,))
                    case 5:
                        cur.execute("select mamba_bp_preemp_deepfilternet_transcrp,successful_transcription from transcription  where id = %s", (id,))
                    case 6:
                        cur.execute("select bp_transcr from transcription,successful_transcription                             where id = %s", (id,))
                    case _:
                        print("No valid column index provided.")
                        return
            return cur.fetchall()[0]
#insert_record('2025-09-07 00:12:00', 'This is a test transcription.',False) # just a test that the inserting function works
#delete_records()

#insert_intermediate_record('This is a test raw transcription to test the id.',1)