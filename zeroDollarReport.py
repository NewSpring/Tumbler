import mssql from dbConnect

query = """
DECLARE @reportEndDate AS DATE = GETDATE();
DECLARE @reportStartDate AS DATE = DATEADD(Month, -1, @reportEndDate);

IF ISDATE(@StartDate) = 1 AND ISDATE(@EndDate) = 1
BEGIN
    SELECT @reportEndDate = @EndDate;
    SELECT @reportStartDate = @StartDate;
END

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
    cursor = mssql(SERVER, DB, USER, PW)
    #Sample select query
    cursor.execute("SELECT @@version;")
    row = cursor.fetchone()
    while row:
        print row[0]
        row = cursor.fetchone()
