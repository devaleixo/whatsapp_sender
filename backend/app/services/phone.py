import re
from typing import Optional


COUNTRY_CODES = {
    "1": 11,
    "44": 12,
    "49": 12,
    "33": 11,
    "34": 11,
    "351": 12,
    "39": 12,
    "52": 12,
    "54": 12,
    "55": 12,
    "56": 11,
    "57": 12,
    "58": 12,
    "61": 11,
    "81": 12,
    "86": 13,
    "91": 12,
    "971": 12,
}


def to_e164(phone: str) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits or len(digits) < 8:
        return None

    # 10-11 digits → BR local (DDD + número), prepend 55
    if 10 <= len(digits) <= 11:
        return f"55{digits}"

    # 12+ digits → try to detect country code
    for code, expected_len in COUNTRY_CODES.items():
        if digits.startswith(code) and len(digits) >= expected_len:
            return digits

    if len(digits) >= 12:
        return digits

    return None
