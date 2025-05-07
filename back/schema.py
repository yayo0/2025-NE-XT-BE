import graphene

from back.core import schema as core_schema
from back.place import schema as place_schema
from back.common import schema as common_schema

class Query(
  core_schema.Query,
  place_schema.Query,
  common_schema.Query,
  graphene.ObjectType
):
  pass

class Mutation(
  place_schema.Mutation,
  common_schema.Mutation,
  graphene.ObjectType
):
  pass

schema = graphene.Schema(query=Query, mutation=Mutation)
