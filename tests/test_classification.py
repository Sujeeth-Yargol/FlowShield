from src.classification import classify_level, RiskStatus

def test_classification_boundaries():
    assert classify_level(10, 100) == RiskStatus.SAFE
    assert classify_level(60, 100) == RiskStatus.WARNING
    assert classify_level(90, 100) == RiskStatus.CRITICAL
