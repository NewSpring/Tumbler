import os

from dotenv import load_dotenv

from dbConnect import mssql
from tumblerLogging import getLogger

# get custom logger
logger = getLogger()


def reportQuery(months=1):
    """This will select the ids the false transactions."""

    return f"""
        DECLARE @reportEndDate AS DATE = GETDATE();
        DECLARE @reportStartDate AS DATE = DATEADD(Month, -{months}, @reportEndDate);

        SET NOCOUNT ON

        SELECT
            T.Id,
            T.FinancialGatewayId,
            T.TransactionCode,
            P.FirstName + ' ' + P.LastName as Person,
            T.TransactionDateTime
        INTO #zero
        FROM [FinancialTransaction] as T
            JOIN [PersonAlias] as PA ON T.AuthorizedPersonAliasId = PA.Id
            JOIN [Person] AS P ON PA.PersonId = P.Id
        WHERE
            T.Status <> 'Failed' AND
            NOT EXISTS
            (
                SELECT *
                FROM [FinancialTransactionDetail] as TD
                WHERE TD.TransactionId = T.Id
            )  OR
            EXISTS
            (
                SELECT *
                FROM [FinancialTransactionDetail] as TD
                WHERE
                    TD.TransactionId = T.Id AND
                    TD.Amount = 0
            )


        SELECT
            Id,
            TransactionCode as 'NMI Reference Number',
            Person,
            TransactionDateTime as 'Date'
        FROM #zero
        WHERE
            FinancialGatewayId = 3 AND
            TransactionDateTime >= @reportStartDate AND
            TransactionDateTime <= @reportEndDate
    """


def getRowQuery(transID, table):
    """This will return a row from a table."""

    return f"""
        SELECT *
        FROM {table}
        WHERE Id = {transID}
    """


def deleteQuery(transID):
    """This will delete a transaction from the two financial tables."""

    return f"""
        DELETE
        FROM FinancialTransaction
        WHERE Id = {transID}

        DELETE
        FROM FinancialTransactionDetail
        WHERE Id = {transID}
    """


def report(months=1, safe=True):
    """This will run the $0.00 Transaction Report and optionally fix all false transactions."""

    # get database credentials
    load_dotenv()

    server = os.getenv("ROCK_MSSQL_HOST")
    db = os.getenv("ROCK_MSSQL_DB")
    user = os.getenv("ROCK_MSSQL_USER")
    pw = os.getenv("ROCK_MSSQL_PW")
    cnxn = mssql(server, db, user, pw)
    cursor = cnxn.cursor()

    # array of transactions to delete
    transToDelete = []

    # get ids of false transactions
    cursor.execute(reportQuery(months))
    row = cursor.fetchone()
    while row:
        # TODO: get logging working
        logger.info(row)
        print(row)

        transToDelete.append(row[0])
        row = cursor.fetchone()

    if transToDelete == []:
        print("Nothing to report.")
        return 0

    # delete transactions
    print("Rows to be deleted...")
    for transID in transToDelete:

        # show rows that will be deleted
        for table in ["FinancialTransaction", "FinancialTransactionDetail"]:
            cursor.execute(getRowQuery(transID, table))
            print(f"from {table}:")
            print(cursor.fetchone())

        if not safe:
            cursor.execute(deleteQuery(transID))
            cnxn.commit()

    cnxn.close()
