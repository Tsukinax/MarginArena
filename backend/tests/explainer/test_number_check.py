"""Seam 3: the explainer's number check (ADR 0001).

Every number in a Verdict explanation must come from the engine's facts for that Verdict. An explanation
that states any other number is rejected, whatever language or numerals it is written in.
"""

from marginarena.explainer import unsupported_numbers

FACTS = """Product: Hyaluronic Sheet Mask x10 (SM-10)
Verdict: Skip, a kind of Revise: don't join the Campaign with this product.
Joining as invited (฿79.80 off): worst-case Campaign profit ฿1,227.28, worst-case margin per unit 9.4%.
Not joining: worst-case Campaign profit ฿1,477.70.
Margin Floor: 10%."""


def test_an_explanation_that_invents_a_figure_is_rejected():
    text = "Skip: not joining keeps ฿1,477.70, while joining as invited would lose about ฿2,500."

    assert unsupported_numbers(text, FACTS) == ["2,500"]


def test_a_thai_explanation_may_round_an_engine_figure_but_not_change_it():
    rounded = "Skip: ไม่เข้าร่วมยังได้กำไร ฿1,478 ในกรณีแย่ที่สุด ส่วนการเข้าร่วมตามคำเชิญได้ ฿1,227.28 และกำไรต่อชิ้น 9%"
    approximated = "Skip: การเข้าร่วมตามคำเชิญได้กำไรราว ฿1,200 ในกรณีแย่ที่สุด"

    assert unsupported_numbers(rounded, FACTS) == []
    assert unsupported_numbers(approximated, FACTS) == ["1,200"]


def test_thai_numerals_are_checked_like_arabic_ones():
    assert unsupported_numbers("ไม่เข้าร่วมได้ ๑,๔๗๗.๗๐ บาท แต่ถ้าเข้าร่วมจะขาดทุนราว ๒,๕๐๐ บาท", FACTS) == ["๒,๕๐๐"]


def test_a_number_too_precise_to_compare_is_rejected():
    assert unsupported_numbers("Joining keeps ฿1,227.2800000000000000000000000000001.", FACTS) == [
        "1,227.2800000000000000000000000000001"
    ]
