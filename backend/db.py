import psycopg
import dotenv
import os

dotenv.load_dotenv()

DB_Name = os.getenv("DB_NAME")
DB_User=os.getenv("DB_USER")
DB_Password=os.getenv("DB_PASSWORD")
DB_Host=os.getenv("DB_HOST")
DB_Port=os.getenv("DB_PORT")

          
def delete_records():
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:
        
        with conn.cursor() as cur:

            cur.execute(
                "create temporary table delete_transcriptions (id int, input_audio_path text, output_audio_path text);" \
                "insert into delete_transcriptions (id, input_audio_path, output_audio_path) " \
                "select id,input_audio_path,output_audio_path from transcription where timestamp <= now() - interval '1 day' order by id desc;"
            )
           
            cur.execute("select * from delete_transcriptions")
            records = cur.fetchall()

            cur.execute("delete from transcription where id in (select id from delete_transcriptions)"
            )
        
            return records
                

def select_records():
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:

        with conn.cursor() as cur:
            
                cur.execute("select id, timestamp,final_transcription,successful_transcription,raw_transcr from transcription order by id desc;")
                records = cur.fetchall()

                #provide records for json-conversion
                json_data = []
                for row in records:
                    json_data.append({
                        'id': row[0],
                        'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                        'transcription': row[2],
                        'status': row[3],
                        'raw_transcription': row[4]
                    })
    return json_data

def select_transcriptions(id):
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:

        with conn.cursor() as cur:
           
            cur.execute("select final_transcription, raw_transcr,bp_preemp_transcr, mamba_bp_transcr, "\
                        "mamba_bp_preemp_transcr, mamba_bp_preemp_deepfilternet_transcr, bp_transcr,timestamp from transcription where id = %s;", (id,))
            
            sql_results = cur.fetchall()
            

            results = []
            for result in sql_results:
                results.append({
                    'final_transcription': result[0],
                    'raw_transcr': result[1],
                    'bp_preemp_transcr': result[2],
                    'mamba_bp_transcr': result[3],
                    'mamba_bp_preemp_transcr': result[4],
                    'mamba_bp_preemp_deepfilternet_transcr': result[5],
                    'bp_transcr': result[6],
                    'timestamp': result[7].strftime("%d.%m.%Y  %H:%M:%S"),
                    'id': id
                })
        return results
    

def select_record(id):
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:

        with conn.cursor() as cur:
            
            cur.execute("select * from transcription where id = %s;", (id,))

            row = cur.fetchone()
            #create json from records

            if not row:
                return {}
            else:

                json_data = {
                    'id': row[0],
                    'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                    'transcription': row[2],
                    'status': row[3]
                    }
    return json_data



def get_latest_id():
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:

        with conn.cursor() as cur:
            

            cur.execute("select max(id) from transcription;")


            id = cur.fetchone()
            if id is None:
                return -1
                
    return id[0]   

def insert_intermediate_record(transcription, column_index,id):
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:
         with conn.cursor() as cur:
            

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
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:
         with conn.cursor() as cur:
            
            cur.execute("insert into transcription (timestamp) values (now());")


# status is boolean: Either True or False
def set_success_status(id,status):  
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:
         with conn.cursor() as cur:
            
            cur.execute("update transcription set successful_transcription = %s where id = %s", (status,id,))

def add_audio_path(id, path, path_flag):
     with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:
         with conn.cursor() as cur:
            match path_flag:
                case 0:
                    cur.execute("update transcription set input_audio_path = %s where id = %s", (path,id,))
                case 1:
                    cur.execute("update transcription set output_audio_path = %s where id = %s", (path,id,))

def select_intermediate_result(id, column_index):
    with psycopg.connect(
        dbname=DB_Name,
        user=DB_User,
        password=DB_Password,
        host=DB_Host,
        port=DB_Port
    ) as conn:

        with conn.cursor() as cur:
           
            match column_index:
                case 0:
                    cur.execute("select final_transcription,successful_transcription from transcription where id = %s;", (id,))
                case 1:
                    cur.execute("select raw_transcr, timestamp from transcription where id = %s;", (id,))
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
                    

            row = cur.fetchone()
            
            #create json from records

            if not row:
                return {}

            json_data = {
                    'id': id,
                    'timestamp': row[1].strftime("%d.%m.%Y  %H:%M:%S"),
                    'transcription': row[0],
                }
            
            return json_data



    