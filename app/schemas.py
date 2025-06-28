from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Literal, Dict
from datetime import datetime

class MyPageResponse(BaseModel) :
    username : str
    email : str
    local_id : int
    region_name: Optional[str] = None
    crop_name : Optional[str] = None
    # profile_image : Optional[str] = None

class MyPageUpdateRequest(BaseModel):
    crop_name : Optional[str] = None
    profile_image : Optional[str] = None
    local_id: Optional[int] = None
    # profile_image : Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password : str
    new_password : str

class PostCreate(BaseModel) :
    local_id : int
    title : str
    content : str
    tags : Optional[List[str]] = []

class PostResponse(BaseModel):
    id : str
    user_id : str
    username: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class CommentCreate(BaseModel):
    post_id: str
    content: str

class DamageReportRequest(BaseModel):
    main_category: Literal["재난/재해", "병해충"]
    sub_category : str
    title: Optional[str] = None
    content: Optional[str] = None
    local: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Project(BaseModel):
    title: str
    link: str