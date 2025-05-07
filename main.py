from fastapi import FastAPI, Query, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from bson.json_util import dumps
import json

client = MongoClient("mongodb+srv://reyjohnandraje2002:ReyJohn17@concentrix.txv3t.mongodb.net/?retryWrites=true&w=majority&appName=Concentrix")
db = client["LoanSystem"]
loan_applications = db["loan_applications"]

app = FastAPI()

@app.get("/verify_account")
def verify_account(account_name: str = Query(...), account_number: str = Query(...)):
    user = loan_applications.find_one({
        "personal_information.account_name": account_name,
        "personal_information.account_number": account_number
    })

    if user:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
        return user
    else:
        raise HTTPException(status_code=404, detail="No matching account found.")
