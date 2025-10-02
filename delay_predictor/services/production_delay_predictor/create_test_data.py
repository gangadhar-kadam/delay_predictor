import frappe
from datetime import datetime, timedelta
import random

# Get existing company
company = frappe.get_all("Company", fields=["name"], limit=1)[0].name
print(f"Using company: {company}")

# Get existing items
items = frappe.get_all("Item", filters={"is_stock_item": 1}, fields=["name"], limit=15)
print(f"Found {len(items)} existing items")

# Get existing warehouses
warehouses = frappe.get_all("Warehouse", fields=["name"], limit=3)
fg_warehouse = warehouses[0].name
wip_warehouse = warehouses[1].name if len(warehouses) > 1 else warehouses[0].name
source_warehouse = warehouses[2].name if len(warehouses) > 2 else warehouses[0].name

# Create comprehensive scenarios that will trigger different delay reasons
scenarios = [
    # Material shortage scenarios
    {
        "name": "Material Shortage - High Volume",
        "qty": 2000,
        "days": 1,
        "expected_reason": "Raw Material Shortage",
    },
    {
        "name": "Material Shortage - Critical",
        "qty": 1500,
        "days": 1,
        "expected_reason": "Raw Material Shortage",
    },
    # Machine breakdown scenarios
    {
        "name": "Machine Breakdown - Complex",
        "qty": 800,
        "days": 1,
        "expected_reason": "Machine Breakdown",
    },
    {
        "name": "Machine Breakdown - Heavy",
        "qty": 1200,
        "days": 1,
        "expected_reason": "Machine Breakdown",
    },
    # Workforce shortage scenarios
    {
        "name": "Workforce Shortage - Large",
        "qty": 1000,
        "days": 1,
        "expected_reason": "Workforce Shortage",
    },
    {
        "name": "Workforce Shortage - Skilled",
        "qty": 600,
        "days": 1,
        "expected_reason": "Workforce Shortage",
    },
    # Quality control scenarios
    {
        "name": "Quality Issues - Precision",
        "qty": 300,
        "days": 1,
        "expected_reason": "Quality Control Issues",
    },
    {
        "name": "Quality Issues - Complex",
        "qty": 500,
        "days": 1,
        "expected_reason": "Quality Control Issues",
    },
    # Supplier delay scenarios
    {
        "name": "Supplier Delay - Import",
        "qty": 400,
        "days": 1,
        "expected_reason": "Supplier Delay",
    },
    {
        "name": "Supplier Delay - Critical",
        "qty": 700,
        "days": 1,
        "expected_reason": "Supplier Delay",
    },
    # Power/Infrastructure scenarios
    {
        "name": "Power Outage - Peak",
        "qty": 900,
        "days": 1,
        "expected_reason": "Power Outage",
    },
    {
        "name": "Tool Unavailability - Special",
        "qty": 200,
        "days": 1,
        "expected_reason": "Tool Unavailability",
    },
    # Maintenance scenarios
    {
        "name": "Maintenance Overdue - Critical",
        "qty": 1100,
        "days": 1,
        "expected_reason": "Maintenance Overdue",
    },
    {
        "name": "Transportation Delay - Remote",
        "qty": 350,
        "days": 1,
        "expected_reason": "Transportation Delay",
    },
    # Weather scenarios
    {
        "name": "Weather Impact - Seasonal",
        "qty": 450,
        "days": 1,
        "expected_reason": "Weather Conditions",
    },
    # Low risk scenarios (should have lower delay probability)
    {
        "name": "Low Risk - Standard",
        "qty": 100,
        "days": 5,
        "expected_reason": "Low Risk",
    },
    {"name": "Low Risk - Small", "qty": 50, "days": 7, "expected_reason": "Low Risk"},
]

# Get existing HSN code
existing_hsn = frappe.get_all("GST HSN Code", fields=["hsn_code"], limit=1)
if existing_hsn:
    hsn_code = existing_hsn[0].hsn_code
    print(f"Using existing HSN code: {hsn_code}")
else:
    print("No HSN codes found, skipping raw material creation")
    hsn_code = None

# Create a universal raw material to avoid BOM recursion
if hsn_code:
    try:
        raw_material = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": "TEST-RAW-UNIVERSAL",
                "item_name": "Test Raw Material Universal",
                "item_group": "Raw Material",
                "is_stock_item": 1,
                "is_purchase_item": 1,
                "gst_hsn_code": hsn_code,
            }
        )
        raw_material.insert()
        frappe.db.commit()
        print("✅ Created universal raw material: TEST-RAW-UNIVERSAL")
    except Exception as e:
        print(f"Raw material creation: {str(e)}")
        hsn_code = None

created_boms = []
created_work_orders = []

for i, scenario in enumerate(scenarios):
    if i >= len(items):
        break

    # Use different items for each BOM
    finished_item = items[i].name

    print(f"\nCreating {scenario['name']} (Expected: {scenario['expected_reason']})...")

    # Create BOM with varying complexity
    bom_name = f"BOM-{finished_item}-{i+1}"
    try:
        # Vary BOM complexity based on scenario
        bom_complexity = 1 if "Low Risk" in scenario["name"] else random.randint(2, 3)

        bom = frappe.get_doc(
            {
                "doctype": "BOM",
                "item": finished_item,
                "quantity": 1,
                "company": company,
                "is_default": 1,
                "is_active": 1,
            }
        )

        # Use universal raw material if available, otherwise use existing items
        if hsn_code:
            bom.append(
                "items",
                {
                    "item_code": "TEST-RAW-UNIVERSAL",
                    "qty": random.randint(2, 8),
                    "rate": random.randint(50, 200),
                },
            )
        else:
            # Use existing items as raw materials, ensuring no self-reference
            raw_item_index = (i + 1) % len(items)
            raw_item = items[raw_item_index].name
            if raw_item != finished_item:
                bom.append(
                    "items",
                    {
                        "item_code": raw_item,
                        "qty": random.randint(2, 8),
                        "rate": random.randint(50, 200),
                    },
                )

        # Add one additional raw material for complex scenarios
        if bom_complexity > 1 and i + 2 < len(items):
            additional_item = items[(i + 2) % len(items)].name
            if (
                additional_item != finished_item
                and additional_item != "TEST-RAW-UNIVERSAL"
            ):
                bom.append(
                    "items",
                    {
                        "item_code": additional_item,
                        "qty": random.randint(1, 3),
                        "rate": random.randint(30, 150),
                    },
                )

        bom.insert()
        bom.submit()
        frappe.db.commit()
        created_boms.append(bom.name)
        print(f"  ✅ Created BOM: {bom.name} (Complexity: {bom_complexity})")

    except Exception as e:
        print(f"  ❌ BOM creation error: {str(e)}")
        continue

    # Create Work Order with scenario-specific parameters
    try:
        # Vary timing based on scenario type
        if "Material Shortage" in scenario["name"]:
            # Short timeline for material shortage scenarios
            planned_duration = random.randint(1, 3)
        elif "Machine Breakdown" in scenario["name"]:
            # Medium timeline for machine issues
            planned_duration = random.randint(2, 5)
        elif "Low Risk" in scenario["name"]:
            # Longer timeline for low risk scenarios
            planned_duration = random.randint(5, 10)
        else:
            # Standard timeline
            planned_duration = random.randint(3, 7)

        planned_start = datetime.now() + timedelta(days=scenario["days"])
        planned_end = planned_start + timedelta(days=planned_duration)

        work_order = frappe.get_doc(
            {
                "doctype": "Work Order",
                "production_item": finished_item,
                "bom_no": bom.name,
                "qty": scenario["qty"],
                "company": company,
                "planned_start_date": planned_start,
                "planned_end_date": planned_end,
                "fg_warehouse": fg_warehouse,
                "wip_warehouse": wip_warehouse,
                "source_warehouse": source_warehouse,
                # Add some additional fields that might influence predictions
                "description": f"Test Work Order for {scenario['expected_reason']} scenario",
            }
        )

        # Set custom scenario type for AI prediction logic
        work_order.custom_scenario_type = scenario["name"]

        work_order.insert()
        work_order.submit()
        created_work_orders.append(work_order.name)
        print(
            f"  ✅ Created Work Order: {work_order.name} (Qty: {scenario['qty']}, Duration: {planned_duration} days)"
        )

    except Exception as e:
        print(f"  ❌ Work Order creation error: {str(e)}")

frappe.db.commit()

print(f"\n🎉 Summary:")
print(f"✅ Created {len(created_boms)} BOMs")
print(f"✅ Created {len(created_work_orders)} Work Orders")
print(f"\nBOMs created: {created_boms}")
print(f"Work Orders created: {created_work_orders}")

print(f"\n📊 Scenario Coverage:")
for scenario in scenarios[: len(created_work_orders)]:
    print(f"  • {scenario['name']}: Expected {scenario['expected_reason']}")

print(f"\n💡 You can now test AI predictions on these Work Orders!")
print(f"   Each Work Order is designed to trigger different delay reasons.")
print(f"   Run AI predictions to see the variety of delay scenarios!")
