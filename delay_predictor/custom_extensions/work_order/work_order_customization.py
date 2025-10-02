"""
Work Order Customization

Extends ERPNext Work Order doctype with AI-powered delay prediction fields.
"""

import frappe
from frappe import _
from frappe.model.document import Document


def entry_point(doc, method=None):
    """
    Entry point for Work Order customizations.

    Args:
        doc: Work Order document
        method: Method being called
    """
    if method == "on_submit":
        on_work_order_submit(doc)
    elif method == "on_update":
        on_work_order_update(doc)
    elif method == "validate":
        validate_work_order(doc)


def on_work_order_submit(doc):
    """
    Handle Work Order submission.

    Args:
        doc: Work Order document
    """
    try:
        # Trigger delay prediction when Work Order is submitted
        from delay_predictor.services.production_delay_predictor.prediction_service import (
            PredictionService,
        )

        service = PredictionService()
        prediction = service.predict_work_order_delay(doc.name)

        # Update Work Order with prediction results
        # doc.custom_ai_delay_probability = prediction["delay_probability"] * 100
        # doc.custom_predicted_delay_reason = prediction["delay_reason"]
        # doc.custom_risk_level = prediction["risk_level"]
        # doc.custom_last_prediction_date = frappe.utils.now()
        # doc.save()

        # Log prediction
        frappe.logger().info(
            f"Delay prediction for {doc.name}: {prediction['delay_probability']:.1%} probability, Risk: {prediction['risk_level']}"
        )

    except Exception as e:
        frappe.logger().error(f"Error in delay prediction for {doc.name}: {str(e)}")


def on_work_order_update(doc):
    """
    Handle Work Order updates.

    Args:
        doc: Work Order document
    """
    try:
        # Re-run prediction if key fields are updated
        if (
            doc.has_value_changed("planned_start_date")
            or doc.has_value_changed("planned_end_date")
            or doc.has_value_changed("qty")
        ):
            from delay_predictor.services.production_delay_predictor.prediction_service import (
                PredictionService,
            )

            service = PredictionService()
            prediction = service.predict_work_order_delay(doc.name)

            frappe.logger().info(
                f"Updated delay prediction for {doc.name}: {prediction['delay_probability']:.1%} probability"
            )

    except Exception as e:
        frappe.logger().error(
            f"Error updating delay prediction for {doc.name}: {str(e)}"
        )


def validate_work_order(doc):
    """
    Validate Work Order data.

    Args:
        doc: Work Order document
    """
    # Add any custom validation logic here
    pass


@frappe.whitelist()
def get_work_order_delay_prediction(work_order_name):
    """
    Get delay prediction for a specific Work Order and save results to database.

    Args:
        work_order_name (str): Name of the Work Order

    Returns:
        Dict: Prediction results
    """
    try:
        from delay_predictor.services.production_delay_predictor.prediction_service import (
            PredictionService,
        )

        service = PredictionService()
        # Get prediction and automatically update document
        prediction = service.predict_work_order_delay(work_order_name)

        return prediction

    except Exception as e:
        frappe.logger().error(
            f"Error getting delay prediction for {work_order_name}: {str(e)}"
        )
        return {
            "error": str(e),
            "delay_probability": 0,
            "risk_level": "Unknown",
            "delay_reason": "Error in prediction",
        }


@frappe.whitelist()
def get_high_risk_work_orders():
    """
    Get all high-risk Work Orders.

    Returns:
        List: High-risk Work Orders
    """
    try:
        from delay_predictor.services.production_delay_predictor.prediction_service import (
            PredictionService,
        )

        service = PredictionService()
        high_risk_orders = service.get_high_risk_orders()

        return high_risk_orders

    except Exception as e:
        frappe.logger().error(f"Error getting high-risk work orders: {str(e)}")
        return []
