from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from llm import generate_sql,execute_query,generate_dashboard
import os
import re

# 환경변수 로드
load_dotenv()

app = FastAPI()

def extract_sql_from_text(text: str) -> str:
    # SQL 쿼리 추출을 위한 정규식 패턴
    sql_pattern = r'SQLQuery:\s*"([^"]*)"'
    match = re.search(sql_pattern, text)
    if match:
        return match.group(1)
    return text

# 요청 데이터 모델
class QuestionRequest(BaseModel):
    question: str

@app.post("/generate-sql")
def generate_sql_api(req: QuestionRequest):
    try:
        # SQL 생성
        sql_query = generate_sql(req.question)  # 변수명 일관성 있게 변경
        print(f"생성된 SQL: {sql_query}")
        
        # 쿼리 실행
        query_result = execute_query(sql_query)  # 올바른 변수 사용
        
        # 대시보드 생성
        dashboard_html = generate_dashboard(query_result)
        
        # 파일 저장
        '''
        with open("dashboard.html", "w", encoding="utf-8") as f:
            f.write(dashboard_html)  # 들여쓰기 수정
        '''
        print("대시보드 생성 완료!")
        return {
            "html": dashboard_html
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"처리 실패: {str(e)}"
        )