from typing import Tuple, Dict, Optional
from i18naddress import normalize_address, InvalidAddressError

STATE_ABBREV = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA", "COLORADO": "CO",
    "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME",
    "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO",
    "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM",
    "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN",
    "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC", "AMERICAN SAMOA": "AS", "GUAM": "GU",
    "NORTHERN MARIANA ISLANDS": "MP", "PUERTO RICO": "PR", "UNITED STATES MINOR OUTLYING ISLANDS": "UM",
    "U.S. VIRGIN ISLANDS": "VI", "AL": "AL", "AK": "AK", "AZ": "AZ", "AR": "AR", "CA": "CA", "CO": "CO", "CT": "CT",
    "DE": "DE", "FL": "FL", "GA": "GA", "HI": "HI", "ID": "ID", "IL": "IL", "IN": "IN", "IA": "IA", "KS": "KS",
    "KY": "KY", "LA": "LA", "ME": "ME", "MD": "MD", "MA": "MA", "MI": "MI", "MN": "MN", "MS": "MS", "MO": "MO",
    "MT": "MT", "NE": "NE", "NV": "NV", "NH": "NH", "NJ": "NJ", "NM": "NM", "NY": "NY", "NC": "NC", "ND": "ND",
    "OH": "OH", "OK": "OK", "OR": "OR", "PA": "PA", "RI": "RI", "SC": "SC", "SD": "SD", "TN": "TN", "TX": "TX",
    "UT": "UT", "VT": "VT", "VA": "VA", "WA": "WA", "WV": "WV", "WI": "WI", "WY": "WY", "DC": "DC", "AS": "AS",
    "GU": "GU", "MP": "MP", "PR": "PR", "UM": "UM", "VI": "VI",
}


class Address:
    def __init__(
            self,
            city: str,
            city_area: str,
            country_area: str,
            country_code: str,
            postal_code: str,
            street_address: str,
            sorting_code: str = None
    ):
        self.city = city
        self.city_area = city_area
        self.state = country_area
        self.country_code = country_code
        self.postal_code = postal_code
        self.street_address = street_address
        self.sorting_code = sorting_code


def validate_address(
        state: str,
        city: str,
        postal_code: str,
        street_address: str,
        country: str = 'US'
) -> Tuple[Optional[Address], Optional[Dict[str, str]]]:
    try:
        response = normalize_address({
            'country_code': country,
            'country_area': state,
            'city': city,
            'postal_code': postal_code,
            'street_address': street_address
        })
        return Address(**response), {}
    except InvalidAddressError as e:
        error_messages = e.errors
        if 'country_area' in error_messages:
            error_messages.update({
                'state': error_messages.pop('country_area')
            })
        return None, error_messages


def validate_usps_address(
        state: str,
        city: str,
        postal_code: str,
        street_address: str,
        country: str = 'US',
        **kwargs
) -> Tuple[Optional[Address], Optional[Dict[str, str]]]:
    try:
        response = normalize_address({
            'country_code': country,
            'country_area': state[0] if type(state) is list else state,
            'city': city[0] if type(city) is list else city,
            'postal_code': postal_code[0] if type(postal_code) is list else postal_code,
            'street_address': street_address
        })
        return Address(**response), {}
    except InvalidAddressError as e:
        error_messages = e.errors
        if 'country_area' in error_messages:
            error_messages.update({
                'state': error_messages.pop('country_area')
            })
        return None, error_messages


def standardize_state(state: str) -> str:
    return STATE_ABBREV.get(state.upper())
