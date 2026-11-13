"""Shared quantity and pack-rounding policy for prescription intake/dispensing."""

from decimal import Decimal, ROUND_CEILING


class QuantityService:
    @staticmethod
    def required_units(dose_per_day, days_supply, pack_size, sells_full_packs):
        try:
            dose = Decimal(str(dose_per_day))
        except Exception as exc:
            raise ValueError("dose_per_day must be numeric.") from exc
        if not dose.is_finite() or dose <= 0:
            raise ValueError("dose_per_day must be a positive finite number.")
        if isinstance(days_supply, bool) or not isinstance(days_supply, int) or days_supply <= 0:
            raise ValueError("days_supply must be a positive integer.")
        if isinstance(pack_size, bool) or not isinstance(pack_size, int) or pack_size <= 0:
            raise ValueError("pack_size must be a positive integer.")
        if not isinstance(sells_full_packs, bool):
            raise ValueError("sells_full_packs must be boolean.")

        units = int((dose * Decimal(days_supply)).to_integral_value(rounding=ROUND_CEILING))
        if sells_full_packs:
            units = ((units + pack_size - 1) // pack_size) * pack_size
        return units
