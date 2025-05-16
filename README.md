
# KOREAT BACKEND

고려대학교 NE-XT 대회에 KOREAT 팀으로 참가한 프로젝트로 한국의 장소 정보를 제공하고 다양한 언어로 번역해주는 웹 사이트의 백엔드입니다. 외국인 관광객을 위해 식당, 관광지 등의 정보와 리뷰를 실시간으로 수집하고 번역하여 제공합니다.

## 기술 스택

- **프레임워크**: Django
- **API**: GraphQL (Graphene)
- **배포**: AWS EB
- **데이터 수집**: Perplexity AI
- **번역 서비스**: DeepL API
- **이미지 저장**: AWS S3
- **인증**: JWT

## 주요 기능

- 한국어 장소 정보 실시간 수집
- 다국어 번역 지원 (영어, 일본어, 중국어 등)
- 사용자별 카테고리 및 장소 저장
- 리뷰 작성 및 이미지 업로드
- 부적절한 리뷰 신고 및 관리

## 프로젝트 구조

```
back/
├── __pycache__/
├── common/                 # 공통 기능 앱
│   ├── __pycache__/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── schema.py
│   ├── tests.py
│   └── views.py
├── core/                   # 초기에 사용햤으나 지금은 사용 X
│   ├── __pycache__/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── schema.py
│   ├── tests.py
│   └── views.py
├── place/                  # 장소 정보 앱
│   ├── __pycache__/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── schema.py           # GraphQL 스키마 (장소 정보, 번역 등)
│   ├── tests.py
│   └── views.py
├── __init__.py
├── .env                    # 환경 변수 파일
├── asgi.py
├── schema.py               # 루트 GraphQL 스키마
├── urls.py
└── wsgi.py
```

## 설치 및 실행

1. 저장소 클론
```bash
git clone https://github.com/username/repository.git
cd back
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
`.env` 파일을 생성하고 다음 변수들을 설정:
```
DEEPL_API_KEY=your_deepl_api_key
OPENAI_API_KEY=your_perplexity_api_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=your_region
```

5. 마이그레이션 실행
```bash
python manage.py migrate
```

6. 서버 실행
```bash
python manage.py runserver
```

## 주의사항

- **settings.py** 파일은 보안상의 이유로 저장소에서 제외되었습니다. 직접 설정이 필요합니다.
- 환경변수는 .env 파일을 이용합니다.
- 

## 라이센스

MIT
