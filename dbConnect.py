import pyodbc
import dotenv

def mssql(server, database, username, password):
    """This will connect to any given database."""
    # check for all parameters
    if not (server and database and username and password):
        raise Exception("Missing arguments.")

    # server = 'localhost\sqlexpress' # for a named instance
    # server = 'myserver,port' # to specify an alternate port
    # server = 'tcp:myserver.database.windows.net' # for standard server configuration
    cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
    return cnxn.cursor()


