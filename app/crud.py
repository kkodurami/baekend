from app.database import users_collection, post_collection, comments_collection, post_likes_collection, damage_report_collection
from app.models import UserRegister
from app.models import UserLogin
from datetime import datetime
import bcrypt
from bson import ObjectId
from fastapi import HTTPException, UploadFile
from .database import users_collection, db
import os
import shutil
from app.constants import LOCAL_CODES, DAMAGE_CATEGORIES
from typing import List
from bson.errors import InvalidId
import uuid
import json
import logging
from pathlib import Path
from typing import Optional, List
import torch
from PIL import Image
import io
import pandas as pd
import numpy as np
from ultralytics import YOLO
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import re
from urllib.parse import urljoin
from app import schemas

def create_user(user : UserRegister) :
    if users_collection.find_one({"email":user.email}) :
        raise ValueError("⚠️ 이미 등록된 이메일입니다.")
    
    hashed_pw = bcrypt.hashpw(user.password.encode("utf-8"),bcrypt.gensalt())

    user_dict = user.dict()
    user_dict['password'] = hashed_pw.decode("utf-8")
    user_dict['crop_name']
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
        "crop_name": user["crop_name"],
        "region_name": LOCAL_CODES.get(user["local_id"], "⚠️ 알 수 없음"),
        # "profile_image": user.get("profile_image", "")
    }

def update_user_mypage(user_id: str, update_data: dict):
    update_fields = {}

    if update_data.get("crop_name") is not None:
        update_fields["crop_name"] = update_data["crop_name"]
    # if update_data.get("profile_image") is not None:
    #     update_fields["profile_image"] = update_data["profile_image"]
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


# 프로필 사진 (주석처리)
# UPLOAD_DIR = "static/profile_images"  
# os.makedirs(UPLOAD_DIR, exist_ok=True)  

# UPLOAD_DIR = "static/profile_images"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# def save_profile_image(user_id: str, file: UploadFile) -> str:
#     filename = f"{user_id}_{file.filename}"
#     file_path = os.path.join(UPLOAD_DIR, filename)

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     url = f"/static/profile_images/{filename}"

#     users_collection.update_one(
#         {"_id": ObjectId(user_id)},
#         {"$set": {"profile_image": url}}
#     )

#     return url


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

def update_comment(comments_id: str, users_id: str, new_content: str):
    try:
        comment_oid = ObjectId(comments_id)
        user_oid = ObjectId(users_id)
    except Exception:
        raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다.")

    # 🔍 문제점: comments 컬렉션에서 users_id 필드로 찾고 있음
    # 실제로는 user_id 필드를 사용해야 함
    result = comments_collection.update_one(
        {"_id": comment_oid, "user_id": users_id},  # ✅ users_id → user_id로 수정
        {"$set": {"content": new_content}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없거나 수정 권한이 없습니다.")


def delete_comment(comments_id: str, users_id: str):
    try:
        comment_oid = ObjectId(comments_id)
        user_oid = ObjectId(users_id)
    except Exception:
        raise HTTPException(status_code=400, detail="유효하지 않은 ID 형식입니다.")

    # 🔍 마찬가지로 delete_comment도 수정 필요
    result = comments_collection.delete_one(
        {"_id": comment_oid, "user_id": users_id}  # ✅ users_id → user_id로 수정
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없거나 삭제 권한이 없습니다.")

def get_comments_by_post(post_id: str):
    """특정 게시글의 댓글 목록 조회"""
    try:
        # 게시글이 존재하는지 먼저 확인
        post = post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
        
        # 댓글 조회 (최신순)
        comments = comments_collection.find({"post_id": post_id}).sort("created_at", -1)
        
        result = []
        for comment in comments:
            result.append({
                "id": str(comment["_id"]),
                "user_id": comment["user_id"],
                "username": comment["username"],
                "content": comment["content"],
                "created_at": comment["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=400, detail="잘못된 게시글 ID입니다.")
    
def get_user_damage_reports(users: str):
    reports = db.damage_report.find({"user_id": ObjectId(users)})

    result = []
    for report in reports:
        result.append({
            "id": str(report["_id"]),
            "main_category": report.get("main_category"),
            "sub_category": report.get("sub_category"),
            "title": report.get("title"),
            "latitude" : report.get("latitude"),
            "longitude" : report.get("longitude")
        })
    return result

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
    
from bson import ObjectId

def get_like_status(post_id: str, user_id: str):
    """특정 사용자의 게시글 좋아요 상태 조회"""
    try:
        # 게시글이 존재하는지 확인
        post = post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
        
        # 사용자가 좋아요를 눌렀는지 확인
        like_record = post_likes_collection.find_one({
            "post_id": post_id,
            "user_id": user_id
        })
        
        # 전체 좋아요 수
        total_likes = post.get("likes", 0)
        
        return {
            "post_id": post_id,
            "user_liked": like_record is not None,
            "total_likes": total_likes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="잘못된 게시글 ID입니다.")


def get_post_likes_list(post_id: str, limit: int = 20):
    """게시글에 좋아요를 누른 사용자 목록 조회"""
    try:
        # 게시글이 존재하는지 확인
        post = post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
        
        # 좋아요를 누른 사용자들 조회 (최근순)
        likes = post_likes_collection.find({"post_id": post_id}).sort("liked_at", -1).limit(limit)
        
        user_list = []
        for like in likes:
            user = users_collection.find_one({"_id": ObjectId(like["user_id"])})
            if user:
                user_list.append({
                    "user_id": like["user_id"],
                    "username": user["username"],
                    "liked_at": like["liked_at"].strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return {
            "post_id": post_id,
            "likes": user_list,
            "total": len(user_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="잘못된 게시글 ID입니다.")


def cancel_like_count(post_id: str):
    try:
        oid = ObjectId(post_id)
    except Exception:
        raise HTTPException(status_code=400, detail="유효하지 않은 post_id 형식입니다.")

    post = db.post.find_one({"_id": oid})
    if not post:
        raise HTTPException(status_code=404, detail="게시글이 존재하지 않습니다.")

    current_likes = post.get("likes", 0)
    new_likes = max(0, current_likes - 1)

    db.post.update_one({"_id": oid}, {"$set": {"likes": new_likes}})
    return {"message": "❌ 좋아요가 취소되었습니다."}


def get_posts_by_local(local_id: int):
    # local_id 유효성 검사
    if not isinstance(local_id, int) or local_id not in LOCAL_CODES:
        raise HTTPException(status_code=400, detail="❌ 잘못된 지역 코드입니다.")
    
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


BASE_DIR = Path(__file__).parent.absolute()
REPORT_DIR = BASE_DIR / "static" / "uploads" / "reports"

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

logger = logging.getLogger(__name__)

def get_current_user():
    return {
        "user_id": "user_123",
        "username": "test_user",
        "email": "test@example.com"
    }

def validate_file(file: UploadFile) -> bool:
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    if not file.content_type or not file.content_type.startswith('image/'):
        return False
    return True

# 🔥 수정된 파일 업로드 함수
async def save_uploaded_file(file: UploadFile, report_id: str) -> dict:
    try:
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{report_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = REPORT_DIR / unique_filename

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="파일 크기가 너무 큽니다.")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # 🔥 파일 URL 생성 개선
        file_url = f"/static/uploads/reports/{unique_filename}"
        
        print(f"📁 파일 저장 완료: {file_path}")
        print(f"🔗 파일 URL: {file_url}")

        return {
            "original_filename": file.filename,
            "saved_filename": unique_filename,
            "file_path": str(file_path),
            "file_url": file_url,  # 올바른 URL 형태
            "file_size": len(content),
            "content_type": file.content_type
        }

    except Exception as e:
        logger.error(f"파일 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")


# JSON 저장 디렉토리 설정
BASE_DIR = Path(__file__).parent
REPORT_DIR = BASE_DIR / "static" / "uploads" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 2. crud.py 수정 - create_damage_report 함수
def create_damage_report(
    user: dict,
    main_category: str,
    sub_category: str,
    title: Optional[str],
    content: Optional[str],
    local: Optional[str],
    latitude: Optional[str],
    longitude: Optional[str],
    file_info: List[dict]
) -> str:
    """
    손해 신고 데이터 MongoDB에 저장 (수정된 버전)
    """
    try:
        # 사용자 정보 처리 - ObjectId 문제 해결
        user_id = str(user.get("_id")) if "_id" in user else str(user.get("user_id", ""))
        
           
        # 🔥 파일 정보 처리 개선
        processed_files = []
        for file_data in file_info:
            if isinstance(file_data, dict) and "file_url" in file_data:
                processed_files.append(file_data["file_url"])
            else:
                processed_files.append(str(file_data))

        report_data = {
            "user_id": user_id,  # 문자열로 저장
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "main_category": main_category,
            "sub_category": sub_category,
            "title": title,
            "content": content,
            "local": local,
            "latitude": float(latitude) if latitude and latitude != "" else None,
            "longitude": float(longitude) if longitude and longitude != "" else None,
            "files": processed_files,  # 파일 URL 목록만 저장
            "created_at": datetime.utcnow(),  # datetime.now() 대신 utcnow() 사용
            "status": "접수완료"
        }
        
        print(f"저장할 데이터: {report_data}")  # 디버깅용
        
      # MongoDB에 저장
        result = damage_report_collection.insert_one(report_data)
        
        if result.inserted_id:
            print(f"✅ 저장 성공! ID: {result.inserted_id}")
            return str(result.inserted_id)
        else:
            raise Exception("저장 실패")
            
    except Exception as e:
        print(f"❌ DB 저장 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"신고 저장 실패: {str(e)}")


def get_user_damage_reports(user_id: str):
    # damage_report에는 user_id가 문자열로 저장되어 있으므로 문자열로 검색
    reports = db.damage_report.find({"user_id": user_id})  # ObjectId() 제거!
    
    result = []
    for report in reports:
        result.append({
            "id": str(report["_id"]),
            "main_category": report.get("main_category"),
            "sub_category": report.get("sub_category"),
            "title": report.get("title"),
            "latitude": report.get("latitude"),
            "longitude": report.get("longitude")
        })
    return result


def get_damage_report_detail(report_id: str):
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="유효하지 않은 report_id 형식입니다.")

    report = db.damage_report.find_one({"_id": oid})
    if not report:
        raise HTTPException(status_code=404, detail="신고 내역을 찾을 수 없습니다.")

    report["id"] = str(report["_id"])
    del report["_id"]

    # 민감한 정보 제거 (선택)
    # report.pop("user_id", None)  # 필요시 작성자 정보 제거
    # report.pop("username", None)
    # report.pop("email", None)
    # report.pop("phone", None)

    return report

def get_recent_reports(limit: int = 10):
    try:
        reports_cursor = db.damage_report.find().sort("created_at", -1).limit(limit)
        reports = []
        for report in reports_cursor:
            reports.append({
                "title": report.get("title", ""),
                "id" : str(report["_id"]),
                "main_category": report.get("main_category", ""),
                "sub_category": report.get("sub_category", ""),
                # "created_at": report.get("created_at"),
                # "local": report.get("local", ""),
                "latitude" : report.get("latitude", ""),
                "longitude" : report.get("longitude", ""),
            })
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail="신고 목록 조회 중 오류 발생")

# 모델 경로 설정 (절대경로)
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"

pest_model_path = MODEL_DIR / "Bug_Detect.pt"  # 해충 탐지 모델
disease_model_path = MODEL_DIR / "Crop_Disease.pt"  # 병해 탐지 모델

if not pest_model_path.exists():
    raise RuntimeError(f"해충 탐지 모델이 존재하지 않습니다: {pest_model_path}")
if not disease_model_path.exists():
    raise RuntimeError(f"병해 탐지 모델이 존재하지 않습니다: {disease_model_path}")

# Ultralytics YOLO 모델 로드
pest_model = YOLO(str(pest_model_path))
disease_model = YOLO(str(disease_model_path))

pest_labels = pest_model.names
disease_labels = disease_model.names

def preprocess_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이미지 처리 실패: {str(e)}")

def process_yolo_results(results, labels, confidence_threshold=0.25):
    detections = []
    for box in results[0].boxes:
        conf = float(box.conf[0])
        if conf >= confidence_threshold:
            class_id = int(box.cls[0])
            xyxy = box.xyxy[0].tolist()
            detections.append({
                "class_id": class_id,
                "class_name": labels[class_id],
                "confidence": conf,
                "bbox": {
                    "x1": xyxy[0],
                    "y1": xyxy[1],
                    "x2": xyxy[2],
                    "y2": xyxy[3]
                }
            })
    return detections

def detect_damage_from_report(report_id: str, confidence_threshold: float = 0.25):
    from bson import ObjectId

    print(f"검색하려는 report_id: {report_id}")

    # report 조회 (ObjectId → str 두 가지 방식 시도)
    try:
        object_id = ObjectId(report_id)
        report = db.damage_report.find_one({"_id": object_id})
    except Exception:
        report = db.damage_report.find_one({"_id": report_id})

    if not report:
        raise HTTPException(status_code=404, detail="해당 report_id의 신고를 찾을 수 없습니다")

    main = report.get("main_category")
    sub = report.get("sub_category")

    if not main or not sub:
        raise HTTPException(status_code=400, detail="main_category 또는 sub_category 정보가 부족합니다")

    # 파일 경로 추출
    files = report.get("files", [])
    if not files:
        raise HTTPException(status_code=400, detail="저장된 파일이 없습니다.")

    file_info = files[0]
    file_path = None

    if isinstance(file_info, dict):
        file_path = file_info.get("file_path") or file_info.get("file_url")
    elif isinstance(file_info, str):
        file_path = file_info
    else:
        raise HTTPException(status_code=400, detail="파일 정보 형식이 잘못되었습니다.")

    if not file_path:
        raise HTTPException(status_code=400, detail="파일 경로를 찾을 수 없습니다.")

    # 로컬 파일 경로 확인
    image_path = Path(file_path)
    if not image_path.exists():
        # file_path가 URL이라면 로컬 경로로 변환 시도
        static_prefix = "/static/uploads/reports/"
        if static_prefix in file_path:
            relative = file_path.split(static_prefix)[-1]
            image_path = REPORT_DIR / relative

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="이미지 파일이 존재하지 않습니다")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_pil = preprocess_image(image_bytes)

    # YOLO 탐지 수행
    if sub == "해충":
        results = pest_model(image_pil)
        labels = pest_labels
        category = "해충"
    elif sub == "병해":
        results = disease_model(image_pil)
        labels = disease_labels
        category = "병해"
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 sub_category입니다 (해충, 병해만 가능)")

    detections = process_yolo_results(results, labels, confidence_threshold)

    return {
        "category": category,
        "total_detections": len(detections),
        "detections": detections,
        "primary_detection": detections[0] if detections else None
    }

def convert_js_link(js_link: str) -> str:
    if js_link.startswith("javascript:fn_detailView"):
        try:
            inner = js_link[js_link.index("(")+1 : js_link.index(")")]
            type_str, s_id = [s.strip().strip("'") for s in inner.split(",")]
            return f"https://www.rda.go.kr/young/custom/{type_str}/view.do?sId={s_id}&cp=1"
        except Exception:
            return ""
    return js_link


def fetch_ongoing_projects():
    """
    농촌진흥청 ongoing projects (세미나/행사) 목록과 상세페이지 링크를 크롤링하여 반환
    """
    base_url = "https://www.rda.go.kr"
    list_url = f"{base_url}/young/custom.do"

    resp = requests.get(list_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    projects = []

    for a_tag in soup.select("div.cardName > a"):
        title = a_tag.get("title", "").strip()
        if not title:
            title = a_tag.get_text(strip=True)

        raw_link = a_tag.get("href", "").strip()
        link = convert_js_link(raw_link)

        projects.append(
            schemas.Project(
                title=title,
                link=link
            )
        )

    return projects