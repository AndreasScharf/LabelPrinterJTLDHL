import pyodbc
from dotenv import load_dotenv
import os
from contextlib import contextmanager

class MSSQLDatabase:
    def __init__(self, server=None, database=None, username=None, password=None, port=1433):
        self.connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};DATABASE={database};UID={username};PWD={password}"
        self.connection = None

    def connect(self):
        try:
            self.connection = pyodbc.connect(self.connection_string)
            print("Connection to MSSQL database successful.")
            return True
        except pyodbc.Error as e:
            print(f"Error connecting to MSSQL database: {e}")
            return False

    def execute_query(self, query, params=None):
        if self.connection is None:
            raise Exception("Database connection is not established.")
        try:
            with self.connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.connection.commit()
                print("Query executed successfully.")
        except pyodbc.Error as e:
            print(f"Error executing query: {e}")
            raise

    def fetch_results(self, query, params=None):
        if self.connection is None:
            raise Exception("Database connection is not established.")
        try:
            with self.connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                results = cursor.fetchall()
                return results
        except pyodbc.Error as e:
            print(f"Error fetching results: {e}")
            raise

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed.")

    @staticmethod
    @contextmanager
    def connect_with_env():
        load_dotenv()  # Load environment variables from .env file
        server = os.getenv("DB_SERVER")
        database = os.getenv("DB_DATABASE")
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", 1433)

        db = MSSQLDatabase(server, database, username, password, port)
        try:
            if db.connect():
                yield db
            else:
                raise Exception("Failed to connect to the database.")
        finally:
            db.close()

# Example usage:
# Create a .env file with the following content:
# DB_SERVER=your_server
# DB_DATABASE=your_database
# DB_USERNAME=your_username
# DB_PASSWORD=your_password
# DB_PORT=1433

# Usage:
# with MSSQLDatabase.connect_with_env() as db:
#     db.execute_query("CREATE TABLE TestTable (id INT, name NVARCHAR(50))")
#     db.execute_query("INSERT INTO TestTable (id, name) VALUES (?, ?)", (1, 'John Doe'))
#     results = db.fetch_results("SELECT * FROM TestTable")
#     print(results)