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
  PlaceInfo, PlaceLog,
  UserCategory, SavedPlace
)
from graphql_jwt.decorators import login_required

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

class UserCategoryType(DjangoObjectType):
  class Meta:
    model = UserCategory


class SavedPlaceType(DjangoObjectType):
  class Meta:
    model = SavedPlace
    fields = '__all__'

  road_address_name_EN = graphene.String()
  category_name_EN = graphene.String()
  roadAddressNameEN = graphene.String()
  categoryNameEN = graphene.String()
  
  def resolve_road_address_name_EN(self, info):
    return self.road_address_name_en
    
  def resolve_category_name_EN(self, info):
    return self.category_name_en
    
  def resolve_roadAddressNameEN(self, info):
    return self.road_address_name_en
    
  def resolve_categoryNameEN(self, info):
    return self.category_name_en

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
      당신은 한국을 방문한 외국인 관광객을 위한 장소 안내 AI입니다.

      다음 장소에 대해 아래 정보를 웹(특히 네이버, 블로그, 카페 등)에서 최대한 수집해 주세요:
      - 식당이라면 음식 종류 (category), 장소라면 종류 (category)
      - 식당이라면 인기 있는 대표 메뉴 10개 (메뉴 이름과 가격 포함), 장소라면 티켓 정보 (menu)
      - 사용자 리뷰 20개 이상 (웹상의 실제 후기 기반으로 생생하게 작성)

      장소 이름: {name}
      주소: {address}
      번역 언어: {language}

      **모든 정보는 사실에 근거해야 하며, 허구로 생성하지 마세요.**
      **메뉴 이름과 가격은 정확한 표기를 사용하세요.**
      **리뷰는 실제 사용자 표현에 기반해 다양하고 구체적으로 구성하세요.**
      **title, category, menu, reviews 항목에 들어가는 내용은 반드시 번역 언어로 작성하세요.**

      출력은 아래 JSON 형식만 사용하며, 코드 블록 기호(```json```) 없이 순수 JSON 텍스트만 출력하세요.
      "menu", "reviews" 항목은 반드시 JSON 배열 형식으로 작성하세요.
      문자열로 감싸거나 escape 처리하지 마세요.
      반드시 아래 JSON 형식으로만 답하세요.
      
      해당 장소에 대한 정보가 없는 경우 반드시 빈 문자열로 답하세요.

      {{
        "title": "장소 이름",
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

        if not content or content.strip() == "":
          raise Exception("No information available for this place")

        try:
          data = json.loads(content)
        except json.JSONDecodeError:
          raise Exception("Could not parse valid JSON from Perplexity response.")


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



class CreateUserCategory(graphene.Mutation):
  class Arguments:
    name = graphene.String(required=True)
    color = graphene.String()

  category = graphene.Field(UserCategoryType)
  message = graphene.String()

  @login_required
  def mutate(self, info, name, color):
    user = info.context.user
    
    if UserCategory.objects.filter(user=user, name=name).exists():
      raise Exception("A category with this name already exists")
    
    category = UserCategory.objects.create(user=user, name=name, color=color)
    return CreateUserCategory(category=category, message="Category created successfully")


class UpdateUserCategory(graphene.Mutation):
  class Arguments:
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    color = graphene.String()

  category = graphene.Field(UserCategoryType)
  message = graphene.String()

  @login_required
  def mutate(self, info, id, name, color=None):
    user = info.context.user
    
    try:
      category = UserCategory.objects.get(id=id, user=user)
    except UserCategory.DoesNotExist:
      raise Exception("Category not found")
      
    if UserCategory.objects.filter(user=user, name=name).exclude(id=id).exists():
      raise Exception("A category with this name already exists")
      
    category.name = name
    if color is not None:
      category.color = color
    category.save()
    return UpdateUserCategory(category=category, message="Category updated successfully")


class DeleteUserCategory(graphene.Mutation):
  class Arguments:
    id = graphene.ID(required=True)

  message = graphene.String()

  @login_required
  def mutate(self, info, id):
    user = info.context.user
    
    try:
      category = UserCategory.objects.get(id=id, user=user)
    except UserCategory.DoesNotExist:
      raise Exception("Category not found")
      
    category.delete()
    return DeleteUserCategory(message="Category deleted successfully")


class CreateSavedPlace(graphene.Mutation):
  class Arguments:
    category_id = graphene.ID(required=True)
    place_id = graphene.String(required=True)
    place_name = graphene.String(required=True)
    address_name = graphene.String()
    road_address_name = graphene.String()
    road_address_name_en = graphene.String()
    phone = graphene.String()
    category_name = graphene.String()
    category_name_en = graphene.String()
    place_url = graphene.String()
    category_group_code = graphene.String()
    x = graphene.String()
    y = graphene.String()
    lat = graphene.String()
    lng = graphene.String()

  place = graphene.Field(SavedPlaceType)
  message = graphene.String()

  @login_required
  def mutate(self, info, category_id, place_id, place_name, **kwargs):
    user = info.context.user
    
    try:
      category = UserCategory.objects.get(id=category_id, user=user)
    except UserCategory.DoesNotExist:
      raise Exception("Category not found")
      
    # 동일 카테고리에 중복된 place_id가 있는지 확인
    if SavedPlace.objects.filter(category=category, place_id=place_id).exists():
      raise Exception("This place is already saved in this category")
    
    place = SavedPlace.objects.create(
      category=category,
      place_id=place_id,
      place_name=place_name,
      **{k: v for k, v in kwargs.items() if v is not None}
    )
    
    return CreateSavedPlace(place=place, message="Place saved successfully")


class UpdateSavedPlace(graphene.Mutation):
  class Arguments:
    id = graphene.ID(required=True)
    place_name = graphene.String()
    address_name = graphene.String()
    road_address_name = graphene.String()
    road_address_name_en = graphene.String()
    phone = graphene.String()
    category_name = graphene.String()
    category_name_en = graphene.String()
    place_url = graphene.String()
    category_group_code = graphene.String()
    x = graphene.String()
    y = graphene.String()
    lat = graphene.String()
    lng = graphene.String()

  place = graphene.Field(SavedPlaceType)
  message = graphene.String()

  @login_required
  def mutate(self, info, id, **kwargs):
    user = info.context.user
    
    try:
      place = SavedPlace.objects.get(id=id, category__user=user)
    except SavedPlace.DoesNotExist:
      raise Exception("Saved place not found")
    
    for key, value in kwargs.items():
      if value is not None:
        setattr(place, key, value)
    
    place.save()
    return UpdateSavedPlace(place=place, message="Place information updated successfully")


class MoveSavedPlace(graphene.Mutation):
  class Arguments:
    id = graphene.ID(required=True)
    new_category_id = graphene.ID(required=True)

  place = graphene.Field(SavedPlaceType)
  message = graphene.String()

  @login_required
  def mutate(self, info, id, new_category_id):
    user = info.context.user
    
    try:
      place = SavedPlace.objects.get(id=id, category__user=user)
    except SavedPlace.DoesNotExist:
      raise Exception("Saved place not found")
      
    try:
      new_category = UserCategory.objects.get(id=new_category_id, user=user)
    except UserCategory.DoesNotExist:
      raise Exception("Target category not found")
      
    # 대상 카테고리에 동일한 place_id가 있는지 확인
    if SavedPlace.objects.filter(category=new_category, place_id=place.place_id).exists():
      raise Exception("This place already exists in the target category")
    
    place.category = new_category
    place.save()
    return MoveSavedPlace(place=place, message="Place moved to different category successfully")


class DeleteSavedPlace(graphene.Mutation):
  class Arguments:
    id = graphene.ID(required=True)

  message = graphene.String()

  @login_required
  def mutate(self, info, id):
    user = info.context.user
    
    try:
      place = SavedPlace.objects.get(id=id, category__user=user)
    except SavedPlace.DoesNotExist:
      raise Exception("Saved place not found")
      
    place.delete()
    return DeleteSavedPlace(message="Saved place deleted successfully")


# Mutation 클래스에 추가
class Mutation(graphene.ObjectType):
  translate_category = TranslateCategory.Field()
  translate_region_to_korean = TranslateRegionToKorean.Field()
  get_place_info = GetPlaceInfo.Field()
  
  # UserCategory 관련 필드
  create_user_category = CreateUserCategory.Field()
  update_user_category = UpdateUserCategory.Field()
  delete_user_category = DeleteUserCategory.Field()
  
  # SavedPlace 관련 필드
  create_saved_place = CreateSavedPlace.Field()
  update_saved_place = UpdateSavedPlace.Field()
  move_saved_place = MoveSavedPlace.Field()
  delete_saved_place = DeleteSavedPlace.Field()


# Query 클래스에 추가
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
  
  # UserCategory 관련 필드
  user_categories = graphene.List(UserCategoryType)
  user_category = graphene.Field(UserCategoryType, id=graphene.ID(required=True))
  
  # SavedPlace 관련 필드
  saved_places_by_category = graphene.List(
    SavedPlaceType, 
    category_id=graphene.ID(required=True)
  )
  saved_place = graphene.Field(SavedPlaceType, id=graphene.ID(required=True))

  @login_required
  def resolve_user_categories(self, info):
    user = info.context.user
    return UserCategory.objects.filter(user=user).order_by('id')
  
  @login_required
  def resolve_user_category(self, info, id):
    user = info.context.user
    try:
      return UserCategory.objects.get(id=id, user=user)
    except UserCategory.DoesNotExist:
      return None
  
  @login_required
  def resolve_saved_places_by_category(self, info, category_id):
    user = info.context.user
    try:
      category = UserCategory.objects.get(id=category_id, user=user)
      return SavedPlace.objects.filter(category=category).order_by('-created_at')
    except UserCategory.DoesNotExist:
      return []
  
  @login_required
  def resolve_saved_place(self, info, id):
    user = info.context.user
    try:
      return SavedPlace.objects.get(id=id, category__user=user)
    except SavedPlace.DoesNotExist:
      return None

  def resolve_place_info_by_name(self, info, name, address):
    try:
      return PlaceInfo.objects.get(name=name, address=address)
    except PlaceInfo.DoesNotExist:
      return None

  def resolve_get_place_info_by_name(self, info, name, address, language):
    prompt = """
      당신은 한국 방문 관광객을 위한 맛집 안내 AI입니다.
      아래의 장소에 대해서 당신이 제공해야 할 것은 종류(장소라면 종류, 식당이라면 음식 종류), 메뉴(장소라면 티켓 정보, 식당이라면 음식)와 가격, 리뷰입니다.
      메뉴는 10개, 리뷰는 20개 이상 네이버 검색엔진을 우선적으로 탐색하세요.
      부가적인 설명은 필요없습니다. 답은 오직 아래의 json 형식으로 답하세요.
      아래에 제공된 언어로 번역하여 답하세요.
      코드 블록 기호(```json```) 없이 순수 JSON 텍스트만 출력하세요.

      {{
        "title": "장소 이름",
        "category": "종류",
        "menu": [{{"name": "치즈버거", "price": "8000원"}}],
        "reviews": ["너무 맛있어요.", "청결해요"]
      }}

      장소 이름: {name}
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