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

        return {
            "original_filename": file.filename,
            "saved_filename": unique_filename,
            "file_path": str(file_path),
            "file_url": f"/static/uploads/reports/{unique_filename}",
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
    손해 신고 데이터 저장 (JSON 파일 기반 저장 - 테스트/로컬용)
    """
    report_id = f"REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    user_info = {
        "user_id": str(user.get("user_id")),  # ObjectId → str 처리
        "username": user.get("username"),
        "email": user.get("email")
    }

    report_data = {
        "report_id": report_id,
        "user_info": user_info,
        "main_category": main_category,
        "sub_category": sub_category,
        "title": title,
        "content": content,
        "location": {
            "local": local,
            "latitude": float(latitude) if latitude else None,
            "longitude": float(longitude) if longitude else None
        },
        "files": file_info,
        "created_at": datetime.now().isoformat(),
        "status": "접수완료"
    }

    try:
        report_file = REPORT_DIR / f"{report_id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신고 저장 실패: {str(e)}")

    return report_id


def get_user_damage_reports(user_id: str):
    # damage_report에는 user_id가 문자열로 저장되어 있으므로 문자열로 검색
    reports = db.damage_report.find({"user_id": user_id})  # ObjectId() 제거!
    
    result = []
    for report in reports:
        result.append({
            "id": str(report["_id"]),
            "main_category": report.get("main_category"),
            "sub_category": report.get("sub_category"),
            "title": report.get("title")
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
