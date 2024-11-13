class PRODUCT_STATUS:
    published = 'published'
    sold = 'sold'
    shipped = 'shipped'
    received = 'received'


class BUNDLE_TYPES:
    outgoing = 'outgoing'
    incoming = 'incoming'


class ORDER_ITEM_STATUS:
    active = 'a'            # Buyer purchased
    ready_to_ship = 's'     # Seller confirmed to ship
    label_pending = 'i'     # System is in progress of printing label
    label_printed = 'p'     # Postage label created(purchased)
    label_failure = 'f'     # Failed to print postage label
    in_transit = 't'        # In transit
    received = 'd'          # Delivered successfully
    canceled = 'c'          # Seller canceled for some reason
    in_return = 'r'         # Buyer needs to return
