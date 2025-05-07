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

@app.get("/analyze_loan_eligibility")
def analyze_loan_eligibility(account_name: str = Query(...), account_number: str = Query(...)):
    user = loan_applications.find_one({
        "personal_information.account_name": account_name,
        "personal_information.account_number": account_number
    })

    if not user:
        raise HTTPException(status_code=404, detail="No matching account found.")

    employment = user.get("employment_information", {})
    financials = user.get("financial_information", {})

    # Extract relevant data
    monthly_income = employment.get("monthly_income", 0)
    length_of_employment = employment.get("length_of_employment", "").lower()
    employment_status = employment.get("employment_status", "").lower()
    existing_loans = financials.get("existing_loans", [])
    assets = financials.get("assets", [])

    # Normalize employment duration
    years_employed = 0
    if "year" in length_of_employment:
        try:
            years_employed = int(length_of_employment.split()[0])
        except:
            pass

    # Basic scoring system
    score = 0

    if monthly_income >= 15000:
        score += 2
    elif monthly_income >= 10000:
        score += 1

    if years_employed >= 2:
        score += 2
    elif years_employed >= 1:
        score += 1

    if employment_status == "employed":
        score += 2
    elif employment_status == "self-employed":
        score += 1

    if len(existing_loans) == 0:
        score += 2
    elif len(existing_loans) == 1:
        score += 1

    if assets:
        score += 1

    # Eligibility result
    is_eligible = score >= 6

    # Suggested loan amount logic
    if not is_eligible:
        suggested_loan = 0
    else:
        # Conservative logic: 3 to 5 times monthly income minus any penalty for existing loans
        multiplier = 5 if years_employed >= 2 else 3
        penalty = len(existing_loans) * 0.5  # 0.5x income per existing loan
        suggested_loan = max((monthly_income * multiplier) - (monthly_income * penalty), 5000)

    return {
        "full_name": user["personal_information"]["full_name"],
        "monthly_income": monthly_income,
        "employment_status": employment_status,
        "years_employed": years_employed,
        "existing_loans": existing_loans,
        "assets": assets,
        "eligibility_score": score,
        "eligible_for_new_loan": is_eligible,
        "recommendation": "Approved for new loan" if is_eligible else "Needs further review or not eligible",
        "suggested_max_loan_amount": f"₱{int(suggested_loan):,}"
    }
