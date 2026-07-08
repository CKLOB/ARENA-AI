import unittest

from app.mlops.models import ModelVersion
from app.shared.db import Base
from app.trading_ai.models import DecisionLog, ShapValue


class ModelMetadataTest(unittest.TestCase):
    def test_tables_are_registered(self):
        self.assertTrue({"decision_logs", "shap_values", "model_versions"} <= set(Base.metadata.tables))

    def test_spring_boot_ids_are_not_foreign_keys(self):
        self.assertFalse(DecisionLog.__table__.c.challenge_id.foreign_keys)
        self.assertFalse(DecisionLog.__table__.c.order_id.foreign_keys)

    def test_shap_values_reference_decision_logs(self):
        self.assertTrue(ShapValue.__table__.c.decision_id.foreign_keys)

    def test_model_version_tag_is_unique(self):
        constraints = {constraint.name for constraint in ModelVersion.__table__.constraints}
        self.assertIn("uq_model_versions_version_tag", constraints)


if __name__ == "__main__":
    unittest.main()
