"""Company-reply handling: accepted / partial / rejected / stalling, from classifier to case outcome."""
import pytest

from escalation_agent import nlu
from escalation_agent.service import CaseService


@pytest.fixture
def sent(tmp_path):
    """A service with one case whose letter to the seller has been sent; notices are captured."""
    notices = []
    svc = CaseService(str(tmp_path / "r.db"), polish=None,
                      notifier=lambda title, text, email=None: notices.append(text))
    cid = svc.start("earbuds", "Left bud is dead.", "Amazon", "OD-1", "2499")["case_id"]
    svc.respond(cid, {"action": "sent"})
    return svc, cid, notices


def reply(svc, cid, text, kind=None):
    return svc.respond(cid, {"action": "reply", "text": text, "kind": kind or nlu.regex_reply_kind(text)})


# ---- classifier -------------------------------------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("they approved my refund", "accepted"),
    ("refund has been initiated to your account", "accepted"),
    ("replacement will be dispatched tomorrow", "accepted"),
    ("they offered a 50% refund", "partial"),
    ("we can offer you a voucher", "partial"),
    ("we can't refund but can offer store credit", "partial"),
    ("your request has been denied", "rejected"),
    ("Amazon rejected my complaint, out of warranty", "rejected"),
    ("we cannot process a refund for this order", "rejected"),
    ("we are looking into it, please wait", "stalling"),
    ("we will get back to you in 2-3 business days", "stalling"),
    ("they said ok", "unclear"),
    ("", "unclear"),
])
def test_regex_reply_kind(text, kind):
    assert nlu.regex_reply_kind(text) == kind


def test_model_answer_is_validated_and_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(nlu, "_groq_json", lambda *a, **k: {"kind": "accepted"})
    assert nlu.classify_reply("anything") == "accepted"
    monkeypatch.setattr(nlu, "_groq_json", lambda *a, **k: {"kind": "banana"})  # invented label
    assert nlu.classify_reply("they rejected it") == "rejected"  # regex answers instead
    monkeypatch.setattr(nlu, "_groq_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    assert nlu.classify_reply("they approved my refund") == "accepted"


# ---- routing ----------------------------------------------------------------------------

@pytest.mark.parametrize("msg,event", [
    ("Amazon rejected my complaint", "seller_replied"),
    ("they offered a 50% refund", "seller_replied"),
    ("got a reply from the seller", "seller_replied"),
    ("escalate", "escalate"),
    ("I sent it", "sent"),
])
def test_waiting_messages_route_to_the_right_event(msg, event):
    tool, args = nlu.regex_route(msg, "c1", "waiting")
    assert tool == "log_response" and args["event"] == event


@pytest.mark.parametrize("msg", ["no reply from the seller yet", "they haven't replied", "it's 23rd Nov", "it's been 12 days"])
def test_silence_and_dates_are_not_replies(msg):
    assert nlu.regex_route(msg, "c1", "waiting")[0] == "get_next_step"


# ---- what the case does -----------------------------------------------------------------

def test_accepted_reply_resolves_the_case(sent):
    svc, cid, _ = sent
    v = reply(svc, cid, "they approved my refund")
    assert v["status"] == "resolved"
    assert any("agreed to your complaint" in t for t in v["timeline"])


def test_rejection_escalates_immediately_with_the_right_words(sent):
    svc, cid, notices = sent
    v = reply(svc, cid, "Amazon rejected my complaint")
    assert v["status"] == "draft_ready" and v["stage"] == "the platform's grievance officer"
    assert v["day"] == 0  # no waiting out the 7-day window
    assert any("rejected the complaint, escalating" in t for t in v["timeline"])
    assert not any("No reply from" in t for t in v["timeline"])
    assert notices and "rejected your complaint" in notices[-1] and "No reply" not in notices[-1]
    assert v["notice"] == notices[-1]


def test_partial_offer_waits_for_the_user_then_can_be_accepted(sent):
    svc, cid, _ = sent
    v = reply(svc, cid, "they offered a 50% refund")
    assert v["status"] == "waiting" and v["reply_kind"] == "partial"
    assert "offer" in v["say"] and "resolved" in v["say"] and "escalate" in v["say"]
    assert svc.respond(cid, {"action": "resolved"})["status"] == "resolved"


def test_partial_offer_can_be_declined_to_escalate(sent):
    svc, cid, notices = sent
    reply(svc, cid, "they offered a 50% refund")
    v = svc.respond(cid, {"action": "escalate"})
    assert v["status"] == "draft_ready" and v["stage"] == "the platform's grievance officer"
    assert any("You declined to wait" in t for t in v["timeline"])
    assert notices and "You chose not to wait" in notices[-1]
    assert v["reply_kind"] == ""  # the next stage starts clean


def test_stalling_reply_keeps_waiting_and_the_clock_running(sent):
    svc, cid, _ = sent
    v = reply(svc, cid, "we are looking into it")
    assert v["status"] == "waiting" and "looking into it" in v["say"]
    v = svc.respond(cid, {"action": "advance", "days": 8})  # stalling does not stop the escalation
    assert v["stage"] == "the platform's grievance officer"
    assert any("No reply from seller support, escalating" in t for t in v["timeline"])


def test_silence_still_escalates_with_the_original_wording(sent):
    svc, cid, notices = sent
    svc.respond(cid, {"action": "advance", "days": 8})
    assert "No reply from seller support within 7 days" in notices[-1]


def test_unknown_kind_is_treated_as_unclear(sent):
    svc, cid, _ = sent
    v = svc.respond(cid, {"action": "reply", "text": "hmm", "kind": "banana"})
    assert v["status"] == "waiting" and v["reply_kind"] == "unclear"


def test_rejection_at_the_helpline_goes_to_the_filing_gate(sent):
    svc, cid, notices = sent
    svc.respond(cid, {"action": "advance", "days": 8})
    svc.respond(cid, {"action": "sent"})
    svc.respond(cid, {"action": "advance", "days": 30})
    svc.respond(cid, {"action": "sent"})
    v = reply(svc, cid, "the helpline rejected it")
    assert v["status"] == "gate"
    assert "Next step: the Consumer Commission" in notices[-1]


def test_escalate_when_it_does_not_apply_says_so(tmp_path):
    svc = CaseService(str(tmp_path / "n.db"), polish=None, notifier=None)
    cid = svc.start("earbuds", "dead", "Amazon", "OD-1", "2499")["case_id"]  # letter not sent yet
    assert svc.respond(cid, {"action": "escalate"})["say"].startswith("That doesn't apply right now.")


def test_log_response_tool_classifies_the_reply(sent, monkeypatch):
    from escalation_agent import mcp_server
    svc, cid, _ = sent
    monkeypatch.setattr(mcp_server, "svc", svc)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    v = mcp_server.log_response(cid, "seller_replied", note="they rejected it, out of warranty")
    assert v["stage"] == "the platform's grievance officer"
    assert mcp_server.log_response(cid, "escalate")["status"] == "draft_ready"  # no-op, not a crash