#! /usr/bin/python
import mssql from dbConnect

def zeroDollarReport():
    """This will run the $0.00 Transaction Report and optionally fix all false transactions."""
    cursor = mssql(SERVER, DB, USER, PW)
    #Sample select query
    cursor.execute("SELECT @@version;")
    row = cursor.fetchone()
    while row:
        print row[0]
        row = cursor.fetchone()

if __name__ == "__main__": 
    zeroDollarReport()
