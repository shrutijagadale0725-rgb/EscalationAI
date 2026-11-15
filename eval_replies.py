"""Accuracy check for company-reply classification (accepted / partial / rejected / stalling / unclear).

Run from the agent folder:   python eval_replies.py
Scores the always-available regex classifier, and the model-backed one too when GROQ_API_KEY is set.
Hand-labelled; extend it with real replies you receive -- that is how the numbers stay honest.
"""
import os
from pathlib import Path

try:  # load GROQ_API_KEY from .env if present, without needing python-dotenv
    for line in Path(".env").read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "GROQ_API_KEY" and v.strip() and not os.getenv("GROQ_API_KEY"):
            os.environ["GROQ_API_KEY"] = v.strip().strip('"\'')
except OSError:
    pass

from escalation_agent import nlu

CASES = [
    # accepted
    ("Seller said they will refund the full amount to my account", "accepted"),
    ("Flipkart approved the return and the refund has been initiated", "accepted"),
    ("They agreed to send a replacement pair", "accepted"),
    ("We have approved your request. Refund will be credited in 5 working days.", "accepted"),
    ("customer care accepted the complaint and arranged a replacement", "accepted"),
    # partial
    ("They only offered a 30% refund", "partial"),
    ("Support said they can give a Rs 500 voucher instead", "partial"),
    ("They offered me a discount coupon for the next order", "partial"),
    ("The company will refund half and keep the rest as a restocking fee", "partial"),
    ("We cannot refund the amount but we can offer store credit.", "partial"),
    # rejected
    ("Meesho rejected my complaint saying the return window is over", "rejected"),
    ("They denied the claim, it is not covered under warranty", "rejected"),
    ("We are unable to process a refund for this product.", "rejected"),
    ("Seller refused to take the item back", "rejected"),
    ("The grievance officer declined my request", "rejected"),
    ("Your order is not eligible for a refund as per our policy.", "rejected"),
    # stalling
    ("They said they are looking into it and will update me", "stalling"),
    ("Got an automated email: your ticket has been received", "stalling"),
    ("We will get back to you within 2-3 working days.", "stalling"),
    ("Support told me the matter is under review, please wait", "stalling"),
    ("They forwarded my issue to the concerned team", "stalling"),
    # unclear
    ("They replied but it was a long message I did not understand", "unclear"),
    ("Seller sent me a link", "unclear"),
    ("They called me", "unclear"),
]


def score(name, fn):
    wrong = [(t, want, fn(t)) for t, want in CASES if fn(t) != want]
    ok = len(CASES) - len(wrong)
    print(f"{name}: {ok}/{len(CASES)} correct ({100 * ok // len(CASES)}%)")
    for t, want, got in wrong:
        print(f"   MISS  {t!r}\n         wanted {want}, got {got}")


if __name__ == "__main__":
    score("regex classifier (works offline)", nlu.regex_reply_kind)
    if os.getenv("GROQ_API_KEY"):
        score("model classifier (Groq, regex fallback)", nlu.classify_reply)
    else:
        print("model classifier: skipped (no GROQ_API_KEY)")