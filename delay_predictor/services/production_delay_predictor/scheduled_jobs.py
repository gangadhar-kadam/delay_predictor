"""
Scheduled Jobs for Production Delay Prediction

Entry points for scheduled jobs that run the delay prediction system.
"""

import frappe
from .prediction_service import PredictionService


def predict_production_delays():
    """
    Scheduled job to predict delays for pending production orders.
    
    This function is called by the cron job defined in hooks.py.
    It processes all pending Work Orders and updates them with delay predictions.
    """
    try:
        # Initialize prediction service
        service = PredictionService()
        
        # Run batch prediction for pending orders
        results = service.batch_predict_pending_orders()
        
        # Log results
        frappe.logger().info(f"Production delay prediction completed: {results['total_orders']} orders processed, {len(results['high_risk_orders'])} high-risk orders found.")
        
        # Send notifications for high-risk orders if any
        if results['high_risk_orders']:
            _send_high_risk_notifications(results['high_risk_orders'])
        
        return {
            'status': 'success',
            'message': f"Processed {results['total_orders']} orders, found {len(results['high_risk_orders'])} high-risk orders",
            'results': results
        }
        
    except Exception as e:
        frappe.logger().error(f"Error in production delay prediction job: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }




def _send_high_risk_notifications(high_risk_orders):
    """
    Send notifications for high-risk production orders.
    
    Args:
        high_risk_orders (List[Dict]): List of high-risk orders
    """
    try:
        # Get notification recipients
        recipients = _get_notification_recipients()
        
        if not recipients:
            return
        
        # Prepare notification content
        subject = f"High-Risk Production Orders Alert - {len(high_risk_orders)} orders"
        
        message = f"""
        <h3>High-Risk Production Orders Detected</h3>
        <p>The following production orders have been flagged as high-risk for delays:</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th>Work Order</th>
                <th>Production Item</th>
                <th>Planned Start</th>
                <th>Delay Probability</th>
                <th>Delay Reason</th>
            </tr>
        """
        
        for order in high_risk_orders:
            message += f"""
            <tr>
                <td>{order['work_order']}</td>
                <td>{order.get('production_item', 'N/A')}</td>
                <td>{order.get('planned_start_date', 'N/A')}</td>
                <td>{order['delay_probability']:.1%}</td>
                <td>{order['delay_reason']}</td>
            </tr>
            """
        
        message += "</table>"
        
        # Send email notifications
        for recipient in recipients:
            frappe.sendmail(
                recipients=[recipient],
                subject=subject,
                message=message,
                header=["High-Risk Production Orders", "red"]
            )
        
        frappe.logger().info(f"High-risk notifications sent to {len(recipients)} recipients")
        
    except Exception as e:
        frappe.logger().error(f"Error sending high-risk notifications: {str(e)}")


def _get_notification_recipients():
    """
    Get list of email recipients for high-risk notifications.
    
    Returns:
        List[str]: List of email addresses
    """
    try:
        # Get users with Manufacturing Manager role
        manufacturing_managers = frappe.get_all(
            'Has Role',
            filters={'role': 'Manufacturing Manager'},
            fields=['parent']
        )
        
        recipients = []
        for manager in manufacturing_managers:
            email = frappe.get_value('User', manager.parent, 'email')
            if email:
                recipients.append(email)
        
        # Add system administrators as fallback
        if not recipients:
            admin_users = frappe.get_all(
                'User',
                filters={'enabled': 1, 'user_type': 'System User'},
                fields=['email'],
                limit=3
            )
            recipients = [user.email for user in admin_users if user.email]
        
        return recipients
        
    except Exception as e:
        frappe.logger().error(f"Error getting notification recipients: {str(e)}")
        return []


def initialize_delay_prediction_system():
    """
    Initialize the delay prediction system.
    
    This function should be called once during system setup to train the initial model.
    """
    try:
        # Initialize prediction service
        service = PredictionService()
        
        # Train initial model
        frappe.logger().info("Training initial delay prediction model...")
        results = service.train_model_from_erpnext()
        
        frappe.logger().info(f"Initial model training completed. Accuracy: {results['accuracy']:.3f}")
        
        return {
            'status': 'success',
            'message': 'Delay prediction system initialized successfully',
            'model_accuracy': results['accuracy']
        }
        
    except Exception as e:
        frappe.logger().error(f"Error initializing delay prediction system: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }
