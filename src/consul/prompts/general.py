from datetime import datetime

import pytz


def get_current_datetime() -> str:
    # TODO: move timezone into config
    now = datetime.now(pytz.timezone("Europe/Prague"))

    # Determine if it is CEST or CET
    timezone_abbr = "CEST" if now.dst() else "CET"

    return now.strftime(f"%A, %d-%m-%Y %H:%M {timezone_abbr}")
