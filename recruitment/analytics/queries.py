"""
Analytics Queries

Pre-built SQL queries for common recruitment analytics use cases.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from recruitment.analytics.client import get_client

logger = logging.getLogger(__name__)


class AnalyticsQueries:
    """Collection of analytics queries for recruitment data."""
    
    def __init__(self):
        self.client = get_client()
    
    def get_hiring_funnel(self) -> pd.DataFrame:
        """
        Get hiring funnel metrics.
        
        Returns:
            DataFrame with status, count, avg_score, and percentage
        """
        query = """
        SELECT 
            status,
            COUNT(*) as count,
            AVG(ai_score) as avg_ai_score,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
        FROM fact_applications
        WHERE ai_score IS NOT NULL
        GROUP BY status
        ORDER BY 
            CASE status 
                WHEN 'pending' THEN 1 
                WHEN 'accepted' THEN 2 
                WHEN 'rejected' THEN 3 
            END
        """
        return self.client.query_df(query)
    
    def get_ai_performance_over_time(self, days: int = 30) -> pd.DataFrame:
        """
        Get AI performance metrics over time.
        
        Args:
            days: Number of days to look back
            
        Returns:
            DataFrame with daily AI performance metrics
        """
        query = f"""
        SELECT 
            DATE_TRUNC('day', applied_at) as date,
            COUNT(*) as applications,
            AVG(ai_score) as avg_ai_score,
            AVG(technical_score) as avg_technical,
            AVG(experience_score) as avg_experience,
            AVG(culture_score) as avg_culture,
            AVG(confidence_score) as avg_confidence,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
        FROM fact_applications
        WHERE ai_score IS NOT NULL
            AND applied_at >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY date
        ORDER BY date DESC
        """
        return self.client.query_df(query)
    
    def get_top_candidates(self, limit: int = 10) -> pd.DataFrame:
        """
        Get top performing candidates based on AI scores.
        
        Args:
            limit: Number of candidates to return
            
        Returns:
            DataFrame with top candidates
        """
        query = f"""
        SELECT 
            candidate_id,
            candidate_name,
            candidate_email,
            COUNT(*) as total_applications,
            AVG(ai_score) as avg_ai_score,
            MAX(ai_score) as max_ai_score,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
        FROM fact_applications
        WHERE ai_score IS NOT NULL
        GROUP BY candidate_id, candidate_name, candidate_email
        HAVING COUNT(*) >= 1
        ORDER BY avg_ai_score DESC
        LIMIT {limit}
        """
        return self.client.query_df(query)
    
    def get_safety_trends(self, weeks: int = 12) -> pd.DataFrame:
        """
        Get safety guardrail trends over time.
        
        Args:
            weeks: Number of weeks to look back
            
        Returns:
            DataFrame with weekly safety metrics
        """
        query = f"""
        SELECT 
            DATE_TRUNC('week', applied_at) as week,
            COUNT(*) as total_applications,
            SUM(pii_count) as total_pii_detected,
            SUM(bias_count) as total_bias_detected,
            AVG(toxicity_score) as avg_toxicity,
            SUM(CASE WHEN has_safety_issues THEN 1 ELSE 0 END) as applications_with_issues,
            SUM(CASE WHEN has_safety_issues THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as issue_percentage
        FROM fact_applications
        WHERE applied_at >= CURRENT_DATE - INTERVAL '{weeks}' WEEK
        GROUP BY week
        ORDER BY week DESC
        """
        return self.client.query_df(query)
    
    def get_job_performance(self, limit: int = 10) -> pd.DataFrame:
        """
        Get job posting performance metrics.
        
        Args:
            limit: Number of jobs to return
            
        Returns:
            DataFrame with job performance metrics
        """
        query = f"""
        SELECT 
            job_id,
            job_title,
            COUNT(*) as total_applications,
            AVG(ai_score) as avg_ai_score,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
            AVG(days_to_decision) as avg_days_to_decision
        FROM fact_applications
        WHERE ai_score IS NOT NULL
        GROUP BY job_id, job_title
        HAVING COUNT(*) >= 1
        ORDER BY total_applications DESC
        LIMIT {limit}
        """
        return self.client.query_df(query)
    
    def get_candidate_success_rate(self, job_title_pattern: str) -> Dict[str, Any]:
        """
        Get historical success rate for jobs matching a pattern.
        
        Args:
            job_title_pattern: Pattern to match job titles (e.g., "Software Engineer")
            
        Returns:
            Dictionary with success rate metrics
        """
        query = """
        SELECT 
            AVG(CASE WHEN status = 'accepted' THEN 1.0 ELSE 0.0 END) as success_rate,
            AVG(ai_score) as avg_ai_score,
            COUNT(*) as total_applications,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count
        FROM fact_applications
        WHERE job_title LIKE ?
            AND ai_score IS NOT NULL
        """
        result = self.client.execute(query, [f"%{job_title_pattern}%"]).fetchone()
        
        if result and result[2] > 0:  # total_applications > 0
            return {
                'success_rate': result[0] or 0.0,
                'avg_ai_score': result[1] or 0.0,
                'total_applications': result[2],
                'accepted_count': result[3]
            }
        else:
            return {
                'success_rate': 0.0,
                'avg_ai_score': 0.0,
                'total_applications': 0,
                'accepted_count': 0
            }
    
    def get_hiring_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Get recent hiring trends.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with hiring trend metrics
        """
        query = f"""
        SELECT 
            COUNT(*) as applications,
            AVG(ai_score) as avg_score,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
        FROM fact_applications
        WHERE applied_at >= CURRENT_DATE - INTERVAL '{days}' DAY
            AND ai_score IS NOT NULL
        """
        result = self.client.execute(query).fetchone()
        
        if result and result[0] > 0:  # applications > 0
            return {
                'applications': result[0],
                'avg_score': result[1] or 0.0,
                'accepted': result[2],
                'rejected': result[3],
                'pending': result[4],
                'acceptance_rate': result[2] / result[0] if result[0] > 0 else 0.0
            }
        else:
            return {
                'applications': 0,
                'avg_score': 0.0,
                'accepted': 0,
                'rejected': 0,
                'pending': 0,
                'acceptance_rate': 0.0
            }
    
    def get_score_distribution(self) -> pd.DataFrame:
        """
        Get AI score distribution.
        
        Returns:
            DataFrame with score ranges and counts
        """
        query = """
        SELECT 
            CASE 
                WHEN ai_score >= 90 THEN '90-100 (Excellent)'
                WHEN ai_score >= 75 THEN '75-89 (Good)'
                WHEN ai_score >= 50 THEN '50-74 (Fair)'
                ELSE '0-49 (Poor)'
            END as score_range,
            COUNT(*) as count,
            AVG(ai_score) as avg_score,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
        FROM fact_applications
        WHERE ai_score IS NOT NULL
        GROUP BY score_range
        ORDER BY 
            CASE score_range
                WHEN '90-100 (Excellent)' THEN 1
                WHEN '75-89 (Good)' THEN 2
                WHEN '50-74 (Fair)' THEN 3
                ELSE 4
            END
        """
        return self.client.query_df(query)
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Get overall analytics summary.
        
        Returns:
            Dictionary with key metrics
        """
        query = """
        SELECT 
            COUNT(*) as total_applications,
            COUNT(DISTINCT candidate_id) as unique_candidates,
            COUNT(DISTINCT job_id) as unique_jobs,
            AVG(ai_score) as avg_ai_score,
            SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as total_accepted,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as total_rejected,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as total_pending,
            AVG(confidence_score) as avg_confidence,
            SUM(has_safety_issues) as applications_with_safety_issues
        FROM fact_applications
        WHERE ai_score IS NOT NULL
        """
        result = self.client.execute(query).fetchone()
        
        if result:
            return {
                'total_applications': result[0],
                'unique_candidates': result[1],
                'unique_jobs': result[2],
                'avg_ai_score': result[3] or 0.0,
                'total_accepted': result[4],
                'total_rejected': result[5],
                'total_pending': result[6],
                'avg_confidence': result[7] or 0.0,
                'applications_with_safety_issues': result[8],
                'acceptance_rate': result[4] / result[0] if result[0] > 0 else 0.0
            }
        else:
            return {}


# Convenience functions
def get_hiring_funnel() -> pd.DataFrame:
    """Get hiring funnel metrics."""
    return AnalyticsQueries().get_hiring_funnel()


def get_ai_performance_over_time(days: int = 30) -> pd.DataFrame:
    """Get AI performance over time."""
    return AnalyticsQueries().get_ai_performance_over_time(days)


def get_top_candidates(limit: int = 10) -> pd.DataFrame:
    """Get top candidates."""
    return AnalyticsQueries().get_top_candidates(limit)


def get_analytics_summary() -> Dict[str, Any]:
    """Get analytics summary."""
    return AnalyticsQueries().get_analytics_summary()
