"""
Analytics Tools for LangGraph Agents

Provides tools for agents to query the analytics warehouse and get ML predictions.
"""

import logging
from langchain.tools import tool
from typing import Dict, Any

from recruitment.analytics.queries import AnalyticsQueries
from recruitment.analytics.ml_models import CandidateSuccessPredictor, TimeToHirePredictor

logger = logging.getLogger(__name__)


@tool
def query_candidate_success_rate(job_title: str) -> dict:
    """
    Query historical success rate for jobs matching a title pattern.
    
    Useful for understanding how well candidates typically perform for similar positions.
    
    Args:
        job_title: Job title or pattern to search for (e.g., "Software Engineer")
        
    Returns:
        Dictionary with success_rate, avg_ai_score, total_applications, accepted_count
    """
    try:
        queries = AnalyticsQueries()
        result = queries.get_candidate_success_rate(job_title)
        
        logger.info(f"📊 Success rate for '{job_title}': {result['success_rate']:.1%}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to query success rate: {e}")
        return {
            'error': str(e),
            'success_rate': 0.0,
            'total_applications': 0
        }


@tool
def get_hiring_trends(days: int = 30) -> dict:
    """
    Get recent hiring trends and statistics.
    
    Useful for understanding current recruitment patterns and performance.
    
    Args:
        days: Number of days to look back (default: 30)
        
    Returns:
        Dictionary with applications, avg_score, accepted, rejected, pending, acceptance_rate
    """
    try:
        queries = AnalyticsQueries()
        result = queries.get_hiring_trends(days)
        
        logger.info(f"📈 Hiring trends (last {days} days): {result['applications']} applications, {result['acceptance_rate']:.1%} acceptance rate")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get hiring trends: {e}")
        return {
            'error': str(e),
            'applications': 0,
            'acceptance_rate': 0.0
        }


@tool
def predict_candidate_success(
    ai_score: int,
    technical_score: int,
    experience_score: int,
    culture_score: int,
    confidence_score: float
) -> dict:
    """
    Predict the probability of a candidate being hired using ML model.
    
    Uses a trained Random Forest model based on historical hiring data.
    
    Args:
        ai_score: Overall AI score (0-100)
        technical_score: Technical skills score (0-100)
        experience_score: Experience level score (0-100)
        culture_score: Culture fit score (0-100)
        confidence_score: AI confidence score (0-1)
        
    Returns:
        Dictionary with will_be_hired (bool), hire_probability (float), confidence (str)
    """
    try:
        predictor = CandidateSuccessPredictor()
        result = predictor.predict(
            ai_score=ai_score,
            technical=technical_score,
            experience=experience_score,
            culture=culture_score,
            confidence=confidence_score
        )
        
        logger.info(f"🤖 ML Prediction: {result['hire_probability']:.1%} probability of hire")
        return result
        
    except Exception as e:
        logger.error(f"Failed to predict candidate success: {e}")
        return {
            'error': str(e),
            'will_be_hired': False,
            'hire_probability': 0.0,
            'confidence': 'low'
        }


@tool
def get_analytics_summary() -> dict:
    """
    Get overall analytics summary with key recruitment metrics.
    
    Provides a high-level overview of the recruitment pipeline performance.
    
    Returns:
        Dictionary with total_applications, unique_candidates, unique_jobs, avg_ai_score, 
        acceptance_rate, and other key metrics
    """
    try:
        queries = AnalyticsQueries()
        result = queries.get_analytics_summary()
        
        logger.info(f"📊 Analytics summary: {result.get('total_applications', 0)} applications, {result.get('acceptance_rate', 0):.1%} acceptance rate")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}")
        return {
            'error': str(e),
            'total_applications': 0
        }


@tool
def analyze_bias_patterns() -> dict:
    """
    Analyze bias detection patterns from safety guardrails.
    
    Useful for understanding and mitigating bias in the recruitment process.
    
    Returns:
        Dictionary with bias statistics and trends
    """
    try:
        queries = AnalyticsQueries()
        
        # Get safety trends
        safety_df = queries.get_safety_trends(weeks=12)
        
        if len(safety_df) == 0:
            return {
                'total_bias_detected': 0,
                'avg_bias_per_application': 0.0,
                'trend': 'no_data'
            }
        
        total_bias = safety_df['total_bias_detected'].sum()
        total_apps = safety_df['total_applications'].sum()
        avg_bias = total_bias / total_apps if total_apps > 0 else 0.0
        
        # Determine trend (comparing first half vs second half of period)
        mid_point = len(safety_df) // 2
        recent_avg = safety_df.head(mid_point)['total_bias_detected'].mean()
        older_avg = safety_df.tail(mid_point)['total_bias_detected'].mean()
        
        if recent_avg > older_avg * 1.1:
            trend = 'increasing'
        elif recent_avg < older_avg * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        result = {
            'total_bias_detected': int(total_bias),
            'avg_bias_per_application': float(avg_bias),
            'trend': trend,
            'weeks_analyzed': len(safety_df)
        }
        
        logger.info(f"⚖️  Bias analysis: {total_bias} issues detected, trend: {trend}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze bias patterns: {e}")
        return {
            'error': str(e),
            'total_bias_detected': 0
        }


# List of all analytics tools for easy import
ANALYTICS_TOOLS = [
    query_candidate_success_rate,
    get_hiring_trends,
    predict_candidate_success,
    get_analytics_summary,
    analyze_bias_patterns
]
