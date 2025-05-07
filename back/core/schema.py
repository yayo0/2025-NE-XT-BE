import graphene
import requests, json

class MenuItemType(graphene.ObjectType):
  name = graphene.String()
  price = graphene.String()

class PlaceInfoType(graphene.ObjectType):
  title = graphene.String()
  category = graphene.String()
  menu = graphene.List(MenuItemType)
  reviews = graphene.List(graphene.String)


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello!")
    crawl_naver_place_info = graphene.Field(PlaceInfoType, keyword=graphene.String())


    def resolve_crawl_naver_place_info(self, info, keyword):
      url = 'https://3jxijkl3qbdfxmkvgphdhjh2g40bpjgv.lambda-url.ap-northeast-2.on.aws/'
      payload = { 'keyword': keyword }

      try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        title = data.get('title', '')
        category = data.get('category', '')

        # 메뉴 리스트 파싱
        menu_data = data.get('menu', [])
        menu_items = [
          MenuItemType(
            name=item.get('name', ''),
            price=item.get('price', '')
          ) for item in menu_data
        ]

        # 리뷰 리스트 파싱 (빈 문자열은 필터링)
        reviews_data = data.get('reviews', [])
        reviews_cleaned = [review.strip() for review in reviews_data if review.strip()]

        return PlaceInfoType(
          title=title,
          category=category,
          menu=menu_items,
          reviews=reviews_cleaned
        )
        
      except requests.exceptions.RequestException as e:
        print(f"Lambda 호출 실패: {e}")
        return None
      except Exception as e:
        print(f"응답 파싱 오류: {e}")
        return None



