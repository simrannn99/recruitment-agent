"""
Machine Learning Models for Recruitment Analytics

Uses scikit-learn to train predictive models on historical recruitment data.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_absolute_error
import joblib

from recruitment.analytics.client import get_client

logger = logging.getLogger(__name__)


class CandidateSuccessPredictor:
    """
    Predicts the probability of a candidate being hired based on AI scores and safety metrics.
    
    Uses Random Forest Classifier for binary classification.
    """
    
    def __init__(self, model_path: str = 'models/candidate_success.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_names = [
            'ai_score', 'technical_score', 'experience_score', 
            'culture_score', 'confidence_score', 'pii_count', 
            'bias_count', 'toxicity_score'
        ]
        
        # Create models directory
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    
    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load and prepare training data from DuckDB.
        
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        client = get_client()
        
        query = """
        SELECT 
            ai_score,
            technical_score,
            experience_score,
            culture_score,
            confidence_score,
            pii_count,
            bias_count,
            toxicity_score,
            CASE WHEN status = 'accepted' THEN 1 ELSE 0 END as hired
        FROM fact_applications
        WHERE ai_score IS NOT NULL
            AND technical_score IS NOT NULL
            AND experience_score IS NOT NULL
            AND culture_score IS NOT NULL
        """
        
        df = client.query_df(query)
        
        if len(df) == 0:
            raise ValueError("No training data available. Please sync data to analytics warehouse first.")
        
        # Fill missing values
        df = df.fillna(0)
        
        X = df[self.feature_names]
        y = df['hired']
        
        logger.info(f"Loaded {len(df)} training samples")
        logger.info(f"  Hired: {y.sum()} ({y.mean()*100:.1f}%)")
        logger.info(f"  Not hired: {(1-y).sum()} ({(1-y).mean()*100:.1f}%)")
        
        return X, y
    
    def train(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, float]:
        """
        Train the candidate success prediction model.
        
        Args:
            test_size: Proportion of data to use for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            logger.info("🤖 Training candidate success prediction model...")
            
            # Load data
            X, y = self.prepare_training_data()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                class_weight='balanced'  # Handle class imbalance
            )
            
            self.model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)[:, 1]
            
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1_score': f1_score(y_test, y_pred, zero_division=0),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
            # Cross-validation
            cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='f1')
            metrics['cv_f1_mean'] = cv_scores.mean()
            metrics['cv_f1_std'] = cv_scores.std()
            
            # Feature importance
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info("✅ Model training completed")
            logger.info(f"  Accuracy: {metrics['accuracy']:.3f}")
            logger.info(f"  Precision: {metrics['precision']:.3f}")
            logger.info(f"  Recall: {metrics['recall']:.3f}")
            logger.info(f"  F1 Score: {metrics['f1_score']:.3f}")
            logger.info(f"  CV F1: {metrics['cv_f1_mean']:.3f} (+/- {metrics['cv_f1_std']:.3f})")
            logger.info("\n  Feature Importance:")
            for _, row in feature_importance.head(5).iterrows():
                logger.info(f"    {row['feature']}: {row['importance']:.3f}")
            
            # Save model
            self.save()
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            raise
    
    def predict(self, ai_score: int, technical: int, experience: int, 
                culture: int, confidence: float, pii_count: int = 0,
                bias_count: int = 0, toxicity_score: float = 0.0) -> Dict[str, Any]:
        """
        Predict hire probability for a candidate.
        
        Args:
            ai_score: Overall AI score (0-100)
            technical: Technical score (0-100)
            experience: Experience score (0-100)
            culture: Culture fit score (0-100)
            confidence: Confidence score (0-1)
            pii_count: Number of PII entities detected
            bias_count: Number of bias issues detected
            toxicity_score: Toxicity score (0-1)
            
        Returns:
            Dictionary with prediction and probability
        """
        if self.model is None:
            self.load()
        
        # Prepare features
        features = pd.DataFrame([{
            'ai_score': ai_score,
            'technical_score': technical,
            'experience_score': experience,
            'culture_score': culture,
            'confidence_score': confidence,
            'pii_count': pii_count,
            'bias_count': bias_count,
            'toxicity_score': toxicity_score
        }])
        
        # Predict
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0][1]
        
        return {
            'will_be_hired': bool(prediction),
            'hire_probability': float(probability),
            'confidence': 'high' if probability > 0.7 or probability < 0.3 else 'medium'
        }
    
    def save(self):
        """Save the trained model to disk."""
        if self.model is not None:
            joblib.dump(self.model, self.model_path)
            logger.info(f"💾 Model saved to {self.model_path}")
    
    def load(self):
        """Load a trained model from disk."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info(f"📂 Model loaded from {self.model_path}")
        else:
            raise FileNotFoundError(f"Model not found at {self.model_path}. Please train the model first.")


class TimeToHirePredictor:
    """
    Predicts the estimated time to hire for a job posting.
    
    Uses Linear Regression.
    """
    
    def __init__(self, model_path: str = 'models/time_to_hire.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_names = ['avg_ai_score', 'total_applications', 'accepted_count']
        
        # Create models directory
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    
    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load and prepare training data."""
        client = get_client()
        
        query = """
        SELECT 
            job_id,
            AVG(ai_score) as avg_ai_score,
            COUNT(*) as total_applications,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
            AVG(days_to_decision) as avg_days_to_hire
        FROM fact_applications
        WHERE ai_score IS NOT NULL
            AND days_to_decision IS NOT NULL
            AND days_to_decision > 0
        GROUP BY job_id
        HAVING COUNT(*) >= 3
        """
        
        df = client.query_df(query)
        
        if len(df) == 0:
            raise ValueError("No training data available for time-to-hire prediction.")
        
        X = df[self.feature_names]
        y = df['avg_days_to_hire']
        
        logger.info(f"Loaded {len(df)} job postings for training")
        
        return X, y
    
    def train(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, float]:
        """Train the time-to-hire prediction model."""
        try:
            logger.info("🤖 Training time-to-hire prediction model...")
            
            # Load data
            X, y = self.prepare_training_data()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
            
            # Train model
            self.model = LinearRegression()
            self.model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test)
            
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
            logger.info("✅ Time-to-hire model training completed")
            logger.info(f"  Mean Absolute Error: {metrics['mae']:.1f} days")
            
            # Save model
            self.save()
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Time-to-hire model training failed: {e}")
            raise
    
    def predict(self, avg_ai_score: float, total_applications: int, 
                accepted_count: int) -> Dict[str, Any]:
        """Predict time to hire."""
        if self.model is None:
            self.load()
        
        features = pd.DataFrame([{
            'avg_ai_score': avg_ai_score,
            'total_applications': total_applications,
            'accepted_count': accepted_count
        }])
        
        days = self.model.predict(features)[0]
        
        return {
            'estimated_days': max(1, int(days)),  # At least 1 day
            'estimated_weeks': max(1, int(days / 7))
        }
    
    def save(self):
        """Save the trained model."""
        if self.model is not None:
            joblib.dump(self.model, self.model_path)
            logger.info(f"💾 Model saved to {self.model_path}")
    
    def load(self):
        """Load a trained model."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info(f"📂 Model loaded from {self.model_path}")
        else:
            raise FileNotFoundError(f"Model not found at {self.model_path}")


# Convenience functions
def train_all_models() -> Dict[str, Dict[str, float]]:
    """Train all ML models."""
    results = {}
    
    try:
        # Train candidate success predictor
        success_predictor = CandidateSuccessPredictor()
        results['candidate_success'] = success_predictor.train()
    except Exception as e:
        logger.error(f"Failed to train candidate success model: {e}")
        results['candidate_success'] = {'error': str(e)}
    
    try:
        # Train time-to-hire predictor
        time_predictor = TimeToHirePredictor()
        results['time_to_hire'] = time_predictor.train()
    except Exception as e:
        logger.error(f"Failed to train time-to-hire model: {e}")
        results['time_to_hire'] = {'error': str(e)}
    
    return results
