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
import utils
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

INITIAL_CHOICE, CHOOSE_FREQUENCY, CHOOSE_VARIANT, STORE_FREQUENCY, BIO = range(5)
SUPPORTED_CHANNELS = ['shopee']
start_reply_keyboard = [['Compare Prices', 'Track Prices']]
frequency_reply_keyboard = ['When price drops by more than 5%', 'When price drops by more than 10%', "Don't need to update me"]


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
    user = update.message.from_user
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
        logger.info("Extracted URL: %s", search_url)
        # store URL in chat_data
        context.chat_data['search_url'] = search_url
        # Extract domain
        context.chat_data['channel'] = utils.extract_domain(search_url)

        logger.info(context.chat_data)

        if context.chat_data['channel'] not in SUPPORTED_CHANNELS:
            update.message.reply_text('Oops! You did not key in a valid URL...',
                                      "Let's try again!",
                                      reply_markup=ReplyKeyboardMarkup(start_reply_keyboard, one_time_keyboard=True))
            return INITIAL_CHOICE
        else:
            update.message.reply_text('Brb! Fetching product variants...')

            if context.chat_data['channel'] == "shopee":
                parameters = utils.extract_shopee_identifiers(context.chat_data['search_url'])
                shopee_item_details = utils.retrieve_item_details_json(
                    utils.build_search_url(utils.SHOPEE_SEARCH_LINK, parameters))
                # todo: Store item details in DB
                item_name = shopee_item_details['item']['name']
                context.chat_data['product_name'] = item_name
                logger.info("Item name: %s", item_name)
                # Fetch variants
                variant_display = []
                variants = []
                for variant in shopee_item_details['item']['models']:
                    variant_dict = {}
                    variant_dict['id'] = variant['itemid']
                    variant_dict['name'] = variant['name'].title()
                    variant_dict['price'] = variant['price'] / 100000
                    variant_dict['quantity'] = variant['stock']
                    option = (f"{variant_dict['name']} - ${variant_dict['price']:.2f} ({variant_dict['quantity']} left)")
                    variants.append(variant_dict)
                    variant_display.append(option)
                logger.info("Variants: %s", variant_display)
                context.chat_data['variants'] = variants
                context.chat_data['variants_displayed'] = variant_display

                # if list is empty, display main product price
                if not variants:
                    variant_dict = {}
                    variant_dict['id'] = shopee_item_details['item']['itemid']
                    variant_dict['name'] = item_name
                    variant_dict['price'] = shopee_item_details['item']['price'] / 100000
                    variant_dict['quantity'] = shopee_item_details['item']['stock']
                    option = (f"{variant_dict['name']} - ${variant_dict['price']:.2f} ({variant_dict['quantity']} left)")
                    variants.append(variant_dict)
                    variant_display.append(option)
                    context.chat_data['variants'] = variants
                    context.chat_data['variants_displayed'] = variant_display

                update.message.reply_markdown(f'Hurray! We found \n\n`{item_name}`\n\n'
                                          'Which variant would you like to track?',
                                          reply_markup=ReplyKeyboardMarkup.from_column(variant_display,
                                                                           one_time_keyboard=True))

                return CHOOSE_FREQUENCY


def get_variant_and_display_frequency(update, context):
    user = update.message.from_user
    chosen_variant = update.message.text
    context.chat_data['chosen_variant'] = chosen_variant
    variants_displayed = context.chat_data['variants_displayed']
    if chosen_variant in variants_displayed:
        chosen_variant_index = variants_displayed.index(chosen_variant)
        context.chat_data['chosen_variant_index'] = chosen_variant_index
        logger.info("%s chose variant %s: %s", user.first_name, chosen_variant_index, chosen_variant)
        #todo Store variant that user wants to track in DB

        # Display frequency
        update.message.reply_text(f'Would you like to receive updates when the price drops?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(frequency_reply_keyboard,
                                                                               one_time_keyboard=True))
    return STORE_FREQUENCY


def get_frequency(update, context):
    user = update.message.from_user
    chosen_threshold = update.message.text
    context.chat_data['chosen_threshold'] = chosen_threshold
    if chosen_threshold in frequency_reply_keyboard:
        chosen_threshold_index = frequency_reply_keyboard.index(chosen_threshold)
        logger.info("%s chose thresholds %s: %s", user.first_name, chosen_threshold_index, chosen_threshold)
        logger.info(user)
        # todo Store user details
        # todo set callback details
        update.message.reply_markdown(f"Super! You've chosen to track: \n\n`{context.chat_data['product_name']}`\n\n"
                                      f"_Variant_: {context.chat_data['chosen_variant']}\n"
                                      f"_Notifications_: {context.chat_data['chosen_threshold']}\n\n"
                                      "This chart will update daily. Check back again tomorrow!")
        send_first_graph(update, context)
    return ConversationHandler.END


def send_first_graph(update, context):
    chat_id = str(update.message.chat.id)

    # Get price
    chosen_variant_index = context.chat_data['chosen_variant_index']
    chosen_variant_price = context.chat_data['variants'][chosen_variant_index]['price']
    chosen_variant_id = context.chat_data['variants'][chosen_variant_index]['id']
    # Get photo
    photo_url = plotly_test.create_image_test(variant_id=chosen_variant_id, chat_id=chat_id)
    # update.message.reply_photo(photo=open("images/fig1.png", "rb"))
    photo = open(photo_url, "rb")
    updated_date = datetime.date(datetime.now())
    msg = bot.send_photo(chat_id=update.message.chat.id,
                   photo=photo,
                   parse_mode='Markdown',
                   caption=f"_Last updated:_ ${chosen_variant_price:.2f} on {updated_date}")
    msg_id = str(msg.message_id)
    photo_url_new = f"{plotly_test.IMAGE_DESTINATION}{chosen_variant_id}_{chat_id}_{msg_id}.png"
    # Update photo url with message id
    photo.close()
    shutil.move(photo_url, photo_url_new)

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

            CHOOSE_FREQUENCY: [MessageHandler(Filters.text, get_variant_and_display_frequency)
                               ],

            STORE_FREQUENCY: [MessageHandler(Filters.text, get_frequency)],

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
    main()