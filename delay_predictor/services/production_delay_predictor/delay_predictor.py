"""
Production Delay Predictor

Machine Learning model for predicting production delays in manufacturing.
Uses multiple algorithms and feature engineering for accurate predictions.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
from typing import Dict, List, Tuple, Any
import frappe
from datetime import datetime


class ProductionDelayPredictor:
    """
    Machine Learning model for predicting production delays.

    Features:
    - Multiple algorithm support (Random Forest, Gradient Boosting, Logistic Regression)
    - Feature engineering and selection
    - Model persistence and loading
    - Cross-validation and performance metrics
    - Real-time prediction capabilities
    """

    def __init__(self, model_type: str = "random_forest"):
        """
        Initialize the delay predictor.

        Args:
            model_type (str): Type of ML model to use ('random_forest', 'decision_tree', 'logistic_regression')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.model_path = "/tmp/production_delay_model.pkl"
        self.scaler_path = "/tmp/production_delay_scaler.pkl"
        self.encoders_path = "/tmp/production_delay_encoders.pkl"
        self.features_path = "/tmp/production_delay_features.pkl"

        # Initialize model based on type
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the ML model based on the specified type."""
        if self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
            )
        elif self.model_type == "decision_tree":
            self.model = DecisionTreeClassifier(
                max_depth=10, random_state=42, class_weight="balanced"
            )
        elif self.model_type == "logistic_regression":
            self.model = LogisticRegression(
                random_state=42, class_weight="balanced", max_iter=1000
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and engineer features for the ML model.

        Args:
            df (pd.DataFrame): Raw production order data

        Returns:
            pd.DataFrame: Processed features ready for training
        """
        # Create a copy to avoid modifying original data
        features_df = df.copy()

        # Feature engineering
        features_df = self._engineer_features(features_df)

        # Handle categorical variables
        features_df = self._encode_categorical_features(features_df)

        # Define all possible features
        all_feature_columns = [
            "material_availability",
            "machine_availability",
            "workforce_availability",
            "shift_capacity",
            "quality_control_issues",
            "supplier_reliability",
            "weather_impact",
            "planned_duration_days",
            "quantity",
            "material_type_encoded",
            "machine_type_encoded",
            "work_shift_encoded",
            "company_encoded",
            "seasonality_factor",
            "resource_stress_factor",
            "complexity_factor",
        ]

        # If this is training, set the feature columns
        if not hasattr(self, "feature_columns") or not self.feature_columns:
            self.feature_columns = [
                col for col in all_feature_columns if col in features_df.columns
            ]

        # Ensure all expected features are present
        for col in self.feature_columns:
            if col not in features_df.columns:
                # Add missing features with default values
                if col in [
                    "material_availability",
                    "machine_availability",
                    "workforce_availability",
                    "shift_capacity",
                ]:
                    features_df[col] = 0.8  # Default availability
                elif col in ["quality_control_issues", "weather_impact"]:
                    features_df[col] = 0.1  # Default low risk
                elif col == "supplier_reliability":
                    features_df[col] = 0.8  # Default good reliability
                elif col == "planned_duration_days":
                    features_df[col] = 7  # Default duration
                elif col == "quantity":
                    features_df[col] = 1  # Default quantity
                elif col.endswith("_encoded"):
                    features_df[col] = 0  # Default encoded value
                elif col in [
                    "seasonality_factor",
                    "resource_stress_factor",
                    "complexity_factor",
                ]:
                    features_df[col] = 0.0  # Default factor values
                else:
                    features_df[col] = 0  # Default value

        # Get the standard feature columns for ML model (exclude scenario_type)
        ml_features = features_df[self.feature_columns]

        # Preserve scenario_type if it exists (for delay reason analysis)
        # But don't include it in the ML model features
        if "scenario_type" in features_df.columns:
            ml_features["scenario_type"] = features_df["scenario_type"]

        return ml_features

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer additional features for better prediction accuracy.

        Args:
            df (pd.DataFrame): Input data

        Returns:
            pd.DataFrame: Data with engineered features
        """
        # Seasonality factor (based on planned start date)
        if "planned_start_date" in df.columns:
            df["planned_start_date"] = pd.to_datetime(df["planned_start_date"])
            df["month"] = df["planned_start_date"].dt.month
            df["seasonality_factor"] = np.sin(2 * np.pi * df["month"] / 12)

        # Resource stress factor (combination of availability metrics)
        availability_cols = [
            "material_availability",
            "machine_availability",
            "workforce_availability",
        ]
        available_cols = [col for col in availability_cols if col in df.columns]
        if available_cols:
            df["resource_stress_factor"] = 1 - df[available_cols].mean(axis=1)

        # Complexity factor (based on quantity and duration)
        if "quantity" in df.columns and "planned_duration_days" in df.columns:
            df["complexity_factor"] = (
                df["quantity"] * df["planned_duration_days"]
            ) / 1000

        # Risk accumulation factor
        risk_cols = ["quality_control_issues", "weather_impact"]
        available_risk_cols = [col for col in risk_cols if col in df.columns]
        if available_risk_cols:
            df["risk_accumulation"] = df[available_risk_cols].sum(axis=1)

        # Preserve scenario_type field for delay reason analysis
        if "scenario_type" in df.columns:
            # Keep the scenario_type field as is
            pass

        return df

    def _encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Encode categorical features using label encoding.

        Args:
            df (pd.DataFrame): Input data with categorical features

        Returns:
            pd.DataFrame: Data with encoded categorical features
        """
        categorical_columns = ["material_type", "machine_type", "work_shift", "company"]

        for col in categorical_columns:
            if col in df.columns:
                encoder = LabelEncoder()
                encoded_col = f"{col}_encoded"
                df[encoded_col] = encoder.fit_transform(df[col].astype(str))
                self.label_encoders[col] = encoder

        return df

    def train(
        self, df: pd.DataFrame, target_column: str = "is_delayed"
    ) -> Dict[str, Any]:
        """
        Train the ML model on production order data.

        Args:
            df (pd.DataFrame): Training data
            target_column (str): Name of the target column

        Returns:
            Dict[str, Any]: Training results and metrics
        """
        # Prepare features
        X = self.prepare_features(df)
        y = df[target_column].astype(int)

        # Handle missing values
        X = X.fillna(X.mean())

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model.fit(X_train_scaled, y_train)

        # Evaluate model
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)

        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)

        # Save model and components
        self.save_model()

        results = {
            "accuracy": accuracy,
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "classification_report": class_report,
            "feature_importance": self._get_feature_importance(X.columns),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            "test_predictions": y_pred.tolist(),
            "test_probabilities": y_pred_proba.tolist(),
        }

        return results

    def _get_feature_importance(self, feature_names: List[str]) -> Dict[str, float]:
        """
        Get feature importance from the trained model.

        Args:
            feature_names (List[str]): Names of features

        Returns:
            Dict[str, float]: Feature importance scores
        """
        if hasattr(self.model, "feature_importances_"):
            importance = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            importance = np.abs(self.model.coef_[0])
        else:
            return {}

        return dict(zip(feature_names, importance))

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict delay probability for a single production order.

        Args:
            data (Dict[str, Any]): Production order data

        Returns:
            Dict[str, Any]: Prediction results
        """
        if self.model is None:
            self.load_model()

        # Check if model is loaded
        if self.model is None:
            raise ValueError("Model not loaded. Please train the model first.")

        # Extract scenario_type before converting to DataFrame
        scenario_type = data.get("scenario_type", "")

        # Convert to DataFrame (excluding scenario_type from ML features)
        ml_data = {k: v for k, v in data.items() if k != "scenario_type"}
        df = pd.DataFrame([ml_data])

        # Prepare features
        X = self.prepare_features(df)
        X = X.fillna(X.mean())

        # Check if scaler is fitted
        if not hasattr(self.scaler, "mean_") or self.scaler.mean_ is None:
            # If scaler is not fitted, we need to retrain or use a fallback
            print("Warning: Scaler not fitted. Using raw features for prediction.")
            X_scaled = X.values
        else:
            # Scale features (don't fit again, just transform)
            X_scaled = self.scaler.transform(X)

        # Make prediction
        delay_probability = self.model.predict_proba(X_scaled)[0, 1]
        prediction = self.model.predict(X_scaled)[0]

        # Get delay reason based on feature analysis
        # Pass the original data with scenario_type to delay reason analysis
        analysis_data = data.copy()
        analysis_data["scenario_type"] = scenario_type
        delay_reason = self._analyze_delay_reason(analysis_data, delay_probability)

        return {
            "delay_probability": round(delay_probability, 3),
            "is_delayed": bool(prediction),
            "delay_reason": delay_reason,
            "risk_level": self._get_risk_level(delay_probability),
            "confidence": self._get_confidence(delay_probability),
        }

    def _analyze_delay_reason(
        self, data: Dict[str, Any], delay_probability: float
    ) -> str:
        """
        Analyze the most likely reason for delay based on input data.

        Args:
            data (Dict[str, Any]): Production order data
            delay_probability (float): Predicted delay probability

        Returns:
            str: Most likely delay reason
        """
        if delay_probability < 0.3:
            return "Low Risk - No significant delays expected"

        # Debug: Print all data keys to see what's available
        print(f"Debug - Available data keys: {list(data.keys())}")
        print(f"Debug - Scenario type value: {data.get('scenario_type', 'NOT_FOUND')}")

        # First, check if we have scenario type information and use it directly
        scenario_type = data.get("scenario_type", "")
        if scenario_type:
            # Map scenario types directly to delay reasons
            if "Material Shortage" in scenario_type:
                return "Raw Material Shortage"
            elif "Machine Breakdown" in scenario_type:
                return "Machine Breakdown"
            elif "Workforce Shortage" in scenario_type:
                return "Workforce Shortage"
            elif "Quality Issues" in scenario_type:
                return "Quality Control Issues"
            elif "Supplier Delay" in scenario_type:
                return "Supplier Delay"
            elif "Power Outage" in scenario_type:
                return "Power Outage"
            elif "Tool Unavailability" in scenario_type:
                return "Tool Unavailability"
            elif "Maintenance Overdue" in scenario_type:
                return "Maintenance Overdue"
            elif "Transportation Delay" in scenario_type:
                return "Transportation Delay"
            elif "Weather Impact" in scenario_type:
                return "Weather Conditions"
            elif "Low Risk" in scenario_type:
                return "Low Risk - No significant delays expected"

        # Fallback to factor-based analysis if no scenario type
        # Analyze factors to determine most likely delay reason
        # Use more intelligent analysis based on actual feature values
        material_risk = 1 - data.get("material_availability", 0.8)
        machine_risk = 1 - data.get("machine_availability", 0.9)
        workforce_risk = 1 - data.get("workforce_availability", 0.85)
        quality_risk = data.get("quality_control_issues", 0.1)
        supplier_risk = 1 - data.get("supplier_reliability", 0.8)
        weather_risk = data.get("weather_impact", 0.05)

        # Create a more comprehensive analysis with all delay reasons
        # Use weighted combinations to better distinguish between different scenarios
        factors = {
            "Raw Material Shortage": material_risk
            * 1.2,  # Boost material shortage detection
            "Machine Breakdown": machine_risk
            * 1.1,  # Boost machine breakdown detection
            "Workforce Shortage": workforce_risk
            * 1.1,  # Boost workforce shortage detection
            "Quality Control Issues": quality_risk
            * 1.3,  # Boost quality issues detection
            "Supplier Delay": supplier_risk * 1.2,  # Boost supplier delay detection
            "Power Outage": weather_risk
            * 1.5,  # Power issues are often weather-related
            "Tool Unavailability": (quality_risk + machine_risk)
            * 0.6,  # Tool issues affect both quality and machines
            "Maintenance Overdue": (machine_risk + quality_risk)
            * 0.7,  # Maintenance affects machines and quality
            "Transportation Delay": (supplier_risk + material_risk)
            * 0.8,  # Transport affects both suppliers and materials
            "Weather Conditions": weather_risk * 1.4,  # Boost weather impact detection
        }

        # Debug logging to understand factor values
        print(f"Debug - Delay factors for analysis:")
        for factor_name, factor_value in factors.items():
            print(f"  {factor_name}: {factor_value:.3f}")
        print(f"  Material availability: {data.get('material_availability', 0.8):.3f}")
        print(f"  Machine availability: {data.get('machine_availability', 0.9):.3f}")
        print(
            f"  Workforce availability: {data.get('workforce_availability', 0.85):.3f}"
        )
        print(
            f"  Quality control issues: {data.get('quality_control_issues', 0.1):.3f}"
        )
        print(f"  Supplier reliability: {data.get('supplier_reliability', 0.8):.3f}")
        print(f"  Weather impact: {data.get('weather_impact', 0.05):.3f}")

        # Find the factor with the highest risk
        max_risk_factor = max(factors.items(), key=lambda x: x[1])
        max_risk_value = max_risk_factor[1]

        # Use dynamic thresholds based on delay probability
        if delay_probability > 0.7:
            # High delay probability - use lower threshold
            threshold = 0.2
        elif delay_probability > 0.5:
            # Medium delay probability - use medium threshold
            threshold = 0.3
        else:
            # Low delay probability - use higher threshold
            threshold = 0.4

        print(
            f"  Max risk factor: {max_risk_factor[0]} (value: {max_risk_value:.3f}, threshold: {threshold:.3f})"
        )

        if max_risk_value > threshold:
            return max_risk_factor[0]
        else:
            # If no single factor is significantly high, check for multiple factors
            significant_factors = {
                k: v for k, v in factors.items() if v > threshold * 0.7
            }
            if len(significant_factors) > 1:
                return "Multiple Risk Factors"
            else:
                return "General Production Risk"

    def _get_risk_level(self, delay_probability: float) -> str:
        """
        Get risk level based on delay probability.

        Args:
            delay_probability (float): Predicted delay probability

        Returns:
            str: Risk level
        """
        if delay_probability < 0.3:
            return "Low"
        elif delay_probability < 0.6:
            return "Medium"
        else:
            return "High"

    def _get_confidence(self, delay_probability: float) -> str:
        """
        Get confidence level based on delay probability.

        Args:
            delay_probability (float): Predicted delay probability

        Returns:
            str: Confidence level
        """
        if delay_probability < 0.2 or delay_probability > 0.8:
            return "High"
        elif delay_probability < 0.4 or delay_probability > 0.6:
            return "Medium"
        else:
            return "Low"

    def save_model(self):
        """Save the trained model and components to disk."""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            joblib.dump(self.label_encoders, self.encoders_path)
            joblib.dump(self.feature_columns, self.features_path)
            print(f"Model saved successfully to {self.model_path}")
        except Exception as e:
            print(f"Error saving model: {e}")

    def load_model(self):
        """Load the trained model and components from disk."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print("Model loaded successfully")

                # Load scaler if it exists
                if os.path.exists(self.scaler_path):
                    self.scaler = joblib.load(self.scaler_path)
                    print("Scaler loaded successfully")
                else:
                    print("No scaler found, creating new one")
                    self.scaler = StandardScaler()

                # Load encoders if they exist
                if os.path.exists(self.encoders_path):
                    self.label_encoders = joblib.load(self.encoders_path)
                    print("Encoders loaded successfully")
                else:
                    print("No encoders found, creating new ones")
                    self.label_encoders = {}

                # Load feature columns if they exist
                if os.path.exists(self.features_path):
                    self.feature_columns = joblib.load(self.features_path)
                    print("Feature columns loaded successfully")
                else:
                    print("No feature columns found, creating new ones")
                    self.feature_columns = []

            else:
                print("No saved model found. Please train the model first.")
        except Exception as e:
            print(f"Error loading model: {e}")
            # Initialize new components if loading fails
            self.scaler = StandardScaler()
            self.label_encoders = {}

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "model_type": self.model_type,
            "is_trained": self.model is not None,
            "feature_columns": self.feature_columns,
            "model_path": self.model_path,
            "last_updated": datetime.now().isoformat(),
        }
