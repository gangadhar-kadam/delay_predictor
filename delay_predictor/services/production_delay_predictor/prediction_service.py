"""
Prediction Service

Service layer for integrating the ML delay predictor with ERPNext.
Handles data extraction, prediction, and result storage.
"""

import frappe
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from .delay_predictor import ProductionDelayPredictor
from .data_generator import ProductionDataGenerator


class PredictionService:
    """
    Service for integrating production delay prediction with ERPNext.

    Features:
    - Extract data from ERPNext Work Orders
    - Generate predictions for new orders
    - Update Work Order records with predictions
    - Batch processing capabilities
    - Scheduled job integration
    """

    def __init__(self, model_type: str = "random_forest"):
        """
        Initialize the prediction service.

        Args:
            model_type (str): Type of ML model to use
        """
        self.predictor = ProductionDelayPredictor(model_type)
        self.data_generator = ProductionDataGenerator()

        # Try to load existing trained model
        try:
            self.predictor.load_model()
        except Exception as e:
            frappe.logger().info(
                f"No trained model found or error loading model: {str(e)}"
            )
            # Model will be trained automatically when first prediction is made

    def train_model_from_erpnext(self) -> Dict[str, Any]:
        """
        Train the ML model using data from ERPNext Work Orders.

        Returns:
            Dict[str, Any]: Training results
        """
        try:
            # Load data from ERPNext
            df = self.data_generator.load_from_erpnext()

            if df.empty:
                print(
                    "No data available from ERPNext. Using simulated data for training."
                )
                df = self.data_generator.generate_production_orders(200)

            # Train model
            results = self.predictor.train(df)

            # Log training results
            frappe.logger().info(
                f"Model training completed. Accuracy: {results['accuracy']:.3f}"
            )

            return results

        except Exception as e:
            frappe.logger().error(f"Error training model: {str(e)}")
            raise

    def predict_work_order_delay(self, work_order_name: str) -> Dict[str, Any]:
        """
        Predict delay probability for a specific Work Order and update the document.

        Args:
            work_order_name (str): Name of the Work Order

        Returns:
            Dict[str, Any]: Prediction results
        """
        try:
            # Ensure model is loaded or train if not available
            if self.predictor.model is None:
                try:
                    self.predictor.load_model()
                except Exception:
                    # Model not found, train it automatically
                    print("Model not found. Training model automatically...")
                    self.train_model_from_erpnext()

            # Get Work Order data
            work_order = frappe.get_doc("Work Order", work_order_name)

            # Extract features for prediction
            features = self._extract_work_order_features(work_order)

            # Make prediction
            prediction = self.predictor.predict(features)

            # Always update Work Order with prediction results
            self._update_work_order_prediction(work_order_name, prediction)

            return prediction

        except Exception as e:
            frappe.logger().error(
                f"Error predicting delay for {work_order_name}: {str(e)}"
            )
            raise

    def _extract_work_order_features(self, work_order) -> Dict[str, Any]:
        """
        Extract features from Work Order for prediction.

        Args:
            work_order: ERPNext Work Order document

        Returns:
            Dict[str, Any]: Extracted features
        """
        # Basic order information
        features = {
            "planned_start_date": work_order.planned_start_date,
            "planned_end_date": work_order.planned_end_date,
            "quantity": work_order.qty,
            "company": work_order.company,
            "production_item": work_order.production_item,
        }

        # Calculate planned duration
        if work_order.planned_start_date and work_order.planned_end_date:
            duration = (
                work_order.planned_end_date - work_order.planned_start_date
            ).days
            features["planned_duration_days"] = duration
        else:
            features["planned_duration_days"] = 7  # Default

        # Get material availability from BOM
        features.update(self._get_material_availability(work_order))

        # Get machine availability
        features.update(self._get_machine_availability(work_order))

        # Get workforce availability
        features.update(self._get_workforce_availability(work_order))

        # Get quality and supplier factors
        features.update(self._get_quality_supplier_factors(work_order))

        # Add simulated factors (in real implementation, these would come from other systems)
        features.update(self._get_simulated_factors(work_order))

        # Add scenario type for direct delay reason mapping
        scenario_type = getattr(work_order, "custom_scenario_type", None)
        if scenario_type:
            features["scenario_type"] = scenario_type

        return features

    def _get_material_availability(self, work_order) -> Dict[str, Any]:
        """
        Get material availability information from BOM and stock.

        Args:
            work_order: Work Order document

        Returns:
            Dict[str, Any]: Material availability features
        """
        try:
            # Get BOM items
            bom_items = frappe.get_all(
                "BOM Item",
                filters={"parent": work_order.bom_no},
                fields=["item_code", "qty", "rate"],
            )

            if not bom_items:
                # Check for scenario-specific material availability
                scenario_type = getattr(work_order, "custom_scenario_type", None)
                if scenario_type:
                    if "Material Shortage" in scenario_type:
                        return {
                            "material_availability": 0.1,
                            "material_type": "Critical",
                        }
                    elif "Supplier Delay" in scenario_type:
                        return {
                            "material_availability": 0.2,
                            "material_type": "Delayed",
                        }
                    elif "Transportation Delay" in scenario_type:
                        return {
                            "material_availability": 0.3,
                            "material_type": "Transport",
                        }
                    elif "Low Risk" in scenario_type:
                        return {
                            "material_availability": 0.95,
                            "material_type": "Abundant",
                        }
                return {"material_availability": 0.8, "material_type": "Unknown"}

            # Check stock availability for each item
            total_required = 0
            total_available = 0

            for item in bom_items:
                # Get current stock
                stock_qty = frappe.db.sql(
                    """
                    SELECT SUM(actual_qty) as qty
                    FROM `tabStock Ledger Entry`
                    WHERE item_code = %s AND warehouse = %s
                """,
                    (item.item_code, work_order.source_warehouse or "Stores - T"),
                )

                available_qty = stock_qty[0][0] if stock_qty and stock_qty[0][0] else 0
                required_qty = item.qty * work_order.qty

                total_required += required_qty
                total_available += min(available_qty, required_qty)

            # Calculate availability ratio
            if total_required > 0:
                availability = total_available / total_required
            else:
                availability = 1.0

            # Override with scenario-specific availability if needed
            scenario_type = getattr(work_order, "custom_scenario_type", None)
            if scenario_type and "Material Shortage" in scenario_type:
                availability = (
                    0.2  # Force low availability for material shortage scenario
                )

            # Get material type from first item
            material_type = (
                frappe.get_value("Item", bom_items[0].item_code, "item_group")
                or "Unknown"
            )

            return {
                "material_availability": min(max(availability, 0), 1),
                "material_type": material_type,
            }

        except Exception as e:
            frappe.logger().error(f"Error getting material availability: {str(e)}")
            return {"material_availability": 0.8, "material_type": "Unknown"}

    def _get_machine_availability(self, work_order) -> Dict[str, Any]:
        """
        Get machine availability information.

        Args:
            work_order: Work Order document

        Returns:
            Dict[str, Any]: Machine availability features
        """
        try:
            # Get operations from Work Order
            operations = frappe.get_all(
                "Work Order Operation",
                filters={"parent": work_order.name},
                fields=["workstation", "status"],
            )

            if not operations:
                # Check for scenario-specific machine availability
                scenario_type = getattr(work_order, "custom_scenario_type", None)
                if scenario_type:
                    if "Machine Breakdown" in scenario_type:
                        return {"machine_availability": 0.2, "machine_type": "Broken"}
                    elif "Power Outage" in scenario_type:
                        return {"machine_availability": 0.1, "machine_type": "Offline"}
                    elif "Tool Unavailability" in scenario_type:
                        return {"machine_availability": 0.3, "machine_type": "Limited"}
                    elif "Maintenance Overdue" in scenario_type:
                        return {
                            "machine_availability": 0.4,
                            "machine_type": "Maintenance",
                        }
                    elif "Low Risk" in scenario_type:
                        return {"machine_availability": 0.95, "machine_type": "Optimal"}
                return {"machine_availability": 0.9, "machine_type": "General"}

            # Check workstation availability
            available_workstations = 0
            total_workstations = len(operations)

            for op in operations:
                if op.workstation:
                    # Check if workstation is available
                    workstation_status = frappe.get_value(
                        "Workstation", op.workstation, "status"
                    )
                    if workstation_status == "Active":
                        available_workstations += 1

            availability = (
                available_workstations / total_workstations
                if total_workstations > 0
                else 0.9
            )

            # Override with scenario-specific availability if needed
            scenario_type = getattr(work_order, "custom_scenario_type", None)
            if scenario_type and "Machine Breakdown" in scenario_type:
                availability = (
                    0.3  # Force low availability for machine breakdown scenario
                )

            # Get machine type from first workstation
            machine_type = "General"
            if operations[0].workstation:
                machine_type = (
                    frappe.get_value(
                        "Workstation", operations[0].workstation, "workstation_type"
                    )
                    or "General"
                )

            return {"machine_availability": availability, "machine_type": machine_type}

        except Exception as e:
            frappe.logger().error(f"Error getting machine availability: {str(e)}")
            return {"machine_availability": 0.9, "machine_type": "General"}

    def _get_workforce_availability(self, work_order) -> Dict[str, Any]:
        """
        Get workforce availability information.

        Args:
            work_order: Work Order document

        Returns:
            Dict[str, Any]: Workforce availability features
        """
        try:
            # Get operations and their workforce requirements
            operations = frappe.get_all(
                "Work Order Operation",
                filters={"parent": work_order.name},
                fields=["workstation", "time_in_mins"],
            )

            if not operations:
                # Check for scenario-specific workforce availability
                scenario_type = getattr(work_order, "custom_scenario_type", None)
                if scenario_type:
                    if "Workforce Shortage" in scenario_type:
                        return {
                            "workforce_availability": 0.2,
                            "work_shift": "Day",
                            "shift_capacity": 0.5,
                        }
                    elif "Low Risk" in scenario_type:
                        return {
                            "workforce_availability": 0.95,
                            "work_shift": "Day",
                            "shift_capacity": 1.2,
                        }
                return {
                    "workforce_availability": 0.85,
                    "work_shift": "Day",
                    "shift_capacity": 1.0,
                }

            # Calculate total work hours required
            total_hours = sum(op.time_in_mins or 0 for op in operations) / 60

            # Estimate workforce availability based on shift capacity
            # In real implementation, this would check actual employee schedules
            shift_capacity = 1.0  # Default
            workforce_availability = 0.85  # Default

            # Override with scenario-specific availability if needed
            scenario_type = getattr(work_order, "custom_scenario_type", None)
            if scenario_type and "Workforce Shortage" in scenario_type:
                workforce_availability = (
                    0.2  # Force low availability for workforce shortage scenario
                )
                shift_capacity = 0.5

            return {
                "workforce_availability": workforce_availability,
                "work_shift": "Day",
                "shift_capacity": shift_capacity,
            }

        except Exception as e:
            frappe.logger().error(f"Error getting workforce availability: {str(e)}")
            return {
                "workforce_availability": 0.85,
                "work_shift": "Day",
                "shift_capacity": 1.0,
            }

    def _get_quality_supplier_factors(self, work_order) -> Dict[str, Any]:
        """
        Get quality control and supplier reliability factors.

        Args:
            work_order: Work Order document

        Returns:
            Dict[str, Any]: Quality and supplier factors
        """
        # In real implementation, these would come from:
        # - Quality control history
        # - Supplier performance data
        # - Historical defect rates

        return {
            "quality_control_issues": 0.1,  # Default low risk
            "supplier_reliability": 0.8,  # Default good reliability
            "weather_impact": 0.05,  # Default low impact
        }

    def _get_simulated_factors(self, work_order=None) -> Dict[str, Any]:
        """
        Get simulated factors for demonstration purposes.

        Args:
            work_order: Work Order document (optional)

        Returns:
            Dict[str, Any]: Simulated factors
        """
        import numpy as np

        # Default factors
        factors = {
            "quality_control_issues": np.random.exponential(0.1),
            "supplier_reliability": np.random.beta(2, 1),
            "weather_impact": np.random.exponential(0.05),
        }

        # If we have a work order, check for scenario-specific conditions
        if work_order:
            scenario_type = getattr(work_order, "custom_scenario_type", None)
            if scenario_type:
                # Override factors based on scenario type to create diverse predictions
                if "Material Shortage" in scenario_type:
                    factors["supplier_reliability"] = (
                        0.1  # Very low - triggers material shortage
                    )
                    factors["quality_control_issues"] = 0.05  # Low
                    factors["weather_impact"] = 0.02  # Low
                elif "Machine Breakdown" in scenario_type:
                    factors["supplier_reliability"] = 0.8  # Good
                    factors["quality_control_issues"] = 0.3  # Moderate - machine issues
                    factors["weather_impact"] = 0.1  # Low
                elif "Workforce Shortage" in scenario_type:
                    factors["supplier_reliability"] = 0.7  # Good
                    factors["quality_control_issues"] = 0.2  # Moderate
                    factors["weather_impact"] = 0.4  # High - workforce issues
                elif "Quality Issues" in scenario_type:
                    factors["supplier_reliability"] = 0.6  # Moderate
                    factors["quality_control_issues"] = (
                        0.9  # Very high - quality issues
                    )
                    factors["weather_impact"] = 0.1  # Low
                elif "Supplier Delay" in scenario_type:
                    factors["supplier_reliability"] = 0.1  # Very low - supplier issues
                    factors["quality_control_issues"] = 0.1  # Low
                    factors["weather_impact"] = 0.2  # Moderate
                elif "Power Outage" in scenario_type:
                    factors["supplier_reliability"] = 0.5  # Moderate
                    factors["quality_control_issues"] = 0.1  # Low
                    factors["weather_impact"] = 0.8  # Very high - power issues
                elif "Tool Unavailability" in scenario_type:
                    factors["supplier_reliability"] = 0.4  # Low
                    factors["quality_control_issues"] = 0.6  # High - tool issues
                    factors["weather_impact"] = 0.1  # Low
                elif "Maintenance Overdue" in scenario_type:
                    factors["supplier_reliability"] = 0.6  # Moderate
                    factors["quality_control_issues"] = 0.7  # High - maintenance issues
                    factors["weather_impact"] = 0.1  # Low
                elif "Transportation Delay" in scenario_type:
                    factors["supplier_reliability"] = 0.2  # Low - transport issues
                    factors["quality_control_issues"] = 0.1  # Low
                    factors["weather_impact"] = 0.3  # Moderate
                elif "Weather Impact" in scenario_type:
                    factors["supplier_reliability"] = 0.5  # Moderate
                    factors["quality_control_issues"] = 0.1  # Low
                    factors["weather_impact"] = 0.9  # Very high - weather issues
                elif "Low Risk" in scenario_type:
                    factors["quality_control_issues"] = 0.02  # Very low
                    factors["supplier_reliability"] = 0.95  # Very high
                    factors["weather_impact"] = 0.01  # Very low

        return factors

    def _update_work_order_prediction(
        self, work_order_name: str, prediction: Dict[str, Any]
    ):
        """
        Update Work Order with prediction results.

        Args:
            work_order_name (str): Name of the Work Order
            prediction (Dict[str, Any]): Prediction results
        """
        try:
            # Update Work Order with custom fields
            frappe.db.set_value(
                "Work Order",
                work_order_name,
                {
                    "custom_ai_delay_probability": prediction["delay_probability"]
                    * 100,
                    "custom_predicted_delay_reason": prediction["delay_reason"],
                    "custom_risk_level": prediction["risk_level"],
                    "custom_last_prediction_date": datetime.now(),
                },
            )

            # Add comment to Work Order
            comment = f"""
            <div class="alert alert-{'danger' if prediction['risk_level'] == 'High' else 'warning' if prediction['risk_level'] == 'Medium' else 'info'}">
                <strong>AI Delay Prediction:</strong><br>
                Probability: {prediction['delay_probability']:.1%}<br>
                Risk Level: {prediction['risk_level']}<br>
                Reason: {prediction['delay_reason']}<br>
                Confidence: {prediction['confidence']}
            </div>
            """

            frappe.get_doc("Work Order", work_order_name).add_comment(
                "Comment", comment
            )

            frappe.db.commit()

        except Exception as e:
            frappe.logger().error(
                f"Error updating Work Order {work_order_name}: {str(e)}"
            )
            raise

    def batch_predict_pending_orders(self) -> Dict[str, Any]:
        """
        Predict delays for all pending Work Orders.

        Returns:
            Dict[str, Any]: Batch prediction results
        """
        try:
            # Get pending Work Orders
            pending_orders = frappe.get_all(
                "Work Order",
                filters={
                    "status": ["in", ["Draft", "Submitted", "Not Started"]],
                    "docstatus": 1,
                },
                fields=["name"],
            )

            results = {
                "total_orders": len(pending_orders),
                "predictions": [],
                "high_risk_orders": [],
                "errors": [],
            }

            for order in pending_orders:
                try:
                    prediction = self.predict_work_order_delay(order.name)
                    results["predictions"].append(
                        {"work_order": order.name, "prediction": prediction}
                    )

                    if prediction["risk_level"] == "High":
                        results["high_risk_orders"].append(
                            {
                                "work_order": order.name,
                                "delay_probability": prediction["delay_probability"],
                                "delay_reason": prediction["delay_reason"],
                            }
                        )

                except Exception as e:
                    results["errors"].append(
                        {"work_order": order.name, "error": str(e)}
                    )

            # Log results
            frappe.logger().info(
                f"Batch prediction completed. {len(results['predictions'])} orders processed, {len(results['high_risk_orders'])} high-risk orders found."
            )

            return results

        except Exception as e:
            frappe.logger().error(f"Error in batch prediction: {str(e)}")
            raise

    def get_high_risk_orders(self) -> List[Dict[str, Any]]:
        """
        Get all Work Orders with high delay risk.

        Returns:
            List[Dict[str, Any]]: High-risk Work Orders
        """
        try:
            high_risk_orders = frappe.get_all(
                "Work Order",
                filters={
                    "custom_risk_level": "High",
                    "status": ["in", ["Draft", "Submitted", "Not Started"]],
                    "docstatus": 1,
                },
                fields=[
                    "name",
                    "production_item",
                    "planned_start_date",
                    "planned_end_date",
                    "custom_ai_delay_probability",
                    "custom_predicted_delay_reason",
                ],
                order_by="custom_ai_delay_probability desc",
            )

            return high_risk_orders

        except Exception as e:
            frappe.logger().error(f"Error getting high-risk orders: {str(e)}")
            return []
