from mongoengine import connect
from mongoengine.connection import disconnect
from credentials import DB_URI


# Connect to, return database
def db_connect(database):
    db = connect(database, host=DB_URI)
    return db