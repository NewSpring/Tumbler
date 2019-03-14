import json
import os
import pprint
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from tumblerLogging import getLogger

# get custom logger
logger = getLogger()

scheduleQuery = """
-- CHANGE PEOPLE
declare @YourPersonId int = 318257
-- not alias
declare @GiverPersonId int = 79325
-- not alias
-- CHANGE FOR SCHEDULES
declare @TransactionFrequencyString varchar(50) = 'Monthly'
-- enum ['One-Time', 'Weekly', 'Bi-Weekly', 'Twice a Month', 'Monthly', 'Quarterly', 'Twice a Year', 'Yearly']
declare @ScheduleStart date = '2017-02-03'
-- in format YYYY-MM-DD
declare @ScheduleNextPayment date = '2017-05-03'
-- in format YYYY-MM-DD
declare @GatewayScheduleId nvarchar(50) = 3471746098
-- the NMI schedule id
-- SCHEDULE DETAILS (DONT CHANGE THIS LINE)
declare @ScheduleDetails table (MerchantField1 int,
    MerchantField2 int,
    Amount decimal(18,2),
    AccountId int)
-- merchant-defined-field-1, merchant-defined-field-2, amount
-- *DO NOT LOOK UP THE CORRECT ACCOUNT. USE THE MERCHANT FIELDS IN NMI*
insert into @ScheduleDetails
    (MerchantField1, MerchantField2, Amount)
values(125, 8, 310.00)
-- ONCE FOR EACH ACCOUNT ON A SCHEDULE
-- PAYMENT DETAILS
declare @AccountNumberMasked varchar(50) = '5849'
-- LAST 4
declare @CurrencyTypeValueString varchar(50) = 'Credit Card'
-- enum ['Cash', 'Check', 'Credit Card', 'ACH', 'Non-Cash']
declare @CreditCardTypeString varchar(50) = 'MasterCard'
-- enum [NULL, 'Visa','MasterCard','American Express','Discover','Diner''s Club','JCB']
-- DONT CHANGE THESE (OR ANYTHING ELSE BELOW HERE)
declare @YourPrimaryAliasId int = (select top 1
    Id
from PersonAlias
where PersonId=@YourPersonId and AliasPersonId=@YourPersonId)
declare @GiverPrimaryAliasId int = (select top 1
    Id
from PersonAlias
where PersonId=@GiverPersonId and AliasPersonId=@GiverPersonId)
update @ScheduleDetails set AccountId = (select top 1
    Id
from FinancialAccount
where (CampusId = MerchantField2 and ParentAccountId = MerchantField1) or (Id = MerchantField1)
order by ParentAccountId desc)
declare @CurrencyTypeValueId int = (select Id
from DefinedValue
where DefinedTypeId = 10 and Value = @CurrencyTypeValueString)
declare @CreditCardTypeValueId int = (select Id
from DefinedValue
where DefinedTypeId = 11 and Value = @CreditCardTypeString)
declare @TransactionFrequencyValueId int = (select Id
from DefinedValue
where DefinedTypeId = 23 and Value = @TransactionFrequencyString)
DECLARE @ForeignKey AS NVARCHAR(MAX) = 'NMIManualReconciliation' + ' ' + CONVERT(varchar(20), GETDATE(), 1);
begin transaction
-- PAYMENT DETAILS
-- declare guid separate for lookup
declare @PaymentDetailGuid uniqueidentifier = NEWID()
insert into FinancialPaymentDetail
    (
    AccountNumberMasked,
    CurrencyTypeValueId,
    CreditCardTypeValueId,
    CreatedByPersonAliasId,
    ModifiedByPersonAliasId,
    ForeignKey,
    Guid
    )
values
    (
        @AccountNumberMasked,
        @CurrencyTypeValueId,
        @CreditCardTypeValueId,
        @GiverPrimaryAliasId,
        @YourPrimaryAliasId,
        @ForeignKey,
        @PaymentDetailGuid
 )
-- THE SCHEDULE
declare @ScheduleGuid uniqueidentifier = NEWID()
insert into FinancialScheduledTransaction
    (
    AuthorizedPersonAliasId,
    TransactionFrequencyValueId,
    StartDate,
    NextPaymentDate,
    IsActive,
    FinancialGatewayId,
    FinancialPaymentDetailId,
    GatewayScheduleId,
    CreatedByPersonAliasId,
    ModifiedByPersonAliasId,
    SourceTypeValueId,
    Guid,
    ForeignKey
    )
values
    (
        @GiverPrimaryAliasId,
        @TransactionFrequencyValueId,
        @ScheduleStart,
        @ScheduleNextPayment,
        1, -- is active
        3, -- NMI
        (select Id
        from FinancialPaymentDetail
        where Guid = @PaymentDetailGuid),
        @GatewayScheduleId,
        @GiverPrimaryAliasId,
        @YourPrimaryAliasId,
        798,
        @ScheduleGuid,
        @ForeignKey
 )
-- THE SCHEDULE DETAILS
insert into FinancialScheduledTransactionDetail
    (
    AccountId,
    Amount,
    ScheduledTransactionId,
    CreatedByPersonAliasId,
    ModifiedByPersonAliasId,
    Guid,
    ForeignKey
    )
select
    AccountId,
    Amount,
    (select Id
    from FinancialScheduledTransaction
    where Guid = @ScheduleGuid),
    @YourPrimaryAliasId,
    @GiverPrimaryAliasId,
    NEWID(),
    @ForeignKey
from @ScheduleDetails
-- SHOW THE ADDED SCHEDULE DETAILS
select
    s.Id as ScheduleId,
    s.TransactionFrequencyValueId,
    s.StartDate,
    s.NextPaymentDate,
    s.GatewayScheduleId,
    s.CreatedByPersonAliasId,
    sd.Id as ScheduleDetailId,
    sd.AccountId,
    sd.Amount,
    pd.Id as PaymentDetailId,
    pd.AccountNumberMasked,
    pd.CurrencyTypeValueId
from
    FinancialScheduledTransaction as s
    inner join FinancialScheduledTransactionDetail as sd on sd.ScheduledTransactionId = s.Id
    inner join FinancialPaymentDetail as pd on s.FinancialPaymentDetailId = pd.Id
where s.Guid = @ScheduleGuid
declare @scheduleId int = (select Id
from FinancialScheduledTransaction
where Guid = @ScheduleGuid)
select concat('https://rock.newspring.cc/page/319?ScheduledTransactionId=',@scheduleId)
--rollback transaction
--commit transaction
"""


def _isRockTxn(txnID, apiURL, authToken):
    payload = {"$filter": f"TransactionCode eq '{txnID}'"}
    headers = {"Authorization-Token": authToken}
    r = requests.get(f"{apiURL}", headers=headers, params=payload)
    logger.debug(r.text)
    if json.loads(r.text) == []:
        return False
    return True


def _getRockTxns(start, apiURL, authToken):
    startDate = start.strftime("%Y-%m-%dT%H:%M:%S")
    payload = {"$filter": f"ModifiedDateTime ge DateTime'{startDate}'"}
    headers = {"Authorization-Token": authToken}
    r = requests.get(f"{apiURL}", params=payload, headers=headers)
    txns = json.loads(r.text)

    # get all transaction codes
    txnCodes = set(map(lambda x: x["TransactionCode"], txns))

    logger.debug(txnCodes)
    return txnCodes


def _getNMIData(start, apiURL, user, password, authKey):
    startDate = start.strftime("%Y%m%d%H%M%S")
    endDate = datetime.today() + timedelta(hours=23, minutes=59, seconds=59)
    payload = {
        "username": f"{user}",
        "password": f"{password}",
        "start_date": f"{startDate}",
        "end_date": f"{endDate}",
        # "transaction_id": "4555154903",
    }
    headers = {"Authorization": f"{authKey}"}
    r = requests.get(f"{apiURL}", params=payload, headers=headers)
    # print(r.text)
    return ET.fromstring(r.text)


def _getNMITxnIDs(data):

    # get all transaction ids from valid (settle action has an amount and date) transactions
    txnIDs = set()
    for txn in data.findall("transaction"):
        for action in txn.findall("action"):
            isSettleAction = action.find("action_type").text == "settle"
            hasAmount = action.find("amount").text != ""
            hasDate = action.find("date").text != ""
            if isSettleAction and hasAmount and hasDate:
                txnIDs.add(txn.find("transaction_id").text)

    logger.debug(txnIDs)
    return txnIDs


def _syncTxn(txnID, url, token):
    headers = {"Authorization": f"{token}"}
    query = """
    {
      mutation {
        syncTransactions (transaction_id:"txnID") {
          id
          entityId
          summary
          status
          statusMessage
          date
          details {
            id
            amount
          }
          payment {
            id
            accountNumber
            paymentType
          }
          person {
            id
            firstName
            lastName
          }
          schedule {
            id
          }
        }
      }
    }
    """.replace(
        "txnID", txnID
    )
    r = requests.post(url, json={"query": query}, headers=headers)
    return r.text


# TODO: this isn't done, may need to finish if we ever stop using HL query
def _nmiToRockTxn(nmiTxn):

    txnCode = nmiTxn.find("transaction_id").text
    timeFormat = "%Y-%m-%dT%H:%M:%S"
    today = datetime.today().strftime(timeFormat)

    # map NMI data to Rock data
    rockTxn = {
        # TODO: find person
        "AuthorizedPersonAliasId": None,
        "ShowAsAnonymous": False,
        "BatchId": nmiTxn.find("action").find("batch_id").text,
        "FinancialGatewayId": os.getenv("ROCK_NMI_GATEWAY_ID"),
        # TODO: use id from FPD table call
        "FinancialPaymentDetailId": None,
        # TODO: how to get this???
        "TransactionDateTime": None,
        "TransactionCode": txnCode,
        "Summary": f"Reference Number: {txnCode}",
        # TODO: what's this?
        "TransactionTypeValueId": None,
        # TODO: what's this?
        "SourceTypeValueId": None,
        "CheckMicrEncrypted": None,
        "CheckMicrHash": None,
        "MICRStatus": None,
        "CheckMicrParts": None,
        "ScheduledTransactionId": None,
        "IsSettled": None,
        "SettledGroupId": None,
        "SettledDate": None,
        "IsReconciled": None,
        "Status": None,
        "StatusMessage": None,
        # TODO: how's this calculated
        "SundayDate": None,
        "AuthorizedPersonAlias": None,
        "FinancialGateway": None,
        "FinancialPaymentDetail": None,
        "TransactionTypeValue": None,
        "SourceTypeValue": None,
        "TransactionDetails": [],
        "Images": [],
        # NOTE: these are probably automatic
        # "CreatedDateTime": f"{today}",
        # "ModifiedDateTime": f"{today}",
        # TODO: same as above
        "CreatedByPersonAliasId": None,
        # TODO: where is this from?
        "ModifiedByPersonAliasId": None,
        "ModifiedAuditValuesAlreadyUpdated": False,
        "Attributes": None,
        "AttributeValues": None,
        # NOTE: this should be automatic
        # "Id": None,
        # how to get this?
        "Guid": None,
        "ForeignId": None,
        "ForeignGuid": None,
        "ForeignKey": nmiTxn.find("order_id").text,
    }
    return rockTxn


def _addTxn(txn, apiURL, authToken):
    payload = txn
    headers = {"Authorization-Token": authToken}
    r = requests.get(f"{apiURL}", data=payload, headers=headers)
    logger.debug(json.loads(r.text))


def report(start=1):
    """This will sync incorrect transactions in Rock back to correct ones in NMI."""

    # load ENV variables
    load_dotenv()
    rockToken = os.getenv("ROCK_TOKEN")
    rockAPI = os.getenv("ROCK_TXN_API_URL")

    # set starting date
    startDate = datetime.today() - timedelta(days=start)

    # get Rock txns
    rockTxns = _getRockTxns(startDate, rockAPI, rockToken)

    # get NMI txns
    nmiData = _getNMIData(
        startDate,
        os.getenv("NMI_API_URL"),
        os.getenv("NMI_USER"),
        os.getenv("NMI_PASSWORD"),
        os.getenv("NMI_KEY"),
    )
    nmiTxns = _getNMITxnIDs(nmiData)

    # get list of missing Rock txns
    missingIDs = nmiTxns - rockTxns
    # gqlResponses = list(map(lambda x: _syncTxn(x), missingIDs))
    # logger.debug(gqlResponses)

    # double check that txns don't exist, dates may not have exactly lined up
    # missingIDs = set(
    # filter(lambda x: not _isRockTxn(x, rockAPI, rockToken), missingIDs)
    # )
    # logger.debug(missingIDs)

    # convert NMI data to xml objects
    # missingTxns = set(
    # filter(
    # lambda x: x.find("transaction_id").text in missingIDs,
    # nmiData.findall("transaction"),
    # )
    # )

    # translate NMI data to Rock data
    # newRockTxns = list(map(lambda x: _nmiToRockTxn(x), missingTxns))
    # logger.debug(newRockTxns)

    # post Rock transaction into the database
    # map(lambda x: _addTxn(x, rockAPI, rockToken), newRockTxns)
    # TODO: get list of txns with wrong amount


report()
