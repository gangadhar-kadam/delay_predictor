"""
Production Data Generator

Generates simulated production order data for training the delay prediction model.
Creates realistic manufacturing scenarios with various delay factors.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any
import frappe


class ProductionDataGenerator:
    """
    Generates simulated production order data for ML model training.

    Creates realistic manufacturing scenarios including:
    - Raw material availability issues
    - Machine downtime scenarios
    - Workforce shortage situations
    - Quality control delays
    - Supplier delivery delays
    """

    def __init__(self, seed: int = 42):
        """
        Initialize the data generator with a random seed for reproducibility.

        Args:
            seed (int): Random seed for reproducible data generation
        """
        np.random.seed(seed)
        random.seed(seed)

        # Define realistic manufacturing scenarios
        self.material_types = [
            "Steel",
            "Aluminum",
            "Plastic",
            "Rubber",
            "Glass",
            "Copper",
            "Fabric",
            "Wood",
            "Ceramic",
            "Composite",
        ]

        self.machine_types = [
            "CNC Machine",
            "Press Machine",
            "Welding Station",
            "Assembly Line",
            "Quality Control Station",
            "Packaging Station",
            "Cutting Machine",
        ]

        self.delay_reasons = [
            "Raw Material Shortage",
            "Machine Breakdown",
            "Workforce Shortage",
            "Quality Control Issues",
            "Supplier Delay",
            "Power Outage",
            "Tool Unavailability",
            "Maintenance Overdue",
            "Transportation Delay",
            "Weather Conditions",
        ]

        self.work_shifts = ["Day", "Night", "Evening"]
        self.companies = [
            "ALFASTACK Manufacturing",
            "TechCorp Industries",
            "Precision Works",
        ]

    def generate_production_orders(self, num_records: int = 200) -> pd.DataFrame:
        """
        Generate simulated production order data.

        Args:
            num_records (int): Number of production orders to generate

        Returns:
            pd.DataFrame: Generated production order data
        """
        data = []

        for i in range(num_records):
            order = self._generate_single_order(i)
            data.append(order)

        return pd.DataFrame(data)

    def _generate_single_order(self, order_id: int) -> Dict[str, Any]:
        """
        Generate a single production order with realistic manufacturing parameters.

        Args:
            order_id (int): Unique identifier for the order

        Returns:
            Dict[str, Any]: Single production order data
        """
        # Base order parameters
        planned_start = datetime.now() - timedelta(days=random.randint(1, 365))
        planned_duration = random.randint(1, 30)  # days
        planned_end = planned_start + timedelta(days=planned_duration)

        # Manufacturing parameters
        material_availability = np.random.beta(2, 2)  # 0-1, realistic distribution
        machine_availability = np.random.beta(3, 1)  # 0-1, usually high
        workforce_availability = np.random.beta(2.5, 1.5)  # 0-1
        shift_capacity = random.choice([0.8, 1.0, 1.2])  # 80%, 100%, 120%

        # Quality and supplier factors
        quality_control_issues = np.random.exponential(0.1)  # Low probability
        supplier_reliability = np.random.beta(2, 1)  # 0-1, usually good
        weather_impact = np.random.exponential(0.05)  # Very low probability

        # Calculate delay probability based on these factors
        delay_probability = self._calculate_delay_probability(
            material_availability,
            machine_availability,
            workforce_availability,
            quality_control_issues,
            supplier_reliability,
            weather_impact,
        )

        # Determine if order was actually delayed
        is_delayed = delay_probability > 0.5

        # Calculate actual duration (with potential delay)
        if is_delayed:
            delay_days = random.randint(1, 15)
            actual_end = planned_end + timedelta(days=delay_days)
            delay_reason = random.choice(self.delay_reasons)
        else:
            actual_end = planned_end + timedelta(days=random.randint(-2, 2))
            delay_reason = None

        return {
            "order_id": f"WO-{order_id:04d}",
            "company": random.choice(self.companies),
            "production_item": f"Product-{random.randint(100, 999)}",
            "planned_start_date": planned_start,
            "planned_end_date": planned_end,
            "actual_start_date": planned_start + timedelta(days=random.randint(-1, 2)),
            "actual_end_date": actual_end,
            "planned_duration_days": planned_duration,
            "actual_duration_days": (actual_end - planned_start).days,
            "quantity": random.randint(10, 1000),
            "material_type": random.choice(self.material_types),
            "machine_type": random.choice(self.machine_types),
            "work_shift": random.choice(self.work_shifts),
            "material_availability": round(material_availability, 3),
            "machine_availability": round(machine_availability, 3),
            "workforce_availability": round(workforce_availability, 3),
            "shift_capacity": shift_capacity,
            "quality_control_issues": round(quality_control_issues, 3),
            "supplier_reliability": round(supplier_reliability, 3),
            "weather_impact": round(weather_impact, 3),
            "is_delayed": is_delayed,
            "delay_reason": delay_reason,
            "delay_probability": round(delay_probability, 3),
            "created_date": planned_start - timedelta(days=random.randint(1, 30)),
        }

    def _calculate_delay_probability(
        self,
        material_avail: float,
        machine_avail: float,
        workforce_avail: float,
        quality_issues: float,
        supplier_rel: float,
        weather_impact: float,
    ) -> float:
        """
        Calculate delay probability based on manufacturing factors.

        Args:
            material_avail (float): Material availability (0-1)
            machine_avail (float): Machine availability (0-1)
            workforce_avail (float): Workforce availability (0-1)
            quality_issues (float): Quality control issues factor
            supplier_rel (float): Supplier reliability (0-1)
            weather_impact (float): Weather impact factor

        Returns:
            float: Calculated delay probability (0-1)
        """
        # Base probability from resource availability
        base_prob = (
            (1 - material_avail) * 0.4
            + (1 - machine_avail) * 0.3
            + (1 - workforce_avail) * 0.2
        )

        # Add risk factors
        risk_factors = (
            quality_issues * 0.1 + (1 - supplier_rel) * 0.15 + weather_impact * 0.05
        )

        # Combine and normalize
        total_prob = base_prob + risk_factors

        # Apply sigmoid function to get realistic probability distribution
        delay_prob = 1 / (1 + np.exp(-10 * (total_prob - 0.3)))

        return min(max(delay_prob, 0), 1)  # Clamp between 0 and 1

    def save_to_csv(
        self, df: pd.DataFrame, filename: str = "production_orders.csv"
    ) -> str:
        """
        Save generated data to CSV file.

        Args:
            df (pd.DataFrame): Generated production order data
            filename (str): Output filename

        Returns:
            str: Path to saved file
        """
        filepath = f"/tmp/{filename}"
        df.to_csv(filepath, index=False)
        return filepath

    def load_from_erpnext(self) -> pd.DataFrame:
        """
        Load actual production order data from ERPNext Work Orders.

        Returns:
            pd.DataFrame: Production order data from ERPNext
        """
        try:
            # Query Work Orders from ERPNext
            work_orders = frappe.get_all(
                "Work Order",
                fields=[
                    "name",
                    "company",
                    "production_item",
                    "planned_start_date",
                    "planned_end_date",
                    "actual_start_date",
                    "actual_end_date",
                    "qty",
                    "status",
                    "creation",
                ],
                filters={"docstatus": ["!=", 2]},  # Exclude cancelled
                limit=1000,
            )

            if not work_orders:
                print("No Work Orders found in ERPNext. Using simulated data.")
                return self.generate_production_orders(100)

            # Convert to DataFrame and add calculated fields
            df = pd.DataFrame(work_orders)

            # Calculate additional features
            df["planned_duration_days"] = (
                pd.to_datetime(df["planned_end_date"])
                - pd.to_datetime(df["planned_start_date"])
            ).dt.days

            df["actual_duration_days"] = (
                pd.to_datetime(df["actual_end_date"])
                - pd.to_datetime(df["actual_start_date"])
            ).dt.days

            df["is_delayed"] = pd.to_datetime(df["actual_end_date"]) > pd.to_datetime(
                df["planned_end_date"]
            )

            # Add simulated features for ML model (in real implementation, these would come from other doctypes)
            df["material_availability"] = np.random.beta(2, 2, len(df))
            df["machine_availability"] = np.random.beta(3, 1, len(df))
            df["workforce_availability"] = np.random.beta(2.5, 1.5, len(df))
            df["shift_capacity"] = np.random.choice([0.8, 1.0, 1.2], len(df))
            df["quality_control_issues"] = np.random.exponential(0.1, len(df))
            df["supplier_reliability"] = np.random.beta(2, 1, len(df))
            df["weather_impact"] = np.random.exponential(0.05, len(df))

            return df

        except Exception as e:
            print(f"Error loading data from ERPNext: {e}")
            print("Falling back to simulated data.")
            return self.generate_production_orders(100)


