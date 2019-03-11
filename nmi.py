import json
import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv


def _getRockTxns(authToken, start):
    startDate = start.strftime("%Y-%m-%dT%H:%M:%S")
    payload = {"$filter": f"TransactionDateTime gt DateTime'{startDate}'", "$top": "1"}
    headers = {"Authorization-Token": authToken}
    r = requests.get(
        "https://rock.newspring.cc/api/FinancialTransactions",
        params=payload,
        headers=headers,
    )
    txns = json.loads(r.text)
    print(txns)
    return txns


def _getNMITxns(start):
    startDate = start.strftime("%Y%m%d%H%M%S")


def report(start=7):
    """This will sync incorrect transactions in Rock back to correct ones in NMI."""

    # load ENV variables
    load_dotenv()

    # set starting date
    startDate = datetime.today() - timedelta(days=start)

    # get Rock txns
    rockTxns = _getRockTxns(os.getenv("ROCK_TOKEN"), startDate)

    # get NMI txns
    # get list of missing txns
    # get list of txns with wrong amount
    # add back in txns


report()
