import plotly.graph_objects as go
import numpy as np

IMAGE_DESTINATION = "images/"

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