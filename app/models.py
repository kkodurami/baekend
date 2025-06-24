from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# 회원가입 
class UserRegister(BaseModel) :
    username : str = Field(..., example="rainuser")
    email : EmailStr
    password : str
    phone_num : str
    local_id : int
    crop_name : Optional[str] = None # ← 농작물 이름 (선택 입력 가능)

# 로그인
class UserLogin(BaseModel) :
    email : EmailStr
    password : str
