import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='sachinsam.mysql.pythonanywhere-services.com',  
        user='sachinsam',                
        password='password@123',
        database='sachinsam$selwyn_ticketing'  
    )
