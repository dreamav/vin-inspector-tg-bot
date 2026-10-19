import asyncio
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_client import VINInspectorAPI
from handlers.vin import validate_vin


async def main():
    print("=== ТЕСТИРОВАНИЕ ВАЛИДАЦИИ VIN ===")
    test_vins = [
        ("WAUZZZ8K9BA123456", True),
        ("WAUZZZ8K9BA12345", False),  # 16 chars
        ("WAUZZZ8K9BA1234567", False),  # 18 chars
        ("WAUZZZ8K9BA12345I", False),  # contains I
        ("WAUZZZ8K9BA12345O", False),  # contains O
        ("WAUZZZ8K9BA12345Q", False),  # contains Q
    ]

    for vin_candidate, expected_valid in test_vins:
        is_val, normalized, err = validate_vin(vin_candidate)
        print(f"VIN: {vin_candidate} -> Valid: {is_val} (expected: {expected_valid})")
        assert is_val == expected_valid, f"Failed for {vin_candidate}"

    print("\n=== ТЕСТИРОВАНИЕ СВЯЗИ С БЭКЕНДОМ ===")
    api = VINInspectorAPI(base_url="http://localhost:8000")

    print("1. Тест decode_vin...")
    res = await api.decode_vin("WAUZZZ8K9BA123456")
    print("Ответ decode_vin:", res)
    assert res.get("success") is True, "decode_vin returned success != True"
    assert res.get("make") == "Audi", f"Expected Audi, got {res.get('make')}"

    print("2. Тест check_oem (Audi)...")
    oem_res = await api.check_oem(oem="06E115562A", brand="audi", vin="WAUZZZ8K9BA123456")
    print("Ответ check_oem:", oem_res)
    assert oem_res.get("success") is True, "check_oem returned success != True"
    assert oem_res.get("status") in ("fit", "not-fit"), f"Unexpected status {oem_res.get('status')}"

    print("3. Тест check_oem со списком совместимых авто (Toyota)...")
    oem_toyota = await api.check_oem(oem="04152-YZZA6", brand="toyota", vin="")
    assert oem_toyota.get("success") is True, "Toyota check_oem failed"
    fitment = oem_toyota.get("fitmentVehicles", [])
    print(f"Найдено совместимых авто: {len(fitment)}")
    assert len(fitment) > 0, "Expected fitmentVehicles to be non-empty"
    from handlers.oem import format_fitment_summary
    summary = format_fitment_summary(fitment, car_title="2016 Scion iM", make="Scion", model="iM")
    assert "⭐️ <b>[Текущее авто]</b>" in summary, "Matching vehicle was not tagged"

    await api.close()
    print("\n✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")


if __name__ == "__main__":
    asyncio.run(main())
