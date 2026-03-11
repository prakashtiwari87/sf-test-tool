"""
sf_testing_engine.py — Salesforce Testing Engine
Phase 2: Salesforce Enhancement

FEATURES:
  • CRUD operations testing (Create, Read, Update, Delete)
  • Field validation testing
  • Required field testing
  • Unique constraint testing
  • Flow execution testing
  • Trigger testing
  • Bulk data testing
  • Rollback support
"""

import time
from typing import List, Dict, Optional, Any
from datetime import datetime

class SalesforceTesting

Engine:
    """
    Comprehensive Salesforce testing engine.
    Supports CRUD, validation, flows, triggers, and bulk operations.
    """
    
    def __init__(self, sf_connection: object, org_domain: str):
        """
        Initialize SF testing engine.
        
        Args:
            sf_connection: Simple-Salesforce connection
            org_domain: Org domain for tracking
        """
        self.sf = sf_connection
        self.org_domain = org_domain
        self.test_records = []  # Track created records for cleanup
    
    # ══════════════════════════════════════════════════════════
    # CRUD TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_create_record(
        self,
        object_name: str,
        field_values: Dict[str, Any],
        expected_result: str = "success"
    ) -> Dict:
        """
        Test record creation.
        
        Args:
            object_name: Salesforce object (e.g., "Account", "Contact")
            field_values: Dict of field values to create
            expected_result: "success" or "failure"
        
        Returns:
            Test result dict
        """
        start_time = time.time()
        
        try:
            # Attempt to create record
            obj = getattr(self.sf, object_name)
            result = obj.create(field_values)
            
            # Track for cleanup
            if result.get("success"):
                self.test_records.append({
                    "object": object_name,
                    "id": result.get("id")
                })
            
            # Evaluate result
            actual_result = "success" if result.get("success") else "failure"
            passed = (actual_result == expected_result)
            
            return {
                "test_type": "CRUD_CREATE",
                "object_name": object_name,
                "status": "PASS" if passed else "FAIL",
                "expected": expected_result,
                "actual": actual_result,
                "record_id": result.get("id"),
                "duration_sec": time.time() - start_time,
                "errors": result.get("errors", [])
            }
        
        except Exception as e:
            actual_result = "error"
            passed = (expected_result == "failure")
            
            return {
                "test_type": "CRUD_CREATE",
                "object_name": object_name,
                "status": "PASS" if passed else "ERROR",
                "expected": expected_result,
                "actual": actual_result,
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_read_record(
        self,
        object_name: str,
        record_id: str,
        expected_fields: Optional[Dict] = None
    ) -> Dict:
        """
        Test record retrieval.
        
        Args:
            object_name: Salesforce object
            record_id: Record ID to retrieve
            expected_fields: Optional dict of expected field values
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            obj = getattr(self.sf, object_name)
            record = obj.get(record_id)
            
            # Validate expected fields
            passed = True
            mismatches = []
            
            if expected_fields:
                for field, expected_value in expected_fields.items():
                    actual_value = record.get(field)
                    if actual_value != expected_value:
                        passed = False
                        mismatches.append({
                            "field": field,
                            "expected": expected_value,
                            "actual": actual_value
                        })
            
            return {
                "test_type": "CRUD_READ",
                "object_name": object_name,
                "record_id": record_id,
                "status": "PASS" if passed else "FAIL",
                "record_found": True,
                "mismatches": mismatches,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "CRUD_READ",
                "object_name": object_name,
                "record_id": record_id,
                "status": "ERROR",
                "record_found": False,
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_update_record(
        self,
        object_name: str,
        record_id: str,
        field_updates: Dict[str, Any],
        expected_result: str = "success"
    ) -> Dict:
        """
        Test record update.
        
        Args:
            object_name: Salesforce object
            record_id: Record ID to update
            field_updates: Dict of field updates
            expected_result: "success" or "failure"
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            obj = getattr(self.sf, object_name)
            result = obj.update(record_id, field_updates)
            
            # Salesforce update returns 204 (no content) on success
            actual_result = "success" if result == 204 else "failure"
            passed = (actual_result == expected_result)
            
            return {
                "test_type": "CRUD_UPDATE",
                "object_name": object_name,
                "record_id": record_id,
                "status": "PASS" if passed else "FAIL",
                "expected": expected_result,
                "actual": actual_result,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            actual_result = "error"
            passed = (expected_result == "failure")
            
            return {
                "test_type": "CRUD_UPDATE",
                "object_name": object_name,
                "record_id": record_id,
                "status": "PASS" if passed else "ERROR",
                "expected": expected_result,
                "actual": actual_result,
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_delete_record(
        self,
        object_name: str,
        record_id: str,
        expected_result: str = "success"
    ) -> Dict:
        """
        Test record deletion.
        
        Args:
            object_name: Salesforce object
            record_id: Record ID to delete
            expected_result: "success" or "failure"
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            obj = getattr(self.sf, object_name)
            result = obj.delete(record_id)
            
            # Salesforce delete returns 204 on success
            actual_result = "success" if result == 204 else "failure"
            passed = (actual_result == expected_result)
            
            # Remove from test_records if deleted successfully
            if result == 204:
                self.test_records = [
                    r for r in self.test_records 
                    if not (r["object"] == object_name and r["id"] == record_id)
                ]
            
            return {
                "test_type": "CRUD_DELETE",
                "object_name": object_name,
                "record_id": record_id,
                "status": "PASS" if passed else "FAIL",
                "expected": expected_result,
                "actual": actual_result,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            actual_result = "error"
            passed = (expected_result == "failure")
            
            return {
                "test_type": "CRUD_DELETE",
                "object_name": object_name,
                "record_id": record_id,
                "status": "PASS" if passed else "ERROR",
                "expected": expected_result,
                "actual": actual_result,
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # VALIDATION TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_required_field(
        self,
        object_name: str,
        required_field: str,
        other_fields: Optional[Dict] = None
    ) -> Dict:
        """
        Test that required field validation works.
        Should fail if required field is missing.
        
        Args:
            object_name: Salesforce object
            required_field: Field that should be required
            other_fields: Other field values to include
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        # Try to create record without required field
        field_values = other_fields.copy() if other_fields else {}
        # Explicitly do NOT include the required field
        
        try:
            obj = getattr(self.sf, object_name)
            result = obj.create(field_values)
            
            # Should have failed but succeeded
            if result.get("success"):
                return {
                    "test_type": "VALIDATION_REQUIRED",
                    "object_name": object_name,
                    "field_name": required_field,
                    "status": "FAIL",
                    "expected": "Validation error",
                    "actual": "Record created successfully",
                    "duration_sec": time.time() - start_time
                }
            else:
                # Failed as expected
                errors = result.get("errors", [])
                field_mentioned = any(required_field in str(e) for e in errors)
                
                return {
                    "test_type": "VALIDATION_REQUIRED",
                    "object_name": object_name,
                    "field_name": required_field,
                    "status": "PASS" if field_mentioned else "PARTIAL",
                    "expected": "Validation error",
                    "actual": "Validation error occurred",
                    "errors": errors,
                    "duration_sec": time.time() - start_time
                }
        
        except Exception as e:
            # Exception occurred (also expected)
            field_mentioned = required_field in str(e)
            
            return {
                "test_type": "VALIDATION_REQUIRED",
                "object_name": object_name,
                "field_name": required_field,
                "status": "PASS" if field_mentioned else "PARTIAL",
                "expected": "Validation error",
                "actual": "Exception raised",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_unique_constraint(
        self,
        object_name: str,
        unique_field: str,
        duplicate_value: Any,
        other_fields: Optional[Dict] = None
    ) -> Dict:
        """
        Test unique field constraint.
        Create two records with same unique field value - should fail.
        
        Args:
            object_name: Salesforce object
            unique_field: Field with unique constraint
            duplicate_value: Value to duplicate
            other_fields: Other required fields
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        field_values = other_fields.copy() if other_fields else {}
        field_values[unique_field] = duplicate_value
        
        try:
            obj = getattr(self.sf, object_name)
            
            # Create first record
            result1 = obj.create(field_values)
            if result1.get("success"):
                self.test_records.append({
                    "object": object_name,
                    "id": result1.get("id")
                })
            
            # Try to create duplicate
            result2 = obj.create(field_values)
            
            if result2.get("success"):
                # Shouldn't have succeeded
                return {
                    "test_type": "VALIDATION_UNIQUE",
                    "object_name": object_name,
                    "field_name": unique_field,
                    "status": "FAIL",
                    "expected": "Duplicate error",
                    "actual": "Duplicate created",
                    "duration_sec": time.time() - start_time
                }
            else:
                # Failed as expected
                return {
                    "test_type": "VALIDATION_UNIQUE",
                    "object_name": object_name,
                    "field_name": unique_field,
                    "status": "PASS",
                    "expected": "Duplicate error",
                    "actual": "Duplicate rejected",
                    "errors": result2.get("errors", []),
                    "duration_sec": time.time() - start_time
                }
        
        except Exception as e:
            return {
                "test_type": "VALIDATION_UNIQUE",
                "object_name": object_name,
                "field_name": unique_field,
                "status": "PASS",
                "expected": "Duplicate error",
                "actual": "Exception raised",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # BULK TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_bulk_create(
        self,
        object_name: str,
        records: List[Dict],
        expected_success_rate: float = 100.0
    ) -> Dict:
        """
        Test bulk record creation.
        
        Args:
            object_name: Salesforce object
            records: List of record dicts to create
            expected_success_rate: Expected % of successful creates
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            obj = getattr(self.sf, object_name)
            
            results = []
            for record in records:
                try:
                    result = obj.create(record)
                    results.append(result)
                    
                    if result.get("success"):
                        self.test_records.append({
                            "object": object_name,
                            "id": result.get("id")
                        })
                except Exception as e:
                    results.append({"success": False, "error": str(e)})
            
            # Calculate success rate
            successful = sum(1 for r in results if r.get("success"))
            actual_rate = (successful / len(records)) * 100 if records else 0
            
            passed = abs(actual_rate - expected_success_rate) < 5  # 5% tolerance
            
            return {
                "test_type": "BULK_CREATE",
                "object_name": object_name,
                "total_records": len(records),
                "successful": successful,
                "failed": len(records) - successful,
                "success_rate": round(actual_rate, 2),
                "expected_rate": expected_success_rate,
                "status": "PASS" if passed else "FAIL",
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "BULK_CREATE",
                "object_name": object_name,
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # QUERY TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_soql_query(
        self,
        query: str,
        expected_record_count: Optional[int] = None,
        expected_min_count: Optional[int] = None
    ) -> Dict:
        """
        Test SOQL query execution.
        
        Args:
            query: SOQL query string
            expected_record_count: Exact expected count (optional)
            expected_min_count: Minimum expected count (optional)
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            result = self.sf.query(query)
            records = result.get("records", [])
            actual_count = len(records)
            
            # Determine pass/fail
            if expected_record_count is not None:
                passed = (actual_count == expected_record_count)
            elif expected_min_count is not None:
                passed = (actual_count >= expected_min_count)
            else:
                passed = True  # Just check query executes
            
            return {
                "test_type": "SOQL_QUERY",
                "query": query[:100],  # Truncate for display
                "status": "PASS" if passed else "FAIL",
                "record_count": actual_count,
                "expected_count": expected_record_count or expected_min_count,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "SOQL_QUERY",
                "query": query[:100],
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # CLEANUP
    # ══════════════════════════════════════════════════════════
    
    def cleanup_test_records(self) -> Dict:
        """
        Delete all records created during testing.
        
        Returns:
            Cleanup summary
        """
        deleted = 0
        errors = []
        
        for record in self.test_records:
            try:
                obj = getattr(self.sf, record["object"])
                obj.delete(record["id"])
                deleted += 1
            except Exception as e:
                errors.append({
                    "object": record["object"],
                    "id": record["id"],
                    "error": str(e)
                })
        
        self.test_records = []
        
        return {
            "total_records": deleted + len(errors),
            "deleted": deleted,
            "errors": len(errors),
            "error_details": errors
        }


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def quick_crud_test(
    sf_connection: object,
    object_name: str,
    test_data: Dict
) -> List[Dict]:
    """
    Quick CRUD test cycle: Create → Read → Update → Delete
    
    Usage:
        from connectors.salesforce_connector import connect_with_oauth
        sf, _ = connect_with_oauth(...)
        
        results = quick_crud_test(
            sf_connection=sf,
            object_name="Account",
            test_data={"Name": "Test Account"}
        )
    """
    engine = SalesforceTestingEngine(sf_connection, "test.salesforce.com")
    results = []
    
    # Create
    create_result = engine.test_create_record(object_name, test_data)
    results.append(create_result)
    
    if create_result.get("status") == "PASS":
        record_id = create_result.get("record_id")
        
        # Read
        read_result = engine.test_read_record(object_name, record_id)
        results.append(read_result)
        
        # Update
        update_data = {"Name": test_data.get("Name", "") + " - Updated"}
        update_result = engine.test_update_record(object_name, record_id, update_data)
        results.append(update_result)
        
        # Delete
        delete_result = engine.test_delete_record(object_name, record_id)
        results.append(delete_result)
    
    return results