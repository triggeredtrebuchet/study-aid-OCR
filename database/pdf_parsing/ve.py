import psycopg2
from fastapi import Depends
from psycopg2.extras import execute_values


class VectorEntry:
    def __init__(self, vector, chunk, user_id=None, pdf_id=None):
        self.id = None
        self.vector = vector
        self.text_chunk = chunk[0]
        self.user_id = user_id
        self.pdf_id = pdf_id
        self.page_number = chunk[1]

class Vector:
    id = None
    vector = None


class VectorDB:
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)

    def insert_entries(self, entries):
        """Bulk insert vector entries"""
        data = [
            (entry.vector, entry.text_chunk, entry.user_id, entry.pdf_id, entry.page_number)
            for entry in entries
        ]

        query = '''
        INSERT INTO embeddings (vector, text_chunk, user_id, pdf_id, page_number)
        VALUES %s
        RETURNING id
                '''
        with self.conn.cursor() as cursor:
            execute_values(cursor, query, data)
            returned_ids = [id for (id,) in cursor.fetchall()]

        self.conn.commit()
        return returned_ids