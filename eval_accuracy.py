"""Field-extraction accuracy on hand-labelled complaints (deterministic: no network, no Groq)."""
from escalation_agent import nlu

R = "\u20b9"  # rupee sign, kept as an escape so the file never depends on terminal encoding

EXTRACTION = [
    ("My earbuds from Amazon arrived broken, order OD-4471, Rs 2499",
     {"platform": "Amazon", "order_id": "OD-4471", "amount": "2499"}),
    ("I ordered a phone cover from Flipkart and it arrived cracked. Order ID is OD4417789, I paid Rs 599.",
     {"platform": "Flipkart", "order_id": "OD4417789", "amount": "599"}),
    ("I bought a kurta on Myntra three weeks ago. The refund was approved but the money never came back. Order no is 88213, Rs 1,499.",
     {"platform": "Myntra", "order_id": "88213", "amount": "1499"}),
    (f"My mixer grinder from Croma stopped working after two days. Order #C-90412, {R}3,200. They keep refusing the replacement.",
     {"platform": "Croma", "order_id": "C-90412", "amount": "3200"}),
    ("I got a wrong size of sneakers from Tata CLiQ. Order number 5521. Nobody replies to my emails.",
     {"platform": "Tata CLiQ", "order_id": "5521"}),
    ("My food delivery from Swiggy never arrived but I was charged Rs 450. The order id is 1002345.",
     {"platform": "Swiggy", "order_id": "1002345", "amount": "450"}),
    ("i ordered a pair of shoes from Roadster and lost track of the order...the order no is 24732",
     {"platform": "Roadster", "order_id": "24732"}),
    ("meesho sent me a torn saree, order MS-77123, paid 899 rupees",
     {"platform": "Meesho", "order_id": "MS-77123", "amount": "899"}),
    ("Nykaa delivered a leaking serum. Order number NY5509231. Rs. 1,250 charged.",
     {"platform": "Nykaa", "order_id": "NY5509231", "amount": "1250"}),
    (f"Received the wrong jacket from Ajio on 12 Oct. Order no AJ-33201, {R}2,999.",
     {"platform": "Ajio", "order_id": "AJ-33201", "amount": "2999"}),
    ("Zomato never delivered my order but charged me 380 rupees. Order ID ZM889120.",
     {"platform": "Zomato", "order_id": "ZM889120", "amount": "380"}),
    ("Blinkit delivered expired milk. Order 5521004, paid Rs 72.",
     {"platform": "Blinkit", "order_id": "5521004", "amount": "72"}),
    ("I bought a laptop from Reliance Digital. Order no is RD-5599. It stopped working in a week.",
     {"platform": "Reliance Digital", "order_id": "RD-5599"}),
    ("The tent I got from Decathlon has a broken zip. Order number 7788123, Rs 4,500.",
     {"platform": "Decathlon", "order_id": "7788123", "amount": "4500"}),
    ("Paid 2,499 rs for a phone on Amazon, order AZ-1001 never arrived",
     {"platform": "Amazon", "order_id": "AZ-1001", "amount": "2499"}),
    ("My package is late and nobody answers", {}),
    ("ordered shoes from bata, order no 4412",  # known limit: lowercase unlisted company is not guessed
     {"order_id": "4412"}),
    ("I ordered on Monday from the seller, order no 9981, Rs 350",
     {"order_id": "9981", "amount": "350"}),
    ("Charged Rs 1,299.50 twice on Myntra. Order MY-20045.",
     {"platform": "Myntra", "order_id": "MY-20045", "amount": "1299.50"}),
    ("The order arrived damaged from Flipkart, Rs 1,999.",
     {"platform": "Flipkart", "amount": "1999"}),
    ("Zomato charged rs5000 but never delivered. Order Z-1234.",
     {"platform": "Zomato", "order_id": "Z-1234", "amount": "5000"}),
    ("I ordered a watch on 12-09-2026 from Croma. Order no 7001, Rs 8,999.",
     {"platform": "Croma", "order_id": "7001", "amount": "8999"}),
]

ROUTING = [  # (message, case_id, status, expected tool)
    ("stop", "c123", "waiting", "log_response"),
    ("file it", "c123", "gate", "log_response"),
    ("show my letter", "c123", "draft_ready", "draft_escalation"),
    ("reopen it", "c123", "closed", "reopen_case"),
    ("get status", "c123", "waiting", "get_next_step"),
]

FIELDS = ("platform", "order_id", "amount")


def norm(k, v):
    return None if v is None else (str(v).strip().lower() if k == "platform" else str(v).strip().upper())


def main():
    hits = {f: 0 for f in FIELDS}
    exact, fails = 0, []
    for text, want in EXTRACTION:
        got = nlu.extract_fields(text)
        bad = [f for f in FIELDS if norm(f, got.get(f)) != norm(f, want.get(f))]
        for f in FIELDS:
            hits[f] += f not in bad
        if bad:
            fails.append((text, want, got))
        else:
            exact += 1
    n = len(EXTRACTION)
    print(f"Field extraction on {n} complaints")
    for f in FIELDS:
        print(f"  {f:9s} {hits[f]}/{n}")
    print(f"  all fields correct: {exact}/{n}")
    r = sum(nlu.regex_route(m, c, s)[0] == t for m, c, s, t in ROUTING)
    print(f"Command routing: {r}/{len(ROUTING)}")
    for text, want, got in fails:
        print(f"\nMISS: {text}\n  expected {want}\n  got      {got}")


if __name__ == "__main__":
    main()