import plotly.graph_objects as go
import numpy as np
import logging
from datetime import datetime
import shutil

IMAGE_DESTINATION = "images/"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def create_image_test(variant_id, chat_id, message_id=""):
    np.random.seed(1)

    N = 100
    x = np.random.rand(N)
    y = np.random.rand(N)
    colors = np.random.rand(N)
    sz = np.random.rand(N) * 30

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers",
        marker=go.scatter.Marker(
            size=sz,
            color=colors,
            opacity=0.6,
            colorscale="Viridis"
        )
    ))

    save_url = f"{IMAGE_DESTINATION}{variant_id}_{chat_id}_{message_id}.png"
    # print(f"Image saved to: {save_url}")

    fig.write_image(save_url)
    return save_url


def send_first_graph(update, context):
    index = context.chat_data['chosen_variant_index']
    item_variant = context.chat_data["variants"][index]
    current_price = item_variant['current_price']
    variant_id = item_variant['variant_id']
    chat_id = str(update.message.chat.id)

    # Create image
    photo_url = create_image_test(variant_id=variant_id, chat_id=chat_id)
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