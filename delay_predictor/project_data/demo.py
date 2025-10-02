#!/usr/bin/env python3
"""
Demo script for Delay Predictor
Shows the core functionality: data generation, model training, and prediction
"""

import sys
import os

# Add the app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "delay_predictor"))

from services.production_delay_predictor.data_generator import ProductionDataGenerator
from services.production_delay_predictor.delay_predictor import ProductionDelayPredictor


def demo_delay_prediction():
    """
    Demonstrate the core delay prediction functionality.
    """
    print("🚀 Delay Predictor - Demo")
    print("=" * 50)

    # Step 1: Generate simulated production data
    print("\n1. Generating Simulated Production Data...")
    data_generator = ProductionDataGenerator(seed=42)
    df = data_generator.generate_production_orders(150)
    print(f"   ✅ Generated {len(df)} production orders")
    print(f"   📊 Delay rate: {df['is_delayed'].mean():.1%}")

    # Show sample data
    print("\n   Sample data:")
    sample_cols = [
        "order_id",
        "material_availability",
        "machine_availability",
        "workforce_availability",
        "is_delayed",
        "delay_reason",
    ]
    print(df[sample_cols].head(3).to_string(index=False))

    # Step 2: Train ML model
    print("\n2. Training Machine Learning Model...")
    predictor = ProductionDelayPredictor(model_type="random_forest")
    results = predictor.train(df)
    print(f"   ✅ Model trained successfully")
    print(f"   📈 Accuracy: {results['accuracy']:.3f}")
    print(f"   📈 Cross-validation: {results['cv_mean']:.3f} ± {results['cv_std']:.3f}")

    # Step 3: Test predictions
    print("\n3. Testing Predictions...")
    test_orders = df.sample(3)
    for idx, order in test_orders.iterrows():
        prediction = predictor.predict(order.to_dict())
        actual_delay = "Yes" if order["is_delayed"] else "No"
        predicted_delay = "Yes" if prediction["is_delayed"] else "No"
        correct = "✅" if (order["is_delayed"] == prediction["is_delayed"]) else "❌"

        print(f"\n   Order {order['order_id']}:")
        print(f"     Material Availability: {order['material_availability']:.1%}")
        print(f"     Machine Availability: {order['machine_availability']:.1%}")
        print(f"     Workforce Availability: {order['workforce_availability']:.1%}")
        print(
            f"     Predicted Delay Probability: {prediction['delay_probability']:.1%}"
        )
        print(f"     Risk Level: {prediction['risk_level']}")
        print(f"     Predicted: {predicted_delay}, Actual: {actual_delay} {correct}")
        print(f"     Delay Reason: {prediction['delay_reason']}")

    # Step 4: Feature importance
    print("\n4. Feature Importance Analysis...")
    feature_importance = results["feature_importance"]
    top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]
    print("   Top 5 Most Important Features:")
    for feature, importance in top_features:
        print(f"     {feature}: {importance:.3f}")

    # Summary
    print("\n" + "=" * 50)
    print("🎉 Demo Completed Successfully!")
    print(f"📊 Model Accuracy: {results['accuracy']:.1%}")
    print(f"📈 Delay Rate in Data: {df['is_delayed'].mean():.1%}")
    print("=" * 50)


def demo_model_comparison():
    """
    Compare different ML models for delay prediction.
    """
    print("\n🔬 Model Comparison Demo")
    print("=" * 30)

    # Generate data
    data_generator = ProductionDataGenerator(seed=42)
    df = data_generator.generate_production_orders(200)

    models = ["random_forest", "decision_tree", "logistic_regression"]
    results = {}

    for model_type in models:
        print(f"\nTesting {model_type}...")
        predictor = ProductionDelayPredictor(model_type=model_type)
        result = predictor.train(df)
        results[model_type] = {
            "accuracy": result["accuracy"],
            "cv_mean": result["cv_mean"],
            "cv_std": result["cv_std"],
        }
        print(f"  Accuracy: {result['accuracy']:.3f}")
        print(f"  CV Score: {result['cv_mean']:.3f} ± {result['cv_std']:.3f}")

    # Find best model
    best_model = max(results.items(), key=lambda x: x[1]["accuracy"])
    print(
        f"\n🏆 Best Model: {best_model[0]} with {best_model[1]['accuracy']:.3f} accuracy"
    )


if __name__ == "__main__":
    try:
        # Run main demo
        demo_delay_prediction()

        # Run model comparison
        demo_model_comparison()

        print("\n✅ Demo completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
