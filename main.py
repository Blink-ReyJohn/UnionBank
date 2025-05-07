from fastapi import FastAPI, Query
from pymongo import MongoClient
from pydantic import BaseModel

client = MongoClient("mongodb+srv://reyjohnandraje2002:ReyJohn17@concentrix.txv3t.mongodb.net/?retryWrites=true&w=majority&appName=Concentrix")
db = client["LoanSystem"]
loan_applications = db["loan_applications"]

app = FastAPI()

class MatchResult(BaseModel):
    match: bool
    full_name: str | None = None
    message: str

@app.get("/verify_account", response_model=MatchResult)
def verify_account(account_name: str = Query(...), account_number: str = Query(...)):
    user = loan_applications.find_one({
        "personal_information.account_name": account_name,
        "personal_information.account_number": account_number
    })

    if user:
        return MatchResult(
            match=True,
            full_name=user["personal_information"]["full_name"],
            message="Account name and number matched."
        )
    else:
        return MatchResult(
            match=False,
            message="No matching account found."
        )
