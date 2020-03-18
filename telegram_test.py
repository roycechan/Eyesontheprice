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
import utils
import logging
import re
from credentials import TELEGRAM_TOKEN
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)

global search_url

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

INITIAL_CHOICE, CHOOSE_FREQUENCY, CHOOSE_VARIANT, STORE_FREQUENCY, BIO = range(5)
SUPPORTED_CHANNELS = ['shopee']
start_reply_keyboard = [['Compare Prices', 'Track Prices']]
frequency_reply_keyboard = ['Update me daily', 'Update me weekly','Update me only when the price drops']


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
    update.message.reply_text('I see! Please enter a valid shopee URL',
                              reply_markup=ReplyKeyboardRemove())

    return CHOOSE_VARIANT


def get_url_and_display_variant(update, context):
    user = update.message.from_user
    logger.info("%s entered for URL: %s", user.first_name, update.message.text)
    # Extract URL
    p = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    url_list = p.findall(update.message.text)
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
                variants = []
                for variant in shopee_item_details['item']['models']:
                    name = variant['name'].title()
                    price = variant['price'] / 100000
                    quantity = variant['stock']
                    option = (f'{name} - ${price:.2f} ({quantity} left)')
                    variants.append(option)
                logger.info("Variants: %s", variants)
                context.chat_data['variants_displayed'] = variants

                # if list is empty, display main product price
                if not variants:
                    price = shopee_item_details['item']['price'] / 100000
                    quantity = shopee_item_details['item']['stock']
                    option = (f'{item_name} - ${price:.2f} ({quantity} left)')
                    variants.append(option)

                update.message.reply_text(f'Hurray! We found {item_name}.\n\n'
                                          'Which variant would you like to track?',
                                          reply_markup=ReplyKeyboardMarkup.from_column(variants,
                                                                           one_time_keyboard=True))

                return CHOOSE_FREQUENCY


def get_variant_and_display_frequency(update, context):
    user = update.message.from_user
    chosen_variant = update.message.text
    context.chat_data['chosen_variant'] = chosen_variant
    variants_displayed = context.chat_data['variants_displayed']
    if chosen_variant in variants_displayed:
        chosen_variant_index = variants_displayed.index(chosen_variant)
        logger.info("%s chose variant %s: %s", user, chosen_variant_index, chosen_variant)
        #todo Store variant that user wants to track in DB

        # Display frequency
        update.message.reply_text(f'When should we update you again?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(frequency_reply_keyboard,
                                                                               one_time_keyboard=True))
    return STORE_FREQUENCY


def get_frequency(update, context):
    user = update.message.from_user
    chosen_frequency = update.message.text
    context.chat_data['chosen_frequency'] = chosen_frequency
    if chosen_frequency in frequency_reply_keyboard:
        chosen_frequency_index = frequency_reply_keyboard.index(chosen_frequency)
        logger.info("%s chose frequency %s: %s", user, chosen_frequency_index, chosen_frequency)
        # todo Store frequency that user wants to track in DB
        # todo Store user details
        # todo set callback details
        update.message.reply_text(f"Super! You've chosen to track {context.chat_data['product_name']}:\n\n"
                                  f"Product Variant: {context.chat_data['chosen_variant']}\n\n"
                                  f"Updates: {context.chat_data['chosen_frequency']}\n\n"
                                  "I'll end the conversation now, hit me up any time!")

    return ConversationHandler.END

def photo(update, context):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
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

            CHOOSE_VARIANT: [MessageHandler(Filters.text, get_url_and_display_variant)],

            CHOOSE_FREQUENCY: [MessageHandler(Filters.text, get_variant_and_display_frequency)],

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