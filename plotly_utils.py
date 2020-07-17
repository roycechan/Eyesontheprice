import plotly.graph_objects as go
import bot
import numpy as np
import logging
from datetime import datetime
import shutil
import string
import db_models
import sys

IMAGE_DESTINATION = "images/"
SAMPLE_IMAGE_URL = f"{IMAGE_DESTINATION}sample.png"

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def plot(date_lists, price_lists, variants, items, chart_name='Price Change'):

    labels = [string.ascii_uppercase[i] for i in range(0, len(variants))]

    fig = go.Figure()

    for i, price_list in enumerate(price_lists):
        fig.add_trace(go.Scatter(
            x=date_lists[i],
            y=price_list,
            mode="lines",
            connectgaps=True,
            name=labels[i] + ": " + items[i][:30] + "...- " + variants[i][:30],
            showlegend=True
        )
        )

    # format axis
    fig.update_layout(
        yaxis=dict(
            zeroline=False,
            showline=False,
            showticklabels=False,
        ),
        autosize=False,
        width=500,
        height=500,
        margin=dict(
            autoexpand=True,
            l=50,
            r=100,
            t=50,
        ),
    )

    # add legend
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="auto",
        x=-0.05,
        font=dict(
            size=12,
            color="black"
        ),
    ))

    # add annotations
    annotations = []

    for price_list, label in zip(price_lists, labels):
        annotations.append(dict(xref='paper', x=-0.05, y=price_list[0],
                                xanchor='left', yanchor='bottom',
                                text='{}: ${}'.format(label, price_list[0]),
                                font=dict(size=12),
                                showarrow=False))

        annotations.append(dict(xref='paper', x=1, y=price_list[-1],
                                xanchor='left', yanchor='middle',
                                text='${} ({:.0%})'.format(price_list[-1],
                                                           ((price_list[-1] / price_list[0])) - 1),
                                font=dict(size=12),
                                showarrow=False))

    # add title
    annotations.append(dict(xref='paper', yref='paper', x=0.0, y=1.05,
                            xanchor='left', yanchor='bottom',
                            text=chart_name,
                            font=dict(size=18,
                                      color='rgb(37,37,37)'),
                            showarrow=False))

    fig.update_layout(annotations=annotations)

    return fig


def update_image(chat_id, message_id, chart_name="Price Change"):
    # retrieve chart
    save_url = f"{IMAGE_DESTINATION}{chat_id}_{message_id}.png"
    chart = db_models.Chart.objects.get(chart_id=message_id, chat_id=chat_id)

    date_lists = []
    price_lists = []
    variants = []
    items = []
    created_prices = []
    created_dates = []

    for variant in chart.variants:
        if len(variant.date_list) > 0:
            date_lists.append(variant.date_list)
            price_lists.append(variant.price_list)
            variants.append(variant.variant_name)
            items.append(variant.item_name)
            created_prices.append(variant.created_price)
            created_dates.append(variant.created_time.date())
            # print("variant added")

    # print(date_lists)
    if any(date_lists):
        # print("plotting")
        fig = plot(date_lists, price_lists, variants, items, chart_name)
        fig.write_image(save_url)
        logger.info(f"Image saved to: {save_url}")
        labels = [string.ascii_uppercase[i] for i in range(0, len(variants))]
        current_prices = [i[-1] for i in price_lists]
        price_changes = [((ai/bi)-1) for ai,bi in zip(current_prices, created_prices)]
        return save_url, labels, current_prices, price_changes, created_dates
    else:
        return None


def generate_photo_url(update, context):
    chart_name = context.chat_data['chart_name']
    chat_id = str(update.message.chat.id)
    TEMP_SAVE_URL = f"{IMAGE_DESTINATION}{chat_id}_temp.png"

    # check for existing charts
    date_lists = []
    price_lists = []
    variants = []
    items = []
    # logger.info(context.chat_data['chosen_variants'])
    for chosen_variant in context.chat_data['chosen_variants']:
        try:
            logger.info(chosen_variant['variant_id'])
            variant = db_models.ItemVariant.objects.get(_id=chosen_variant['variant_id'])

            variants.append(variant.variant_name)
            items.append(variant.item_name)
            if variant.date_list:
                date_lists.append(variant.date_list)
                price_lists.append(variant.price_list)
                logger.info(f"Found {variant.variant_name}")
        except db_models.ItemVariant.DoesNotExist:
            variant = None

    # if any variant already tracked before, display price history
    if len(date_lists) > 0:
        fig = plot(date_lists, price_lists, variants, items, chart_name)
        fig.write_image(TEMP_SAVE_URL)
        # chart = open(TEMP_SAVE_URL, "rb")
        update.message.reply_text("Hurray! Someone else was tracking the same items. Showing you the full price history. Check back daily for updates!")
        return TEMP_SAVE_URL
    # plot sample figure
    else:
        update.message.reply_text("Here's a sample of what the chart will look like after some time. Check back again tomorrow!")
        # chart = open(SAMPLE_IMAGE_URL, "rb")
        return SAMPLE_IMAGE_URL

    # Store in context
    context.chat_data['chart_id'] = chart_id
    logger.info(f"CONTEXT: chart_id:{chart_id}")
