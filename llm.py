from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.chains import create_sql_query_chain
from dotenv import load_dotenv
import psycopg2
import os
import json
import re

# 환경변수 로드
load_dotenv()

def generate_sql(question: str) -> str:
    # DB 연결
    uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    db = SQLDatabase.from_uri(uri)
    
    # LLM 초기화
    llm = ChatOpenAI(model="gpt-4o")
    
    # 프롬프트 설정
    prompt = PromptTemplate.from_template(
        """
        당신은 SQLGen 어시스턴트 입니다. {dialect} 문법에 맞는 SQL 쿼리를 작성하는 어시스턴트 역할을 수행하세요.

        [테이블 스키마]
        {table_info}

        [요구사항]
        1.사용자의 질문을 받으면, 먼저 문법적으로 올바른 {dialect} 쿼리를 생성하고 쿼리 결과를 분석해 답변을 제공하세요.  
        2.사용자가 명시적으로 원하는 결과 수를 지정하지 않았다면 항상 쿼리 결과를 최대 {top_k}개로 제한하세요.  
        3.관련성이 높은 컬럼을 기준으로 정렬하여 가장 유의미한 결과를 반환하세요.
        4.오더순서는 첫번쨰 컬럼부터 차례대로 오름차순으로 정렬하세요.
        5.SR 관련 질문이니 tb_fail_rqst 테이블을 기준으로 조회하세요.
        6.tb_fail_rqst 테이블의 del_yn 칼럼이 '0'인 컬럼만 조회하세요.
        7.유사어 비교할떄는 like 연산만 사용하세요.(양쪽에 `%` 와일드카드 허용)
        8.응답형식으로만 응답하세요.
        9.컬럼명은 영어고 alies를 한글로 해주고 띄어쓰기시 _로 해주세요.
        10.조회하는 컬럼명이 _cd로 끝날경우 tb_com_cd테이블의 cm_std_cd와 조인하여 cd_nm으로 조회하세요.
        11.쿼리에서 날짜를 비교시 컬림의 data_Type이 timestamp일경우 to_char(컬럼, 'YYYY-MM-DD')로 변환하여 날짜만 비교하세요.
        12.order by 와 group by 는 테이블의 컬럼명으로 사용하세요.

        [응답 형식]
        SQLQuery: "실행할 SQL 쿼리"
    
    
        Question: {input}
        """
    ).partial(dialect=db.dialect)

    print("db.dialect",db.dialect)
    
    # 체인 생성
    agent = create_sql_query_chain(llm, db, prompt=prompt)
    
    # 쿼리 생성
    response = agent.invoke({
        "question": question,
        "top_k": 200
    })
    sql = response.replace('```', '') \
              .replace('"', '') \
              .replace('SQLQuery: ', '') \
              .replace('sql', '') \
              .strip() \
              .rstrip(';') \
              .strip()
    return sql 

def execute_query(query: str) -> list:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cur = conn.cursor()
    cur.execute(query)
    data = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return {"columns": columns, "rows": data}

# 3. LLM으로 HTML 대시보드 생성
def generate_dashboard(data: dict) -> str:
    llm = ChatOpenAI(model="gpt-4o",temperature=0.3)
    
    prompt = PromptTemplate.from_template("""
    [데이터 구조]
    컬럼: {columns}
    샘플 데이터: {sample_rows}

    [요구사항]
    1. 데이터를 시각화할 HTML 대시보드 생성
    2. Plotly.js 라이브러리 사용
    3. 테이블과 차트 1개 포함
    4. 반응형 디자인
    5. 설명은 응답하지 않아도 됩니다.
                                          
    [응답 형식]
    <html>
    <body>
    <h1>대시보드 명칭</h1>
    <table>
        <thead>칼럼</thead>
        <tbody>데이터</tbody>
    </table>
    <div id="chart"/>
    </html>
    """)

    # 사용 예시
    formatted_prompt = prompt.format(
        columns=data['columns'],
        sample_rows=data['rows'][:3]
    )
    
    # LLM 호출
    response = llm.invoke(formatted_prompt)
    response.content = response.content.replace('```html', '') \
                                        .replace('```', '') \
                                        .strip()
    # 결과 반환
    return response.content