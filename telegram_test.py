#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import plotly_test
import utils, db_utils, shopee_utils
import logging
from credentials import TELEGRAM_TOKEN
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
import telegram
from datetime import datetime
import os
import shutil


bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

INITIAL_CHOICE, CHOOSE_THRESHOLD, CHOOSE_VARIANT, STORE_THRESHOLD, BIO = range(5)
SUPPORTED_CHANNELS = ['shopee']
start_reply_keyboard = [['Compare Prices', 'Track Prices']]
frequency_reply_keyboard = ['When price drops by more than 10%',
                            'When price drops by more than 20%',
                            'When price drops by more than 30%',
                            "Don't need to update me"]


def start(update, context):
    update.message.reply_text(
        'Hi! My name is Pricey. I make it easy for you to compare and track prices across platforms '
        'Send /cancel to stop talking to me.\n\n'
        'What can I do for you today?',
        reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))

    return INITIAL_CHOICE


def compare(update, context):
    return INITIAL_CHOICE


def track(update, context):
    return INITIAL_CHOICE


def prompt_url(update, context):
    # store char id and user data
    user = update.message.from_user
    context.chat_data['user'] = user
    context.chat_data['chat_id'] = str(update.message.chat.id)
    logger.info(f"Stored user: {context.chat_data['user']} and chat_id: {context.chat_data['chat_id']}")

    logger.info("%s chose: %s", user.first_name, update.message.text)
    update.message.reply_text('All right! Please paste a Shopee product URL from either the app or online',
                              reply_markup=ReplyKeyboardRemove())

    return CHOOSE_VARIANT


def get_url_and_display_variant(update, context):
    user = update.message.from_user
    # check if it's a photo since photo and caption are shared from app
    if update.message.photo:
        # Extract caption
        caption = update.message.caption
        logger.info(f"{user.first_name} entered photo with caption: {caption}")
        # Extract URL
        url_list = utils.extract_url(caption)

    else:
        logger.info(f"{user.first_name} entered text: {update.message.text}")
        # Extract URL
        url_list = utils.extract_url(update.message.text)

    if not url_list:
        update.message.reply_text('Oops! You did not key in a valid URL...\n\n'
                                  "Let's try again!",
                                  reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
        return INITIAL_CHOICE
    else:
        search_url = url_list[0]
        logger.info("Bot extracted URL: %s", search_url)
        # store URL in chat_data
        context.chat_data['search_url'] = search_url
        context.chat_data['channel'] = utils.extract_domain(search_url)
        logger.info(f"CONTEXT: search_url: {search_url}, channel: {context.chat_data['channel']}")

        if context.chat_data['channel'] not in SUPPORTED_CHANNELS:
            update.message.reply_text('Oops! You did not key in a valid URL...',
                                      "Let's try again!",
                                      reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
            return INITIAL_CHOICE
        else:
            update.message.reply_text('Brb! Fetching product variants...')

            if context.chat_data['channel'] == "shopee":
                item_json = shopee_utils.get_shopee_json(search_url)
                item_dict, variants, variants_display = shopee_utils.get_shopee_variants(item_json)

                logger.info(f"Bot found item: {item_dict['item_name']} with variants: {variants_display}")

                update.message.reply_markdown(f'Hurray! We found \n\n`{item_dict["item_name"]}`\n\n'
                                          'Which variant would you like to track?',
                                          reply_markup=ReplyKeyboardMarkup.from_column(variants_display,
                                                                           one_time_keyboard=True))

                logger.info(f"Bot prompted {user.first_name} for variant choice")

                # Store item in context
                context.chat_data['item'] = item_dict
                context.chat_data['variants'] = variants
                context.chat_data['variants_displayed'] = variants_display
                logger.info(f"CONTEXT: item: {context.chat_data['item']['item_name']}, variants, variants_display")
                # Store item details in DB
                db_utils.add_item(item_dict)
                logger.info(f"DB: Item {item_dict['item_id']} stored")

                return CHOOSE_THRESHOLD


def get_variant_and_display_threshold(update, context):
    user = update.message.from_user
    # Get index of chosen variant
    chosen_variant = update.message.text

    variants_displayed = context.chat_data['variants_displayed']
    if chosen_variant in variants_displayed:
        chosen_variant_index = variants_displayed.index(chosen_variant)
        logger.info("%s chose variant %s: %s", user.first_name, chosen_variant_index, chosen_variant)

        context.chat_data['chosen_variant'] = chosen_variant
        context.chat_data['chosen_variant_index'] = chosen_variant_index
        logger.info(f"CONTEXT: chosen variant: {chosen_variant}, index: {chosen_variant_index}")
        # Store item variant
        db_utils.add_item_variant(context)
        logger.info(f"DB: ItemVariant {chosen_variant_index} stored")

        # Display frequency
        update.message.reply_text(f'Would you like to receive updates when the price drops?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(frequency_reply_keyboard,
                                                                               one_time_keyboard=True))
        logger.info(f"Bot prompted {user.first_name} for notification threshold")

    return STORE_THRESHOLD


def get_threshold(update, context):
    user = update.message.from_user
    chosen_threshold = update.message.text
    if chosen_threshold in frequency_reply_keyboard:
        logger.info("%s chose threshold: %s", user.first_name, chosen_threshold)
        parsed_threshold = parse_threshold(chosen_threshold)

        # Store
        context.chat_data['threshold'] = parsed_threshold
        context.chat_data['user'] = user
        logger.info(f"CONTEXT: threshold:{parsed_threshold}, user:{user}")

        # todo set callback details
        update.message.reply_markdown(f"Super! You've chosen to track: \n\n`{context.chat_data['item']['item_name']}`\n\n"
                                      f"_Variant_: {context.chat_data['chosen_variant']}\n"
                                      f"_Notifications_: {chosen_threshold}\n\n"
                                      "The chart below will update daily. Check back again tomorrow!")
        send_first_graph(update, context)
        logger.info("Bot sent first chart")
    return ConversationHandler.END


def send_first_graph(update, context):
    # Extract details from context
    index = context.chat_data['chosen_variant_index']
    item_variant = context.chat_data["variants"][index]
    current_price = item_variant['current_price']
    variant_id = item_variant['variant_id']
    chat_id = str(update.message.chat.id)

    # Create image
    photo_url = plotly_test.create_image_test(variant_id=variant_id, chat_id=chat_id)
    # update.message.reply_photo(photo=open("images/fig1.png", "rb"))
    photo = open(photo_url, "rb")
    updated_date = datetime.date(datetime.now())
    message = bot.send_photo(chat_id=update.message.chat.id,
                   photo=photo,
                   parse_mode='Markdown',
                   caption=f"_Last updated:_ ${current_price:.2f} on {updated_date}")
    chart_message_id = str(message.message_id)
    photo_url_new = f"{plotly_test.IMAGE_DESTINATION}{variant_id}_{chat_id}_{chart_message_id}.png"
    # Update photo url with message id
    photo.close()
    shutil.move(photo_url, photo_url_new)

    # Store in context
    context.chat_data['chart_message_id'] = chart_message_id
    logger.info(f"CONTEXT: chart_message_id:{chart_message_id}")
    # Store in db chat, chart, chart variant
    db_utils.add_chat(context)
    logger.info(f"DB: Chat stored. chat_id {chat_id}, chart_message {chart_message_id}, variant {variant_id}")


def parse_threshold(string):
    if string is not "Don't need to update me":
        # extract number X from string with X%
        threshold = string.split()[-1].split('%')[0]
        return threshold
    else:
        return None


def photo(update, context):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    print(photo_file)
    print(update.message.photo)
    photo_file.download('user_photo.jpg')
    logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
    update.message.reply_text('Gorgeous! Now, send me your location please, '
                              'or send /skip if you don\'t want to.')

    return BIO


def skip_photo(update, context):
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)
    update.message.reply_text('I bet you look great! Now, send me your location please, '
                              'or send /skip.')

    return BIO


def skip_location(update, context):
    user = update.message.from_user
    logger.info("User %s did not send a location.", user.first_name)
    update.message.reply_text('You seem a bit paranoid! '
                              'At last, tell me something about yourself.')

    return BIO


def bio(update, context):
    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)
    update.message.reply_text('Thank you! I hope we can talk again some day.')

    return ConversationHandler.END


def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                      CommandHandler('compare', prompt_url),
                      CommandHandler('track', prompt_url)
                      ],

        states={
            INITIAL_CHOICE: [MessageHandler(Filters.regex('^(Compare Prices|Track Prices)$'), prompt_url),
                             ],

            CHOOSE_VARIANT: [MessageHandler(Filters.all, get_url_and_display_variant)],

            CHOOSE_THRESHOLD: [MessageHandler(Filters.text, get_variant_and_display_threshold)
                               ],

            STORE_THRESHOLD: [MessageHandler(Filters.text, get_threshold)],

            BIO: [MessageHandler(Filters.text, bio)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    db = db_utils.db_connect("eyesontheprice")
    main()