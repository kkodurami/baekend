from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# 회원가입 
class UserRegister(BaseModel) :
    username : str = Field(..., example="rainuser")
    email : EmailStr
    password : str
    phone_num : str
    local_id : int

# 로그인
class UserLogin(BaseModel) :
    email : EmailStr
    password : str
