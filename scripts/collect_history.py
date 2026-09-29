"""Download dated official result-page data; no private API or credentials needed."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

NAMES = ("LT_5/5", "LT_4/5+", "LT_4/5", "LT_3/5+B", "LT_3/5", "LT_2/5+")
TIERS = ("jackpot", "four_bonus", "four", "three_bonus", "three", "two_bonus")


def parse_draw(payload, expected, source):
    matches = [
        r
        for r in payload["results"]
        if r.get("gameId") == "lotto" and r.get("drawDate", "")[:10] == expected.isoformat()
    ]
    if len(matches) != 1 or matches[0]["status"] != "resulted":
        raise ValueError(f"Missing or ambiguous completed draw for {expected}")
    result = matches[0]["results"]
    wins = result["lottoWins"]
    if tuple(w["name"] for w in wins) != NAMES:
        raise ValueError(f"Unexpected prize categories for {expected}")
    if any(type(w[k]) is not int or w[k] < 0 for w in wins for k in ("amount", "winners")):
        raise ValueError(f"Invalid prize values for {expected}")
    return {
        "date": expected.isoformat(),
        "source": source,
        "winners": [w["winners"] for w in wins],
        "amounts": [w["amount"] for w in wins],
        "numbers": [int(n) for n in result["lottoNumbers"]],
        "bonus_numbers": [int(n) for n in result["bonusNumbers"]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 5, 24))
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.start < date(2025, 5, 18)
        or args.start > args.end
        or args.start.weekday() != 5
        or args.end.weekday() != 5
    ):
        parser.error("Use Saturday endpoints within the current rules period.")
    draws = []
    current = args.start
    while current <= args.end:
        year, week, _ = current.isocalendar()
        source = f"https://games.lotto.is/urslit/lotto?year={year}&week={week}"
        endpoint = (
            f"https://games.lotto.is/api/proxy/result/lotto?gameId=lotto&year={year}&week={week}"
        )
        with urlopen(
            Request(endpoint, headers={"User-Agent": "lotteryAnalyzer historical research"}),
            timeout=30,
        ) as response:
            draws.append(parse_draw(json.load(response), current, source))
            draws[-1]["data_source"] = endpoint
        print(current, flush=True)
        current += timedelta(days=7)
    data = {
        "observed_on": date.today().isoformat(),
        "rules_effective_from": "2025-05-18",
        "provenance": (
            "Public results endpoint used by lotto.is result pages; dates and "
            "category order verified. Winning rows are not unique players. "
            "Zero-winner amounts are displayed unwon pools."
        ),
        "tier_order": TIERS,
        "draws": draws,
    }
    args.output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
