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

INITIAL_CHOICE, DISPLAY_VARIANTS, PROMPT_URL, LOCATION, BIO = range(5)
SUPPORTED_CHANNELS = ['shopee']
reply_keyboard = [['Compare Prices', 'Track Prices']]


def start(update, context):
    update.message.reply_text(
        'Hi! My name is Pricey. I make it easy for you to compare and track prices across platforms '
        'Send /cancel to stop talking to me.\n\n'
        'What can I do for you today?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return INITIAL_CHOICE


def prompt_url(update, context):
    user = update.message.from_user
    logger.info("%s chose: %s", user.first_name, update.message.text)
    update.message.reply_text('I see! Please enter a valid shopee URL',
                              reply_markup=ReplyKeyboardRemove())

    return PROMPT_URL


def get_url(update, context):
    user = update.message.from_user
    logger.info("%s entered URL: %s", user.first_name, update.message.text)
    # Extract URL
    p = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    url_list = p.findall(update.message.text)
    if not url_list:
        update.message.reply_text('Oops! You did not key in a valid URL...',
                                  "Let's try again!",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
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
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return INITIAL_CHOICE
        else:
            update.message.reply_text('Brb! Fetching product variants...')

        return DISPLAY_VARIANTS

def display_variants(update, context):
    # Get variants from previous method

    # Fetch variants

    user = update.message.from_user
    logger.info("%s entered URL: %s", user.first_name, search_url)

    return BIO


def photo(update, context):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('user_photo.jpg')
    logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
    update.message.reply_text('Gorgeous! Now, send me your location please, '
                              'or send /skip if you don\'t want to.')

    return LOCATION


def skip_photo(update, context):
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)
    update.message.reply_text('I bet you look great! Now, send me your location please, '
                              'or send /skip.')

    return LOCATION


def location(update, context):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    update.message.reply_text('Maybe I can visit you sometime! '
                              'At last, tell me something about yourself.')

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
        entry_points=[CommandHandler('start', start)],

        states={
            INITIAL_CHOICE: [MessageHandler(Filters.regex('^(Compare Prices|Track Prices)$'), prompt_url)],
            #
            # PHOTO: [MessageHandler(Filters.photo, photo),
            #         CommandHandler('skip', skip_photo)],

            PROMPT_URL: [MessageHandler(Filters.text, get_url)],

            DISPLAY_VARIANTS: [MessageHandler(Filters.regex('^(Compare Prices|Track Prices)$'), display_variants())],

            LOCATION: [MessageHandler(Filters.location, location),
                       CommandHandler('skip', skip_location)],

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