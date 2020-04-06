import mongoengine
from datetime import datetime


# variants
class ItemVariant(mongoengine.DynamicDocument):
    variant_id = mongoengine.StringField(required=True, primary_key=True)
    variant_name = mongoengine.StringField()
    item_id = mongoengine.StringField(required=True)
    item_name = mongoengine.StringField()
    channel = mongoengine.StringField()
    created_time = mongoengine.DateTimeField()
    last_updated_time = mongoengine.DateTimeField(default=datetime.now())
    last_updated_price = mongoengine.DecimalField()
    price_list = mongoengine.ListField(mongoengine.DecimalField())
    currency = mongoengine.StringField()
    shop_id = mongoengine.StringField()
    stock = mongoengine.IntField()
    chat_ids = mongoengine.ListField(mongoengine.StringField())
    price_change = mongoengine.DecimalField()
    price_change_percent = mongoengine.FloatField()
    meta = {
        'collection': 'variants',
        'indexes': [
            'item_id'
        ]
    }


# chats
class ChatVariant(mongoengine.EmbeddedDocument):
    # message id of chart
    message_id = mongoengine.StringField(required=True, primary_key=True)
    variant_id = mongoengine.StringField(required=True)
    variant_name = mongoengine.StringField()
    item_id = mongoengine.StringField(required=True)
    item_name = mongoengine.StringField()
    channel = mongoengine.StringField()
    created_time = mongoengine.DateTimeField()
    last_updated_time = mongoengine.DateTimeField(default=datetime.now())
    last_updated_price = mongoengine.DecimalField()
    price_list = mongoengine.ListField(mongoengine.DecimalField())
    currency = mongoengine.StringField()
    shop_id = mongoengine.StringField()
    stock = mongoengine.IntField()
    price_change = mongoengine.DecimalField()
    meta = {
        'indexes': [
            'variant_id'
        ]
    }


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
    currency = mongoengine.StringField()
    categories = mongoengine.ListField(mongoengine.StringField())
    variant_ids = mongoengine.ListField(mongoengine.StringField())
    item_brand = mongoengine.StringField()
    item_sold = mongoengine.IntField()
    item_rating = mongoengine.DecimalField()
    item_stock = mongoengine.IntField()
    meta = {
        'collection': 'items'
    }


# charts
class Charts(mongoengine.DynamicDocument):
    message_id = mongoengine.StringField(required=True, primary_key=True)
    variants = mongoengine.ListField(mongoengine.EmbeddedDocumentField(ChatVariant))
    meta = {
        'collection': 'charts'
    }