from app.database import users_collection, post_collection, comments_collection, post_likes_collection, damage_report_collection
from app.models import UserRegister
from app.models import UserLogin
from datetime import datetime
import bcrypt
from bson import ObjectId
from fastapi import HTTPException, UploadFile
from .database import users_collection
import os
import shutil
from app.constants import LOCAL_CODES
from typing import List

def create_user(user : UserRegister) :
    if users_collection.find_one({"email":user.email}) :
        raise ValueError("⚠️ 이미 등록된 이메일입니다.")
    
    hashed_pw = bcrypt.hashpw(user.password.encode("utf-8"),bcrypt.gensalt())

    user_dict = user.dict()
    user_dict['password'] = hashed_pw.decode("utf-8")
    user_dict['create_date'] = datetime.utcnow()

    users_collection.insert_one(user_dict)


def authenticate_user(login_data : UserLogin) :
    user = users_collection.find_one({'email':login_data.email})
    if not user :
        return None # 존재하지 않는 사용자
    
    if not bcrypt.checkpw(login_data.password.encode("utf-8"),user['password'].encode("utf-8")) :
        return None # 비밀번호 틀림
    
    return user # 인증 성공 시 사용자 정보 반환

def get_user_mypage(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="❌ 사용자 정보를 찾을 수 없습니다.")
    
    return {
        "username": user["username"],
        "email": user["email"],
        "local_id": user["local_id"],
        "crop_name": user.get("crop_name", ""),
        "region_name": LOCAL_CODES.get(user["local_id"], "⚠️ 알 수 없음"),
        "profile_image": user.get("profile_image", "")
    }

def update_user_mypage(user_id: str, update_data: dict):
    update_fields = {}

    if update_data.get("crop_name") is not None:
        update_fields["crop_name"] = update_data["crop_name"]
    if update_data.get("profile_image") is not None:
        update_fields["profile_image"] = update_data["profile_image"]
    if update_data.get("local_id") is not None:
        update_fields["local_id"] = update_data["local_id"]

    if not update_fields:
        raise ValueError("⚠️ 업데이트할 값이 없습니다.")

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )

def change_user_password(user_id: str, current_pw: str, new_pw: str):
    user = users_collection.find_one({"_id" : ObjectId(user_id)})

    if not user or not bcrypt.checkpw(current_pw.encode(), user["password"].encode()):
       raise HTTPException(status_code=400, detail="⚠️ 현재 비밀번호가 올바르지 않습니다.")
    
    new_hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": new_hashed}})


UPLOAD_DIR = "static/profile_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_profile_image(user_id: str, file: UploadFile) -> str:
    filename = f"{user_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"/static/profile_images/{filename}"

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile_image": url}}
    )

    return url


def create_post(user: dict, post_data: dict):
    post = {
        "user_id": str(user["_id"]),
        "username": user["username"],
        "title": post_data["title"],
        "content": post_data["content"],
        "tags": post_data.get("tags", []),
        "local_id": user["local_id"],
        "created_at": datetime.utcnow(),
        "likes": 0
    }
    post_collection.insert_one(post)
    return post

def get_all_posts_with_index():
    posts = post_collection.find().sort("created_at", -1)

    result = []
    for idx, post in enumerate(posts, start=1):  # ← 번호 붙이기
        result.append({
            "no": idx,
            "id": str(post["_id"]),
            "title": post["title"],
            "username": post["username"],
            "created_at": post["created_at"].strftime("%Y-%m-%d %H:%M"),  # 날짜 포맷
            "likes": post.get("likes", 0)
        })

    return result


def get_post_detail(post_id: str):
    post = post_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
    return {
        "id": str(post["_id"]),
        "user_id": post["user_id"],
        "username": post["username"],
        "title": post["title"],
        "content": post["content"],
        "tags": post.get("tags", []),
        "created_at": post["created_at"]
    }

def update_post(post_id: str, user_id: str, update_data: dict):
    post = post_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
    if post["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="❌ 수정 권한이 없습니다.")

    update_fields = {k: v for k, v in update_data.items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="⚠️ 수정할 내용이 없습니다.")

    post_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": update_fields}
    )

def delete_post(post_id: str, user_id: str):
    post = post_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
    if post["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="❌ 삭제 권한이 없습니다.")

    post_collection.delete_one({"_id": ObjectId(post_id)})


def add_comment(user: dict, comment_data: dict):
    comment = {
        "post_id": comment_data["post_id"],
        "user_id": str(user["_id"]),
        "username": user["username"],
        "content": comment_data["content"],
        "created_at": datetime.utcnow()
    }
    comments_collection.insert_one(comment)
    return comment

def toggle_like_post(post_id: str, user_id: str):
    # 중복 방지: user-post 조합이 이미 있는지 확인
    existing = post_likes_collection.find_one({"post_id": post_id, "user_id": user_id})

    if existing:
        # 좋아요 취소
        post_likes_collection.delete_one({"_id": existing["_id"]})
        post_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes": -1}}
        )
        return {"liked": False}
    else:
        # 좋아요 추가
        post_likes_collection.insert_one({
            "post_id": post_id,
            "user_id": user_id,
            "liked_at": datetime.utcnow()
        })
        post_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes": 1}}
        )
        return {"liked": True}

def get_posts_by_local(local_id: int):
    posts = post_collection.find({"local_id": local_id}).sort("created_at", -1)

    result = []
    for idx, post in enumerate(posts, start=1):
        result.append({
            "no": idx,
            "id": str(post["_id"]),
            "title": post["title"],
            "username": post["username"],
            "created_at": post["created_at"].strftime("%Y-%m-%d %H:%M"),
            "likes": post.get("likes", 0)
        })

    return result


DAMAGE_UPLOAD_DIR = "static/reports"
os.makedirs(DAMAGE_UPLOAD_DIR, exist_ok=True)

def create_damage_report(
    user: dict,
    category: str,
    title: str,
    content: str,
    local: str,
    # latitude: float,
    # longitude: float,
    files: List[UploadFile]
):
    uploaded_files = []

    for file in files:
        filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
        filepath = os.path.join(DAMAGE_UPLOAD_DIR, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        uploaded_files.append(f"/static/reports/{filename}")

    report = {
        "user_id": str(user["_id"]),
        "username": user["username"],
        "category": category,
        "title": title,
        "content": content,
        "local": local,
        # "latitude": latitude,
        # "longitude": longitude,
        "files": uploaded_files,
        "created_at": datetime.utcnow()
    }

    damage_report_collection.insert_one(report)
    return report

