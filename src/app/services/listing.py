from app.models import *


def create_listing(*, title: str) -> Bundle:
    bundle = Bundle(title=title)
    # bundle.full_clean()
    bundle.save()
