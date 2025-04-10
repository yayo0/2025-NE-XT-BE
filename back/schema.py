import graphene

from back.core import schema as core_schema

class Query(core_schema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
