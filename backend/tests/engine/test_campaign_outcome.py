"""Campaign demand and profit for one Promo Plan.

Demand follows the spec: units = baseline x Campaign traffic lift x (buyer price ratio)^elasticity
x Counter-move factor, rounded down (never overstate demand) and capped at stock.
Expected values are worked by hand from that formula.
"""

from decimal import Decimal

from marginarena.engine import CampaignTerms, CounterMove, PriceCut, PromoPlan, Sku, campaign_outcome, get_profile

SHOPEE = get_profile("shopee-th-nonmall-prime-fmcg")


def item(stock: int = 1000) -> Sku:
    return Sku(
        id="FMCG-100",
        name="฿100 item costing ฿50",
        list_price=Decimal("100"),
        cost=Decimal("50"),
        stock=stock,
        baseline_units=100,
        elasticity=Decimal("-1.52"),
    )


TWENTY_OFF = PromoPlan(mechanics=(PriceCut(amount=Decimal("20")),))
DOUBLE_TRAFFIC = CampaignTerms(traffic_lift=Decimal("2"))


def test_twenty_percent_off_with_doubled_traffic_sells_280_units():
    # 100 x 2 x 0.8^-1.52 = 280.76 -> 280 units at ฿6.67 each.
    outcome = campaign_outcome(item(), TWENTY_OFF, SHOPEE, DOUBLE_TRAFFIC)

    assert outcome.units == 280
    assert outcome.total_profit == Decimal("1867.60")


def test_units_never_exceed_stock():
    outcome = campaign_outcome(item(stock=250), TWENTY_OFF, SHOPEE, DOUBLE_TRAFFIC)

    assert outcome.units == 250
    assert outcome.total_profit == Decimal("1667.50")


def test_no_discount_sells_baseline_times_traffic_lift():
    outcome = campaign_outcome(item(), PromoPlan(), SHOPEE, DOUBLE_TRAFFIC)

    assert outcome.units == 200
    assert outcome.total_profit == Decimal("4222.00")


def test_rival_cheaper_than_us_takes_demand_in_proportion_to_the_gap():
    # ADR 0004: we lose demand only when the Rival ends up cheaper. Rival cuts 25% to ฿75 against our ฿80;
    # with sensitivity 0.6 we keep (75/80)^0.6 = 0.96202: 100 x 2 x 0.8^-1.52 x 0.96202 = 270.09 -> 270.
    rival = CounterMove(rival="Deep undercutter", rival_price_cut=Decimal("0.25"))
    terms = CampaignTerms(traffic_lift=Decimal("2"), cross_price_sensitivity=Decimal("0.6"))

    outcome = campaign_outcome(item(), TWENTY_OFF, SHOPEE, terms, rival)

    assert outcome.units == 270
    assert outcome.total_profit == Decimal("1800.90")


def test_rival_cut_that_leaves_it_dearer_than_us_changes_nothing():
    # Rival cuts 10% to ฿90; we sell at ฿80, so we keep all demand.
    rival = CounterMove(rival="Undercutter", rival_price_cut=Decimal("0.10"))

    assert campaign_outcome(item(), TWENTY_OFF, SHOPEE, DOUBLE_TRAFFIC, rival).units == 280


def test_rival_voucher_counts_as_part_of_its_effective_price_cut():
    # 15% off plus a ฿10 voucher on a ฿100 reference price is an effective 25% cut: same as the ฿75 case.
    rival = CounterMove(rival="Voucher bomber", rival_price_cut=Decimal("0.15"), voucher=Decimal("10"))
    terms = CampaignTerms(traffic_lift=Decimal("2"), cross_price_sensitivity=Decimal("0.6"))

    assert campaign_outcome(item(), TWENTY_OFF, SHOPEE, terms, rival).units == 270
