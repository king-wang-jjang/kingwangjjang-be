from graphene import ObjectType, String, Schema, Field

class Query(ObjectType):
    hello = String(name=String(default_value="stranger"))

    def resolve_hello(self, info, name):
        return f"Hello {name}"

schema = Schema(query=Query)