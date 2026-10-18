"""Unit tests for SlainteScan / Slainte-Scan-MCP clinical interoperability tools."""
import unittest
import os
import json
import sys

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.clinical_rules import calculate_mts_category, get_mts_details
from src.terminology import resolve_terminology
from src.schema_scanner import scan_clinical_schema
from src.fhir_ie_core import generate_fhir_bundle, IRISH_GMS_OID
from src.fhir_validator import validate_fhir_resource

class TestClinicalRules(unittest.TestCase):
    def test_category_1_immediate(self):
        vitals = {"spo2": 88, "systolic_bp": 85, "heart_rate": 150}
        self.assertEqual(calculate_mts_category(vitals), 1)

    def test_category_2_very_urgent(self):
        vitals = {"spo2": 91, "pain": 8, "systolic_bp": 130}
        self.assertEqual(calculate_mts_category(vitals), 2)

    def test_category_3_urgent(self):
        vitals = {"pain": 5, "heart_rate": 110, "spo2": 96}
        self.assertEqual(calculate_mts_category(vitals), 3)

    def test_category_4_standard(self):
        vitals = {"pain": 2, "temperature": 37.9, "spo2": 98}
        self.assertEqual(calculate_mts_category(vitals), 4)

    def test_category_5_non_urgent(self):
        vitals = {"pain": 0, "heart_rate": 72, "spo2": 99, "systolic_bp": 120}
        self.assertEqual(calculate_mts_category(vitals), 5)

    def test_mts_details(self):
        details = get_mts_details(1)
        self.assertEqual(details["name"], "Immediate")
        self.assertEqual(details["target_time_minutes"], 0)
        self.assertEqual(details["color"], "Red")

class TestTerminology(unittest.TestCase):
    def test_vital_to_loinc(self):
        res = resolve_terminology("vital", "systolic_bp")
        self.assertTrue(res["found"])
        self.assertEqual(res["code"], "8480-6")
        self.assertEqual(res["unit"], "mmHg")

    def test_complaint_to_snomed(self):
        res = resolve_terminology("clinical", "chest pain")
        self.assertTrue(res["found"])
        self.assertEqual(res["code"], "29857009")
        self.assertEqual(res["display"], "Chest pain")

    def test_unknown_vital(self):
        res = resolve_terminology("vital", "random_unmapped_vital_xyz")
        self.assertFalse(res["found"])

class TestSchemaScanner(unittest.TestCase):
    def test_csv_introspection(self):
        csv_data = "pt_id,Patient_Name,GMS_NO,triage_complaint,sys_bp,hr,o2_sat\nP101,John Doe,12345,chest pain,140,88,98"
        res = scan_clinical_schema(csv_data)
        self.assertEqual(res["source_type"], "csv")
        self.assertEqual(res["row_count"], 1)
        mapping = res["detected_mappings"]
        self.assertEqual(mapping["patient_id"], "pt_id")
        self.assertEqual(mapping["full_name"], "Patient_Name")
        self.assertEqual(mapping["systolic_bp"], "sys_bp")
        self.assertEqual(mapping["spo2"], "o2_sat")

    def test_restricted_system_path_blocked(self):
        res = scan_clinical_schema("/etc/passwd")
        self.assertIn("error", res)
        self.assertIn("disallowed", res["error"])

class TestFhirGenerationAndValidation(unittest.TestCase):
    def test_bundle_generation_and_validation(self):
        vitals = {
            "systolic_bp": 125,
            "diastolic_bp": 82,
            "heart_rate": 78,
            "spo2": 98,
            "temperature": 36.8,
            "pain": 1,
            "complaint": "chest pain"
        }
        bundle = generate_fhir_bundle(
            vitals=vitals,
            triage_category=2,
            gms_number="99123-A",
            patient_id="P999",
            name="Maeve Higgins",
            gender="female",
            birthdate="1984-03-22",
            complaint="chest pain",
            labs=[{"name": "Troponin", "value": 0.02, "unit": "ng/mL"}],
            medications=[{"name": "Aspirin", "instructions": "300mg stat"}],
            allergies=[{"name": "Penicillin", "severity": "high", "reactions": ["Anaphylaxis"]}]
        )
        self.assertEqual(bundle["resourceType"], "Bundle")
        self.assertEqual(bundle["type"], "collection")
        
        # Verify validation
        val = validate_fhir_resource(bundle)
        self.assertTrue(val["valid"], f"Validation failed with errors: {val.get('errors')}")

        # Check Irish GMS OID present
        patient_entries = [
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "Patient"
        ]
        self.assertEqual(len(patient_entries), 1)
        pt = patient_entries[0]
        self.assertEqual(pt["identifier"][0]["system"], IRISH_GMS_OID)
        self.assertEqual(pt["identifier"][0]["value"], "99123-A")

if __name__ == "__main__":
    unittest.main()
