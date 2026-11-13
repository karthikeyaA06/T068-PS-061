import pytest

from app.services.master_data_service import MasterDataService


def test_register_supplier_validates_required_name_and_optional_fields(monkeypatch):
    monkeypatch.setattr(MasterDataService, "_insert", staticmethod(lambda operation, *args: 41))
    result = MasterDataService().register_supplier(
        "  Demo Supplier  ", contact_person=" Contact ", phone="123"
    )
    assert result == {"supplier_id": 41, "supplier_name": "Demo Supplier"}


def test_register_supplier_rejects_blank_name():
    with pytest.raises(ValueError, match="supplier_name is required"):
        MasterDataService().register_supplier("  ")


def test_register_customer_rejects_non_boolean_loyalty_flag():
    with pytest.raises(ValueError, match="loyalty_member must be boolean"):
        MasterDataService().register_customer("Demo Customer", loyalty_member=1)


def test_register_doctor_requires_registration_number(monkeypatch):
    with pytest.raises(ValueError, match="registration_number is required"):
        MasterDataService().register_doctor("", "Demo Doctor")


def test_register_patient_normalizes_optional_contact(monkeypatch):
    monkeypatch.setattr(MasterDataService, "_insert", staticmethod(lambda operation, *args: 12))
    result = MasterDataService().register_patient("Demo Patient", contact="  ")
    assert result == {"patient_id": 12, "patient_name": "Demo Patient"}
