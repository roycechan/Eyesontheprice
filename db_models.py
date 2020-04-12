import mongoengine
from datetime import datetime

#
class Price(mongoengine.EmbeddedDocument):
    date = mongoengine.DateField()
    price = mongoengine.DecimalField()


# variants
class ItemVariant(mongoengine.DynamicDocument):
    variant_id = mongoengine.StringField(required=True, primary_key=True)
    variant_name = mongoengine.StringField()
    item_id = mongoengine.StringField(required=True)
    item_name = mongoengine.StringField()
    channel = mongoengine.StringField()
    created_time = mongoengine.DateTimeField()
    last_updated_time = mongoengine.DateTimeField()
    current_price = mongoengine.DecimalField()
    price_history = mongoengine.EmbeddedDocumentListField(Price)
    price_history_full = mongoengine.ListField(mongoengine.DecimalField())
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


# 1 Chat: M ChartMessages; 1 ChartMessage: M ChatItemVariants
class ChatItemVariant(mongoengine.EmbeddedDocument):
    variant_id = mongoengine.StringField(required=True, primary_key=True)
    channel = mongoengine.StringField()
    item_name = mongoengine.StringField()
    variant_name = mongoengine.StringField()
    chat_item_variant_created_time = mongoengine.DateTimeField()
    last_updated_time = mongoengine.DateTimeField()
    # to be replicated from ItemVariant periodically
    created_time = mongoengine.DateTimeField()
    current_price = mongoengine.DecimalField()
    price_history_full = mongoengine.ListField(mongoengine.DecimalField())
    currency = mongoengine.StringField()
    stock = mongoengine.IntField()
    price_change = mongoengine.DecimalField()
    price_change_percent = mongoengine.FloatField()
    meta = {
        'collection': 'variants',
        'indexes': [
            'item_id'
        ]
    }


# charts
class ChartMessage(mongoengine.EmbeddedDocument):
    # chart id = message id
    chart_message_id = mongoengine.StringField(required=True, primary_key=True)
    variants = mongoengine.EmbeddedDocumentListField(ChatItemVariant)
    threshold = mongoengine.IntField()
    price_changes = mongoengine.ListField(mongoengine.DecimalField())
    price_changes_percent = mongoengine.ListField(mongoengine.FloatField())
    meta = {
        'collection': 'charts'
    }


class Chat(mongoengine.DynamicDocument):
    # chat_id
    chat_id = mongoengine.StringField(required=True, primary_key=True)
    chat_created_time = mongoengine.DateTimeField()
    user_id = mongoengine.StringField()
    user_first_name = mongoengine.StringField()
    user_username = mongoengine.StringField()
    chart_messages = mongoengine.EmbeddedDocumentListField(ChartMessage)
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

