import mongoengine
from datetime import datetime

# variants
class Variant(mongoengine.EmbeddedDocument):
    variant_id = mongoengine.StringField(required=True, primary_key=True)
    variant_name = mongoengine.StringField()
    item_id = mongoengine.StringField(required=True)
    item_name = mongoengine.StringField()
    channel = mongoengine.StringField()
    created_time = mongoengine.DateTimeField(default=datetime.now())
    last_updated_time = mongoengine.DateTimeField()
    price_list = mongoengine.ListField(mongoengine.DecimalField())
    currency_code = mongoengine.StringField()
    shop_id = mongoengine.StringField()
    stock = mongoengine.IntField()
    meta = {
        'collection': 'variants',
        'indexes': [
            'item_id'
        ]
    }


# chats
class ChatVariant(mongoengine.EmbeddedDocument):
    variant = mongoengine.ReferenceField(Variant)
    message_id = mongoengine.StringField()


class Chat(mongoengine.DynamicDocument):
    # chat_id
    chat_id = mongoengine.StringField(required=True, primary_key=True)
    user_first_name = mongoengine.StringField()
    user_username = mongoengine.StringField()
    user_variants = mongoengine.ListField(mongoengine.EmbeddedDocumentField(ChatVariant))
    meta = {
        'collection': 'chats'
    }


# items
class Item(mongoengine.DynamicDocument):
    item_id = mongoengine.StringField(required=True, primary_key=True)
    shop_id = mongoengine.StringField()
    item_name = mongoengine.StringField()
    item_description = mongoengine.StringField()
    channel = mongoengine.StringField()
    price_min = mongoengine.DecimalField()
    price_max = mongoengine.DecimalField()
    currency_code = mongoengine.StringField()
    categories = mongoengine.ListField(mongoengine.StringField())
    variant_ids = mongoengine.ListField(mongoengine.StringField())
    item_brand = mongoengine.StringField()
    item_sold = mongoengine.IntField()
    item_rating = mongoengine.IntField()
    item_stock = mongoengine.IntField()
    meta = {
        'collection': 'items'
    }


# charts
class Charts(mongoengine.DynamicDocument):
    message_id = mongoengine.StringField(required=True, primary_key=True)
    variants = mongoengine.ListField(mongoengine.EmbeddedDocumentField(Variant))
    meta = {
        'collection': 'charts'
    }