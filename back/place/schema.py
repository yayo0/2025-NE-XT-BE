import re, requests, json
import graphene
from django.conf import settings
from django.core.management import call_command
from graphene_django import DjangoObjectType
from openai import OpenAI
from graphene.types.generic import GenericScalar
from back.place.models import (
  Category, CategoryLog,
  RegionName, RegionLog,
  PlaceInfo, PlaceLog
)


# 🔑 외부 API 설정
DEEPL_URL = 'https://api-free.deepl.com/v2/translate'
DEEPL_AUTH_KEY = settings.DEEPL_API_KEY
OPENAI_API = settings.OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API, base_url="https://api.perplexity.ai")


def deepl_translate(text: str, source_lang: str, target_lang: str) -> str:
  try:
    res = requests.post(
      DEEPL_URL,
      data={
        'text': text,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'auth_key': DEEPL_AUTH_KEY,
      }
    )
    res.raise_for_status()
    return res.json()['translations'][0]['text']
  except Exception as e:
    raise RuntimeError(f'DeepL translation failed: {str(e)}')



class CategoryType(DjangoObjectType):
  class Meta:
    model = Category

class RegionNameType(DjangoObjectType):
  class Meta:
    model = RegionName

class PlaceInfoType(DjangoObjectType):
  class Meta:
    model = PlaceInfo
  
  menu_or_ticket_info = GenericScalar()
  translated_reviews = GenericScalar()


class TranslateCategory(graphene.Mutation):
  class Arguments:
    text = graphene.String(required=True)

  translated_text = graphene.String()

  def mutate(self, info, text):
    if not text:
      raise Exception("Missing 'text' field")

    CategoryLog.objects.create(korean=text)

    try:
      category = Category.objects.get(korean=text)
      return TranslateCategory(translated_text=category.english)
    except Category.DoesNotExist:
      pass

    translated = deepl_translate(text, source_lang='KO', target_lang='EN')
    Category.objects.create(korean=text, english=translated)
    return TranslateCategory(translated_text=translated)


class TranslateRegionToKorean(graphene.Mutation):
  class Arguments:
    text = graphene.String(required=True)

  translated_text = graphene.String()

  def mutate(self, info, text):
    if not text:
      raise Exception("Missing 'text' field")

    RegionLog.objects.create(english=text)

    try:
      region = RegionName.objects.get(english=text)
      return TranslateRegionToKorean(translated_text=region.korean)
    except RegionName.DoesNotExist:
      pass

    translated = deepl_translate(text, source_lang='EN', target_lang='KO')
    RegionName.objects.create(korean=translated, english=text)
    return TranslateRegionToKorean(translated_text=translated)


class GetPlaceInfo(graphene.Mutation):
  class Arguments:
    name = graphene.String(required=True)
    address = graphene.String(required=True)
    language = graphene.String(required=True)

  place = graphene.Field(PlaceInfoType)

  def mutate(self, info, name, address, language):
    if not name or not address or not language:
      raise Exception('Missing name or address or language')
    
    PlaceLog.objects.create(name=name, address=address, language=language)

    try:
      # 이미 있는 경우 리턴
      place = PlaceInfo.objects.get(name=name, address=address, language=language)
      return GetPlaceInfo(place=place)

    except PlaceInfo.DoesNotExist:

      # 프롬프트 구성
      prompt = """
      당신은 한국을 방문한 외국인 관광객을 위한 식당 안내 AI입니다.

      다음 식당에 대해 아래 정보를 웹(특히 네이버, 블로그, 카페 등)에서 최대한 수집해 주세요:
      - 음식 종류 (category)
      - 인기 있는 대표 메뉴 10개 (실제 메뉴 이름과 가격 포함. 가격은 반드시 포함)
      - 사용자 리뷰 20개 이상 (웹상의 실제 후기 기반으로 생생하게 작성)

      **모든 정보는 사실에 근거해야 하며, 허구로 생성하지 마세요.**
      **메뉴 이름과 가격은 정확한 표기를 사용하세요.**
      **리뷰는 실제 사용자 표현에 기반해 다양하고 구체적으로 구성하세요.**
      **title, category, menu, reviews 항목 모두 아래에 제공된 언어로 작성하세요(반드시).**

      출력은 아래 JSON 형식만 사용하며, 코드 블록 기호(```json`) 없이 순수 JSON 텍스트만 출력하세요.
      "menu", "reviews" 항목은 반드시 JSON 배열 형식으로 작성하세요.
      문자열로 감싸거나 escape 처리하지 마세요.

      식당 이름: {name}
      주소: {address}
      언어: {language}
      
      {{
        "title": "식당 이름",
        "category": "음식 종류",
        "menu": [{{"name": "치즈버거", "price": "8000원"}}],
        "reviews": ["너무 맛있어요.", "청결해요"]
      }}

      """.format(name=name, address=address, language=language)

      messages = [
        {
          "role": "system",
          "content": (
            "You are a professional tourist assistant who always replies only in the requested JSON format. "
            "You must rely on real, recent web data (especially Naver, blogs, local listings). "
            "Never invent data. Every item must be filled with the best real-world estimate possible. "
            "Do not use markdown or explanations — return only raw JSON text."
          ),
        },
        {
          "role": "user",
          "content": prompt,
        },
      ]

      try:
        response = client.chat.completions.create(
          model="sonar",
          messages=messages
        )
        content = response.choices[0].message.content

        try:
          data = json.loads(content)
        except json.JSONDecodeError:
          raise Exception("Perplexity 응답에서 유효한 JSON을 파싱하지 못했습니다.")


        place = PlaceInfo.objects.create(
          name=name,
          address=address,
          language=language,
          title=data.get("title"),
          category=data.get("category"),
          menu_or_ticket_info=data.get("menu"),
          translated_reviews=data.get("reviews")
        )

        return GetPlaceInfo(place=place)

      except Exception as e:
        raise Exception(f"Perplexity API Error: {str(e)}")



class InsertFixedCategories(graphene.Mutation):
  message = graphene.String()
  inserted = graphene.Int()
  skipped = graphene.Int()

  def mutate(self, info):
    raw_data = '''
    음식점 > 한식 > 육류,고기 > 곱창,막창	Restaurant > Korean > Meats, Pork > Gopchang, Makchang
    음식점 > 한식 > 냉면	Restaurants > Korean > Cold Noodles
    음식점 > 샤브샤브	Restaurants > Shabu-Shabu
    음식점 > 중식 > 중국요리	Restaurants > Chinese > Chinese
    음식점 > 한식 > 찌개,전골	Restaurant > Korean > Jjigae,Hotpot
    음식점 > 한식 > 순대	Restaurants > Korean > Sundae
    음식점 > 양식	Restaurant > Forms
    음식점 > 한식 > 한정식	Restaurants > Korean > Korean Food
    음식점 > 한식 > 육류,고기 > 닭요리	Restaurant > Korean > Meat, meat > Chicken
    음식점 > 일식 > 돈까스,우동	Restaurant > Japanese > Tonkatsu,Udon Noodles
    음식점 > 양식 > 이탈리안	Restaurants > Western > Italian
    음식점 > 양식 > 피자	Restaurants > Western > Pizza
    음식점 > 한식 > 육류,고기	Restaurant > Korean > Meat
    음식점 > 일식 > 초밥,롤	Restaurant > Japanese > Sushi, Rolls
    음식점 > 한식 > 해물,생선 > 게,대게	Restaurants > Korean > Seafood, Fish > Crab, Snow Crab
    음식점 > 일식 > 참치회	Restaurants > Japanese > Tuna Sashimi
    음식점 > 한식	Restaurants > Korean
    음식점 > 양식 > 햄버거	Restaurants > Forms > Hamburger
    음식점 > 술집 > 일본식주점	Restaurants > Bars > Japanese Restaurants
    음식점 > 한식 > 해물,생선 > 추어	Restaurant > Korean > Seafood, Fish > Chuur
    음식점 > 한식 > 해물,생선	Restaurants > Korean > Seafood, Fish
    음식점 > 중식	Restaurants > Chinese
    음식점 > 퓨전요리 > 퓨전일식	Restaurants > Fusion > Fusion Japanese
    음식점 > 한식 > 해물,생선 > 회	Restaurant > Korean > Seafood, Fish > Sashimi
    음식점 > 퓨전요리	Restaurants > Fusion
    음식점 > 양식 > 멕시칸,브라질	Restaurant > Western > Mexican,Brazilian
    음식점 > 한식 > 해물,생선 > 복어	Restaurants > Korean > Seafood, Fish > Pufferfish
    음식점 > 중식 > 양꼬치	Restaurants > Chinese > Lamb Skewers
    여행 > 관광,명소 > 전망대	Travel > Sightseeing, Attractions > Observatories
    여행 > 관광,명소 > 테마거리	Travel > Sightseeing, attractions > Themed streets
    여행 > 관광,명소 > 섬 > 섬(내륙)	Travel > Sightseeing, Attractions > Islands > Islands (Inland)
    여행 > 관광,명소 > 도보여행	Travel > Sightseeing, attractions > Walking tours
    음식점 > 한식 > 해물,생선 > 아구	Restaurant > Korean > Seafood, Fish > Agu
    음식점 > 뷔페	Restaurants > Buffets
    음식점 > 한식 > 육류,고기 > 갈비	Restaurants > Korean > Meat, Pork > Ribs
    음식점 > 한식 > 수제비	Restaurants > Korean > Sujebi
    음식점 > 일식 > 일본식라면	Restaurants > Japanese > Japanese Ramen
    음식점 > 분식 > 떡볶이	Restaurants > Bunsik > Tteokbokki
    음식점 > 일식	Restaurants > Japanese
    음식점 > 한식 > 설렁탕	Restaurants > Korean > Seolleongtang
    음식점 > 한식 > 국수 > 칼국수	Restaurants > Korean > Noodles > Kalguksu
    음식점 > 한식 > 국수	Restaurants > Korean > Noodles
    음식점 > 뷔페 > 해산물뷔페 > 쿠우쿠우	Restaurants > Buffet > Seafood Buffet > Koo Koo Koo
    음식점 > 간식 > 제과,베이커리	Restaurants > Snacks > Confectionery, Bakery
    음식점 > 한식 > 해물,생선 > 매운탕,해물탕	Restaurant > Korean > Seafood, Fish > Spicy Hot Pot, Seafood Hot Pot
    여행 > 관광,명소 > 관광농원	Travel > Sightseeing, attractions > Tourist farms
    여행 > 관광,명소 > 계곡	Travel > Sightseeing, attractions > Valleys
    여행 > 관광,명소 > 도보여행 > DMZ평화의길	Travel > Sightseeing, Attractions > Walking Tour > DMZ Peace Road
    여행 > 관광,명소 > 산	Travel > Sightseeing, attractions > Mountains
    여행 > 관광,명소 > 관광단지	Travel > Sightseeing, attractions > Tourist complexes
    여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길	Travel > Sightseeing, Attractions > Walking > Olle-gil > Jeju Olle-gil
    음식점 > 패스트푸드	Restaurants > Fast Food
    음식점 > 분식	Restaurants > Meals
    여행 > 관광,명소 > 저수지	Travel > Sightseeing, attractions > Reservoirs
    음식점 > 한식 > 육류,고기 > 삼겹살	Restaurants > Korean > Meat, Pork > Pork Belly
    음식점 > 술집 > 호프,요리주점	Restaurants > Bars > Hops, Cuisine Bars
    음식점 > 한식 > 감자탕	Restaurants > Korean > Potato Soup
    음식점 > 한식 > 육류,고기 > 족발,보쌈	Restaurants > Korean > Meats, Pork > Pork Feet, Bossam
    음식점 > 술집 > 실내포장마차	Restaurants > Bars > Indoor stalls
    음식점 > 기사식당	Restaurants > Knight's Restaurant
    음식점 > 양식 > 스테이크,립	Restaurant > Western > Steak, Ribs
    음식점 > 한식 > 국밥	Restaurants > Korean > Soup
    '''

    created = 0
    skipped = 0
    for line in raw_data.strip().splitlines():
      if not line.strip():
        continue
      parts = line.strip().split('\t')
      if len(parts) != 2:
        continue
      korean, english = parts
      if Category.objects.filter(korean=korean.strip()).exists():
        skipped += 1
        continue
      Category.objects.create(korean=korean.strip(), english=english.strip())
      created += 1

    return InsertFixedCategories(
      message='카테고리 일괄 입력 완료',
      inserted=created,
      skipped=skipped
    )


class InsertCategoryLogs(graphene.Mutation):
  message = graphene.String()
  inserted = graphene.Int()
  skipped = graphene.Int()

  def mutate(self, info):
    raw = '''
음식점 > 한식 > 냉면
음식점 > 한식 > 육류,고기
음식점 > 한식 > 해물,생선 > 아구
음식점 > 한식 > 육류,고기
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 육류,고기
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 뷔페
음식점 > 한식 > 육류,고기
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 수제비
음식점 > 일식 > 일본식라면
음식점 > 분식 > 떡볶이
음식점 > 한식 > 해물,생선
음식점 > 일식
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 설렁탕
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 찌개,전골
음식점 > 한식
음식점 > 한식
음식점 > 중식
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 국수 > 칼국수
음식점 > 한식 > 해물,생선 > 복어
음식점 > 한식 > 국수
음식점 > 한식 > 해물,생선 > 회
음식점 > 뷔페
음식점 > 뷔페 > 해산물뷔페 > 쿠우쿠우
음식점 > 간식 > 제과,베이커리
음식점 > 한식 > 해물,생선 > 매운탕,해물탕
음식점 > 한식 > 순대
음식점 > 간식 > 제과,베이커리
여행 > 관광,명소 > 관광농원
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 도보여행 > DMZ평화의길
여행 > 관광,명소 > 관광농원
여행 > 관광,명소 > 도보여행
여행 > 관광,명소 > 산
여행 > 관광,명소 > 관광농원
여행 > 관광,명소 > 도보여행 > DMZ평화의길
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 도보여행
여행 > 관광,명소 > 관광단지
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
여행 > 관광,명소 > 도보여행 > 올레길 > 제주올레길
음식점 > 한식 > 해물,생선
음식점 > 패스트푸드
음식점 > 한식 > 수제비
음식점 > 분식
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 분식
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 한식 > 국수
음식점 > 한식 > 해물,생선
음식점 > 분식
음식점 > 한식 > 냉면
음식점 > 한식 > 해물,생선 > 복어
음식점 > 한식 > 냉면
음식점 > 패스트푸드
음식점 > 한식 > 수제비
음식점 > 분식
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 저수지
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 계곡
여행 > 관광,명소 > 저수지
음식점 > 한식 > 국수
음식점 > 분식
음식점 > 한식 > 해물,생선 > 복어
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 한식 > 수제비
음식점 > 분식
음식점 > 한식 > 냉면
음식점 > 한식 > 해물,생선
음식점 > 패스트푸드
음식점 > 샤브샤브
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 한정식
음식점 > 양식
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 냉면
음식점 > 중식 > 중국요리
음식점 > 한식 > 한정식
음식점 > 한식 > 냉면
음식점 > 양식
음식점 > 중식 > 중국요리
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 냉면
음식점 > 한식 > 순대
음식점 > 한식 > 한정식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 한정식
음식점 > 샤브샤브
음식점 > 양식
음식점 > 중식 > 중국요리
음식점 > 한식 > 한정식
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 샤브샤브
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 냉면
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 한정식
음식점 > 한식 > 한정식
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 한정식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 양식
음식점 > 중식 > 중국요리
음식점 > 한식 > 순대
음식점 > 샤브샤브
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 중식 > 중국요리
음식점 > 한식 > 찌개,전골
음식점 > 샤브샤브
음식점 > 한식 > 한정식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 양식
음식점 > 한식 > 한정식
음식점 > 한식 > 냉면
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 한식 > 순대
음식점 > 한식 > 한정식
음식점 > 한식 > 찌개,전골
음식점 > 양식
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 중식 > 중국요리
음식점 > 샤브샤브
음식점 > 한식 > 한정식
음식점 > 중식 > 중국요리
음식점 > 한식 > 냉면
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 한식 > 한정식
음식점 > 샤브샤브
음식점 > 한식 > 한정식
음식점 > 한식 > 찌개,전골
음식점 > 양식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 중식 > 중국요리
음식점 > 한식 > 한정식
음식점 > 한식 > 냉면
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 한정식
음식점 > 샤브샤브
음식점 > 양식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 샤브샤브
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 한정식
음식점 > 중식 > 중국요리
음식점 > 한식 > 한정식
음식점 > 한식 > 냉면
음식점 > 양식
음식점 > 한식 > 순대
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 냉면
음식점 > 샤브샤브
음식점 > 한식 > 냉면
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 냉면
음식점 > 한식 > 한정식
음식점 > 한식 > 한정식
음식점 > 양식
음식점 > 중식 > 중국요리
음식점 > 한식 > 순대
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 한정식
음식점 > 중식 > 중국요리
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 한식 > 냉면
음식점 > 샤브샤브
음식점 > 한식 > 찌개,전골
음식점 > 양식
음식점 > 한식 > 한정식
음식점 > 샤브샤브
음식점 > 한식 > 한정식
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 한정식
음식점 > 한식 > 순대
음식점 > 한식 > 냉면
음식점 > 중식 > 중국요리
음식점 > 한식 > 냉면
음식점 > 양식
음식점 > 한식 > 찌개,전골
음식점 > 중식 > 중국요리
음식점 > 한식 > 냉면
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 한정식
음식점 > 한식 > 한정식
음식점 > 양식
음식점 > 한식 > 냉면
음식점 > 샤브샤브
음식점 > 한식 > 순대
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 샤브샤브
음식점 > 양식
음식점 > 중식 > 중국요리
음식점 > 한식 > 냉면
음식점 > 한식 > 순대
음식점 > 한식 > 한정식
음식점 > 한식 > 찌개,전골
음식점 > 한식 > 냉면
음식점 > 한식 > 한정식
음식점 > 한식 > 육류,고기 > 삼겹살
음식점 > 양식 > 햄버거
음식점 > 양식
음식점 > 간식 > 제과,베이커리
음식점 > 술집 > 호프,요리주점
음식점 > 한식 > 감자탕
음식점 > 술집 > 호프,요리주점
음식점 > 간식 > 제과,베이커리
음식점 > 한식 > 육류,고기 > 족발,보쌈
음식점 > 일식 > 돈까스,우동
음식점 > 한식 > 감자탕
음식점 > 한식 > 육류,고기 > 족발,보쌈
음식점 > 술집 > 호프,요리주점
음식점 > 한식 > 육류,고기 > 삼겹살
음식점 > 양식
음식점 > 양식 > 햄버거
음식점 > 간식 > 제과,베이커리
음식점 > 일식 > 돈까스,우동
음식점 > 술집 > 호프,요리주점
음식점 > 간식 > 제과,베이커리
음식점 > 술집 > 실내포장마차
음식점 > 중식 > 중국요리
음식점 > 일식 > 돈까스,우동
음식점 > 기사식당
음식점 > 한식 > 해물,생선 > 회
음식점 > 한식 > 감자탕
음식점 > 양식 > 스테이크,립
음식점 > 양식 > 이탈리안
음식점 > 일식 > 일본식라면
음식점 > 한식 > 냉면
음식점 > 양식 > 이탈리안
음식점 > 술집 > 호프,요리주점
음식점 > 한식 > 육류,고기
음식점 > 한식 > 국수
음식점 > 한식 > 육류,고기 > 갈비
음식점 > 한식 > 육류,고기 > 곱창,막창
음식점 > 한식 > 육류,고기
음식점 > 분식
음식점 > 한식 > 설렁탕
음식점 > 한식 > 육류,고기
음식점 > 한식 > 해물,생선
음식점 > 한식 > 순대
음식점 > 한식 > 순대
음식점 > 한식 > 순대
음식점 > 한식 > 육류,고기 > 삼겹살
음식점 > 한식
음식점 > 한식 > 국밥
    '''

    created = 0
    skipped = 0
    for line in raw.strip().splitlines():
      name = line.strip()
      if not name:
        continue
      if CategoryLog.objects.filter(korean=name).exists():
        skipped += 1
        continue
      CategoryLog.objects.create(korean=name)
      created += 1

    return InsertCategoryLogs(
      message='CategoryLog 일괄 추가 완료',
      inserted=created,
      skipped=skipped
    )

class Mutation(graphene.ObjectType):
  translate_category = TranslateCategory.Field()
  translate_region_to_korean = TranslateRegionToKorean.Field()
  get_place_info = GetPlaceInfo.Field()
  insert_fixed_categories = InsertFixedCategories.Field()
  insert_category_logs = InsertCategoryLogs.Field()


class Query(graphene.ObjectType):
  place_info_by_name = graphene.Field(
    PlaceInfoType,
    name=graphene.String(required=True),
    address=graphene.String(required=True)
  )
  get_place_info_by_name = graphene.String(
    name=graphene.String(required=True),
    address=graphene.String(required=True),
    language=graphene.String(required=True)
  )

  def resolve_place_info_by_name(self, info, name, address):
    try:
      return PlaceInfo.objects.get(name=name, address=address)
    except PlaceInfo.DoesNotExist:
      return None

  def resolve_get_place_info_by_name(self, info, name, address, language):
    prompt = """
      당신은 한국 방문 관광객을 위한 맛집 안내 AI입니다.
      아래의 식당에 대해서 당신이 제공해야 할 것은 음식 종류, 메뉴와 가격, 리뷰입니다.
      메뉴는 10개, 리뷰는 20개 이상 네이버 검색엔진을 우선적으로 탐색하세요.
      부가적인 설명은 필요없습니다. 답은 오직 아래의 json 형식으로 답하세요.
      아래에 제공된 언어로 번역하여 답하세요.
      코드 블록 기호(```json`) 없이 순수 JSON 텍스트만 출력하세요.

      {{
        "title": "식당 이름",
        "category": "음식 종류",
        "menu": [{{"name": "치즈버거", "price": "8000원"}}],
        "reviews": ["너무 맛있어요.", "청결해요"]
      }}

      식당 이름: {name}
      주소: {address}
      언어: {language}
      """.format(name=name, address=address, language=language)

    messages = [
      {
        "role": "system",
        "content": (
          "You are a helpful assistant that only replies in the just specified JSON format. "
          "No other text or explanation is needed."
        ),
      },
      {
        "role": "user",
        "content": prompt,
      },
    ]

    response = client.chat.completions.create(
      model="sonar",
      messages=messages
    )
    content = response.choices[0].message.content
    return content