from fastapi import (
    FastAPI, HTTPException, Header, Depends, APIRouter,
    UploadFile, File, Form
)
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from typing import Optional, List
from datetime import datetime
import os

from app.models import UserRegister, UserLogin
from app.schemas import (
    MyPageResponse, MyPageUpdateRequest, ChangePasswordRequest,
    PostCreate, PostUpdate, CommentCreate
)
from app.crud import (
    create_user, authenticate_user, get_user_mypage, update_user_mypage,
    change_user_password, save_profile_image, create_post,
    get_all_posts_with_index, get_post_detail, update_post, delete_post,
    add_comment, toggle_like_post, get_posts_by_local, create_damage_report,
    get_like_status, get_comments_by_post, get_user_damage_reports,
    get_damage_report_detail, get_recent_reports
)
from app.auth import create_access_token, get_current_user
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import users_collection, post_collection
from bson import ObjectId

app = FastAPI()
# router = APIRouter()
# app.include_router(post.router)
bearer_scheme = HTTPBearer()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ 개발 중에는 * 허용, 배포 시에는 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="kkodurami",
        version="1.0.0",
        description="API 문서",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"bearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# 회원가입
@app.post('/register') 
def register(user : UserRegister) :
    try :
        create_user(user)
        return {'message':'✅ 회원가입 성공'}
    except ValueError as e :
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e :
        import traceback
        traceback.print_exc()  # ⬅️ 콘솔에 에러 출력
        raise HTTPException(status_code=500, detail="❌ 서버 오류")
    
# 로그인
@app.post("/login")
def login(user: UserLogin):
    authenticated = authenticate_user(user)
    if not authenticated:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다.")

    token = create_access_token({"user_id": str(authenticated["_id"])})
    return {
        "message": f"{authenticated['username']} 님, 환영합니다!",
        "access_token": token
    }

# 비밀번호 변경
@app.patch("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
) :
    user_id = str(current_user["_id"])
    change_user_password(user_id, req.current_password, req.new_password)
    return {"message" : "✅ 비밀번호가 성공적으로 변경되었습니다"}

# 마이페이지 조회
@app.get("/mypage")
def mypage(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])  # ✅ ObjectId → str
    user_info = get_user_mypage(user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="❌ 사용자 정보를 찾을 수 없습니다.")
    return {"mypage": user_info} 

# 마이페이지 수정
@app.patch("/mypage")
def update_mypage(update_req: MyPageUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = str(current_user["_id"])
        update_user_mypage(user_id, update_req.dict())
        return {"message": "✅ 마이페이지가 성공적으로 수정되었습니다."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="서버 오류")
    

# 프로필 이미지 업로드
@app.post("/upload-profile-image")
def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    url = save_profile_image(user_id, file)
    return {"message": "✅ 프로필 이미지 업로드 완료", "profile_image_url": url}

# 게시글 작성
@app.post("/post")
def write_post(
    post_data: PostCreate,
    current_user: dict = Depends(get_current_user)
):
    post = create_post(current_user, post_data.dict())
    post["id"] = str(post["_id"])
    del post["_id"]
    return post

# 전체 글 목록 조회
@app.get("/posts")
def list_posts():
    posts = get_all_posts_with_index()
    return {"posts": posts}

# 글 상세 조회
@app.get("/posts/{post_id}")
def post_detail(post_id: str):
     return get_post_detail(post_id)

# 게시글 수정
@app.patch("/posts/{post_id}")
def edit_post(
    post_id: str,
    update: PostUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_post(post_id, str(current_user["_id"]), update.dict())
    return {"message": "✅ 게시글이 수정되었습니다."}

# 게시글 삭제
@app.delete("/posts/{post_id}")
def remove_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
):
    delete_post(post_id, str(current_user["_id"]))
    return {"message": "✅ 게시글이 삭제되었습니다."}

# 댓글 쓰기
@app.post("/comments")
def write_comment(
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_user)
):
    comment = add_comment(current_user, comment_data.dict())
    comment["id"] = str(comment["_id"])
    del comment["_id"]
    return comment

# 댓글 조회
@app.get("/posts/{post_id}/comments")
def get_post_comments(post_id: str):
    """특정 게시글의 댓글 목록 조회"""
    comments = get_comments_by_post(post_id)
    return {
        "post_id": post_id,
        "comments": comments,
        "total": len(comments)
    }


# 좋아요 기능
@app.post("/posts/{post_id}/like")
def like_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
):
    result = toggle_like_post(post_id, str(current_user["_id"]))
    return {"message": "좋아요 처리 완료", "liked": result["liked"]}

# 좋아요 상태
@app.get("/posts/{post_id}/like-status")
def get_post_like_status_public(post_id: str):
    """게시글 좋아요 상태 조회 (로그인 불필요)"""
    try:
        # 게시글 존재 확인
        post = post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="⚠️ 게시글을 찾을 수 없습니다.")
        
        total_likes = post.get("likes", 0)
        
        return {
            "post_id": post_id,
            "total_likes": total_likes,
            "user_liked": None  # 로그인하지 않은 경우
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="잘못된 게시글 ID입니다.")

# 로그인한 사용자의 좋아요 상태 조회
@app.get("/posts/{post_id}/like-status/me")
def get_my_like_status(
    post_id: str,
    current_user: dict = Depends(get_current_user)
):
    """현재 사용자의 좋아요 상태 조회 (로그인 필요)"""
    user_id = str(current_user["_id"])
    return get_like_status(post_id, user_id)

# 로컬 아이디 필터링
@app.get("/post/local")
def list_local_posts(current_user: dict = Depends(get_current_user)):
    local_id = current_user["local_id"]
    posts = get_posts_by_local(local_id)
    return {"posts": posts}

# 신고 페이지
@app.post("/report-damage")
async def report_damage(
    main_category: str = Form(...),
    sub_category: str = Form(...),
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    local: Optional[str] = Form(None),
    # latitude: float = Form(...),
    # longitude: float = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    create_damage_report(
        user=current_user,
        main_category=main_category,
        sub_category=sub_category,
        title=title,
        content=content,
        local=local,
        # latitude=latitude,
        # longitude=longitude,
        files=files
    )
    return {"message": "✅ 신고가 성공적으로 접수되었습니다."}

# 사용자의 신고 목록 조회
@app.get("/my-reports")
def get_my_reports(current_user: dict = Depends(get_current_user)):
    print("현재 사용자 ID:", current_user["_id"])  # 콘솔 확인용
    user_id = str(current_user["_id"])
    reports = get_user_damage_reports(user_id)
    return {"reports": reports}

# 신고 상세 조회
@app.get("/report/{report_id}")
def read_report_detail(report_id: str):
    return get_damage_report_detail(report_id)

# 실시간 신고사항 확인
@app.get("/reports/recent")
def read_recent_reports(limit: int = 20):
    reports = get_recent_reports(limit)
    return {"reports": reports}


# @app.on_event("startup")
# def check_routes():
#     print("Registered routes:")
#     for route in app.routes:
#         print(route.path)