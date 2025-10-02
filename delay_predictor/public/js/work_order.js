/**
 * Work Order Custom JavaScript
 * 
 * Handles AI delay prediction functionality for Work Orders.
 */

frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        // Add AI prediction buttons
        add_ai_prediction_buttons(frm);
        
        // Update risk level indicator
        update_risk_level_indicator(frm);
    },
    
    custom_trigger_prediction: function(frm) {
        // Trigger AI prediction
        trigger_ai_prediction(frm);
    },
    
    custom_view_prediction_details: function(frm) {
        // Show prediction details dialog
        show_prediction_details(frm);
    }
});

function add_ai_prediction_buttons(frm) {
    /**
     * Add AI prediction buttons to the Work Order form.
     */
    if (frm.doc.docstatus === 1) { // Only for submitted documents
        frm.add_custom_button(__('Run AI Prediction'), function() {
            trigger_ai_prediction(frm);
        }, __('AI Actions'));
        
        if (frm.doc.custom_ai_delay_probability) {
            frm.add_custom_button(__('View Prediction Details'), function() {
                show_prediction_details(frm);
            }, __('AI Actions'));
        }
    }
}

function trigger_ai_prediction(frm) {
    /**
     * Trigger AI delay prediction for the current Work Order.
     */
    frappe.call({
        method: 'delay_predictor.custom_extensions.work_order.work_order_customization.get_work_order_delay_prediction',
        args: {
            work_order_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                if (r.message.error) {
                    frappe.msgprint({
                        title: __('Prediction Error'),
                        message: r.message.error,
                        indicator: 'red'
                    });
                } else {
                    // Update form fields
                    // frm.set_value('custom_ai_delay_probability', r.message.delay_probability * 100);
                    // frm.set_value('custom_predicted_delay_reason', r.message.delay_reason);
                    // frm.set_value('custom_risk_level', r.message.risk_level);
                    // frm.set_value('custom_last_prediction_date', new Date());
                    
                    // // Save the document
                    // frm.save();
                    
                    // Show success message
                    frappe.msgprint({
                        title: __('Prediction Complete'),
                        message: __('AI delay prediction completed successfully.'),
                        indicator: 'green'
                    });
                    // frm.reload_doc();
                    // Update risk indicator
                    update_risk_level_indicator(frm);
                    frm.reload_doc();
                }
            }
        },
        freeze: true,
        freeze_message: __('Running AI prediction...')
    });
}

function show_prediction_details(frm) {
    /**
     * Show detailed prediction analysis in a dialog.
     */
    if (!frm.doc.custom_ai_delay_probability) {
        frappe.msgprint({
            title: __('No Prediction Available'),
            message: __('Please run AI prediction first.'),
            indicator: 'orange'
        });
        return;
    }
    
    let dialog = new frappe.ui.Dialog({
        title: __('AI Delay Prediction Details'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'prediction_summary'
            }
        ],
        size: 'large'
    });
    
    // Prepare prediction summary HTML
    let risk_color = get_risk_color(frm.doc.custom_risk_level);
    let confidence_color = 'info'; // Default color
    
    let summary_html = `
        <div class="prediction-details">
            <div class="row">
                <div class="col-md-6">
                    <h4>Prediction Summary</h4>
                    <table class="table table-bordered">
                        <tr>
                            <td><strong>Delay Probability:</strong></td>
                            <td><span class="badge badge-${risk_color}">${frm.doc.custom_ai_delay_probability}%</span></td>
                        </tr>
                        <tr>
                            <td><strong>Risk Level:</strong></td>
                            <td><span class="badge badge-${risk_color}">${frm.doc.custom_risk_level || 'Not assessed'}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Predicted Reason:</strong></td>
                            <td><span class="badge badge-${confidence_color}">${frm.doc.custom_predicted_delay_reason || 'Not specified'}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Last Updated:</strong></td>
                            <td>${frm.doc.custom_last_prediction_date || 'Never'}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h4>Predicted Delay Reason</h4>
                    <div class="alert alert-${risk_color}">
                        ${frm.doc.custom_predicted_delay_reason || 'No reason provided'}
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <h4>Recommendations</h4>
                    <div class="recommendations">
                        ${get_recommendations(frm.doc.custom_ai_delay_probability, frm.doc.custom_predicted_delay_reason)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    dialog.fields_dict.prediction_summary.$wrapper.html(summary_html);
    dialog.show();
}

function update_risk_level_indicator(frm) {
    /**
     * Update the risk level indicator in the form.
     */
    if (frm.doc.custom_ai_delay_probability) {
        let risk_color = get_risk_color(frm.doc.custom_risk_level);
        let indicator_html = `
            <div class="risk-indicator">
                <span class="badge badge-${risk_color}">
                    <i class="fa fa-exclamation-triangle"></i>
                    ${frm.doc.custom_risk_level || 'Unknown'} Risk: ${frm.doc.custom_ai_delay_probability || 0}%
                </span>
            </div>
        `;
        
        // Add indicator to form header
        if (!frm.risk_indicator_added) {
            frm.page.add_inner_message(indicator_html);
            frm.risk_indicator_added = true;
        }
    }
    
    // Refresh the page to show updated data
    // frm.reload_doc();
}

function get_risk_color(risk_level) {
    /**
     * Get color class for risk level.
     */
    switch(risk_level) {
        case 'High':
            return 'danger';
        case 'Medium':
            return 'warning';
        case 'Low':
            return 'success';
        default:
            return 'secondary';
    }
}

function get_confidence_color(confidence) {
    /**
     * Get color class for confidence level.
     */
    switch(confidence) {
        case 'High':
            return 'success';
        case 'Medium':
            return 'warning';
        case 'Low':
            return 'danger';
        default:
            return 'secondary';
    }
}

function get_recommendations(delay_probability, delay_reason) {
    /**
     * Get recommendations based on delay probability and delay reason.
     */
    let recommendations = [];
    
    if (delay_probability > 70) {
        recommendations.push('<li><strong>Immediate Action Required:</strong> Review and address the identified risk factors</li>');
        recommendations.push('<li><strong>Resource Allocation:</strong> Consider allocating additional resources</li>');
        recommendations.push('<li><strong>Alternative Planning:</strong> Develop contingency plans</li>');
    } else if (delay_probability > 40) {
        recommendations.push('<li><strong>Monitor Closely:</strong> Keep a close watch on progress</li>');
        recommendations.push('<li><strong>Preventive Measures:</strong> Take preventive actions to avoid delays</li>');
    } else {
        recommendations.push('<li><strong>Continue Monitoring:</strong> Regular monitoring is sufficient</li>');
    }
    
    // Add specific recommendations based on delay reason
    if (delay_reason && delay_reason.includes('Material')) {
        recommendations.push('<li><strong>Material Management:</strong> Verify material availability and consider alternative suppliers</li>');
    }
    
    if (delay_reason && delay_reason.includes('Machine')) {
        recommendations.push('<li><strong>Equipment Check:</strong> Schedule preventive maintenance and check equipment status</li>');
    }
    
    if (delay_reason && delay_reason.includes('Workforce')) {
        recommendations.push('<li><strong>Staff Planning:</strong> Ensure adequate staffing and consider overtime arrangements</li>');
    }
    
    return '<ul>' + recommendations.join('') + '</ul>';
}
