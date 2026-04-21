import reflex as rx

config = rx.Config(
    app_name="buddhi_ai_server",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)