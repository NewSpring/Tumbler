import os
from dotenv import load_dotenv
from dbConnect import mssql

query = """
DECLARE @reportEndDate AS DATE = GETDATE();
DECLARE @reportStartDate AS DATE = DATEADD(Month, -1, @reportEndDate);

-- this is for the datepicker in Rock
/*
IF ISDATE(@StartDate) = 1 AND ISDATE(@EndDate) = 1
BEGIN
    SELECT @reportEndDate = @EndDate;
    SELECT @reportStartDate = @StartDate;
END
*/

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

def report():
    """This will run the $0.00 Transaction Report and optionally fix all false transactions."""

    # get database credentials
    load_dotenv()

    server = os.getenv("ROCK_MSSQL_HOST")
    db = os.getenv("ROCK_MSSQL_DB")
    user = os.getenv("ROCK_MSSQL_USER")
    pw = os.getenv("ROCK_MSSQL_PW")
    cursor = mssql(server, db, user, pw)

    #Sample select query
    cursor.execute(query)
    row = cursor.fetchone()
    while row:
        print(row[0])
        row = cursor.fetchone()
