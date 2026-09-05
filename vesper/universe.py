from collections import Counter


def reference_universe(records):
    eligible, rejected = {}, Counter()
    for row in records:
        reason = None
        if row.get("market") != "stocks" or row.get("locale") != "us":
            reason = "NON_US_OR_OTC"
        elif row.get("type") != "CS":
            reason = "NOT_COMMON_STOCK"
        elif not row.get("active"):
            reason = "INACTIVE_ON_REQUESTED_DATE"
        elif not row.get("primary_exchange") or not row.get("ticker"):
            reason = "BROKEN_REFERENCE"
        elif row.get("currency_name", "usd").lower() != "usd":
            reason = "NON_USD"
        if reason:
            rejected[reason] += 1
        else:
            eligible[row["ticker"]] = row
    return eligible, dict(rejected)


def split_return(entry, exit_price, shares_per_original=1, cash_per_original=0):
    if min(entry, exit_price, shares_per_original) <= 0:
        raise ValueError("Positive prices and split ratio required")
    return (exit_price * shares_per_original + cash_per_original) / entry - 1
