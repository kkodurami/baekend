from pymongo import MongoClient
from dotenv import load_dotenv
import os

# .env 파일 로드
# env_path = os.path.join(os.path.dirname(__file__), '..', r'C:\Users\kanga\Desktop\AI_study\project_kkodurami\.env')
load_dotenv() # dotenv_path=env_path

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

# 디버깅
if MONGODB_URI is None:
    raise ValueError("❌ MONGODB_URI 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
if DB_NAME is None:
    raise ValueError("❌ DB_NAME 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")


client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

print("✅ MongoDB에 성공적으로 연결되었습니다!")

# 컬렉션 선언 예시
users_collection = db["users"]
post_collection = db["post"]
comments_collection = db["comments"]
post_likes_collection = db["post_likes"]
damage_report_collection = db["damage_report"]

