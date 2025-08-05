from fastapi import FastAPI, HTTPException, Query, Body
from pymongo import MongoClient
from bson import ObjectId
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from typing import Optional

SECRET_KEY = "demo-secret-key"
ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_MINUTES = 30
SENDER_EMAIL = "reyjohnandraje2002@gmail.com"
SENDER_PASSWORD = "xwxv nifa yajn wfeb"

app = FastAPI()

client = MongoClient("mongodb+srv://reyjohnandraje2002:ReyJohn17@concentrix.txv3t.mongodb.net/?retryWrites=true&w=majority&appName=Concentrix")
db = client["LoanSystem"]
loan_applications = db["loan_applications"]

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
def get_password_hash(password):
   return pwd_context.hash(password)
def verify_password(plain_password, hashed_password):
   return pwd_context.verify(plain_password, hashed_password)
def create_reset_token(email: str):
   expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
   payload = {"sub": email, "exp": expire}
   token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
   return token, expire
def send_reset_email(to_email: str, token: str):
   reset_link = f"https://websites-2o2x.onrender.com?token={token}"
   subject = "Password Reset Request"
   body = f"""
   Hi,
   You requested to reset your password. Click the link below to proceed:
   {reset_link}
   This link will expire in {RESET_TOKEN_EXPIRE_MINUTES} minutes.
   If you did not request this, please ignore this email.
   """
   msg = MIMEText(body)
   msg["Subject"] = subject
   msg["From"] = SENDER_EMAIL
   msg["To"] = to_email
   with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
       server.login(SENDER_EMAIL, SENDER_PASSWORD)
       server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

@app.get("/verify_account")
def verify_account(account_name: str = Query(...), account_number: str = Query(...)):
   user = loan_applications.find_one({
       "personal_information.account_name": account_name,
       "personal_information.account_number": account_number
   })
   if user:
       user["_id"] = str(user["_id"])
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
   employment = user.get("employment_information", {}).get("employment_income", {})
   financials = user.get("financial_information", {})
   monthly_income = employment.get("monthly_income", 0)
   length_of_employment = employment.get("length_of_employment", "").lower()
   employment_status = employment.get("employment_status", "").lower()
   employer_name = employment.get("employer_name", "")
   job_title = employment.get("job_title", "")
   years_employed = 0
   if "year" in length_of_employment:
       try:
           years_employed = int(length_of_employment.split()[0])
       except:
           pass
   existing_loans = financials.get("existing_loans", [])
   assets = financials.get("assets", [])
   score = 0
   if monthly_income >= 15000: score += 2
   elif monthly_income >= 10000: score += 1
   if years_employed >= 2: score += 2
   elif years_employed >= 1: score += 1
   if employment_status == "employed": score += 2
   elif employment_status == "self-employed": score += 1
   if len(existing_loans) == 0: score += 2
   elif len(existing_loans) == 1: score += 1
   if assets: score += 1
   is_eligible = score >= 6
   if not is_eligible:
       suggested_loan = 0
   else:
       multiplier = 5 if years_employed >= 2 else 3
       penalty = len(existing_loans) * 0.5
       suggested_loan = max((monthly_income * multiplier) - (monthly_income * penalty), 5000)
   return {
       "full_name": user["personal_information"]["full_name"],
       "monthly_income": monthly_income,
       "employment_status": employment_status,
       "employer_name": employer_name,
       "job_title": job_title,
       "years_employed": years_employed,
       "existing_loans": existing_loans,
       "assets": assets,
       "eligibility_score": score,
       "eligible_for_new_loan": is_eligible,
       "recommendation": "Approved for new loan" if is_eligible else "Needs further review or not eligible",
       "suggested_max_loan_amount": f"₱{int(suggested_loan):,}"
   }
   
@app.post("/request_password_reset")
def request_password_reset(
   payload: Optional[EmailRequest] = Body(None),
   email: Optional[str] = Query(None)
):
   user_email = payload.email if payload and payload.email else email
   if not user_email:
       raise HTTPException(status_code=400, detail="Email is required.")
   user = loan_applications.find_one({"login_credentials.email": user_email})
   if not user:
       raise HTTPException(status_code=404, detail="No user found with this email.")
   token, expiry = create_reset_token(user_email)
   loan_applications.update_one(
       {"_id": user["_id"]},
       {"$set": {
           "login_credentials.reset_token": token,
           "login_credentials.token_expiry": expiry
       }}
   )
   send_reset_email(user_email, token)
   return {"message": "Password reset email sent."}
   
@app.post("/reset_password")
def reset_password(token: str = Body(...), new_password: str = Body(...)):
   try:
       payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
       email = payload.get("sub")
   except:
       raise HTTPException(status_code=400, detail="Invalid or expired token.")
   user = loan_applications.find_one({"login_credentials.email": email})
   if not user or user.get("login_credentials", {}).get("reset_token") != token:
       raise HTTPException(status_code=400, detail="Invalid token or user mismatch.")
   hashed_pw = get_password_hash(new_password)
   loan_applications.update_one(
       {"_id": user["_id"]},
       {"$set": {
           "login_credentials.password": hashed_pw,
           "login_credentials.reset_token": None,
           "login_credentials.token_expiry": None
       }}
   )
   return {"message": "Password reset successful."}
