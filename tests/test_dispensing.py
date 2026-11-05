import pytest

from app.services.dispensing_service import DispensingService


def test_required_units_round_up_fractional_units():
    assert DispensingService.calculate_required_units(
        dose_per_day="1.5",
        days_supply=3,
        pack_size=10,
        sells_full_packs=False,
    ) == 5


def test_required_units_exactly_one_pack_stays_one_pack():
    assert DispensingService.calculate_required_units(
        dose_per_day=1,
        days_supply=10,
        pack_size=10,
        sells_full_packs=True,
    ) == 10


def test_required_units_one_above_pack_rounds_to_next_pack():
    assert DispensingService.calculate_required_units(
        dose_per_day=1,
        days_supply=11,
        pack_size=10,
        sells_full_packs=True,
    ) == 20


def test_required_units_non_full_pack_does_not_round_to_pack():
    assert DispensingService.calculate_required_units(
        dose_per_day=1,
        days_supply=11,
        pack_size=10,
        sells_full_packs=False,
    ) == 11


@pytest.mark.parametrize(
    "dose,days,pack_size,full_packs",
    [
        (0, 10, 10, False),
        (1, 0, 10, False),
        (1, 10, 0, False),
        (1, True, 10, False),
        (1, 10, 10, 1),
    ],
)
def test_required_units_rejects_invalid_inputs(
    dose, days, pack_size, full_packs
):
    with pytest.raises(ValueError):
        DispensingService.calculate_required_units(
            dose, days, pack_size, full_packs
        )
