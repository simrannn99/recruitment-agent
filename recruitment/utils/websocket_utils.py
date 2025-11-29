"""
Utility functions for WebSocket notifications.

This module provides helper functions to send real-time updates
to WebSocket clients when Celery tasks complete.
"""

import logging
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def send_task_update(task_id, status, result=None, error=None, progress=None):
    """
    Send a task status update to all WebSocket clients listening to this task.
    
    Args:
        task_id (str): Celery task ID
        status (str): Task status ('started', 'completed', 'failed', 'progress')
        result (dict, optional): Task result data
        error (str, optional): Error message if task failed
        progress (dict, optional): Progress information for long-running tasks
                                   e.g., {'current': 5, 'total': 10, 'percent': 50}
    
    Example:
        send_task_update(
            task_id='abc-123',
            status='completed',
            result={'embedding_dimension': 384}
        )
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        logger.warning("Channel layer not configured. WebSocket updates disabled.")
        return
    
    room_group_name = f'task_{task_id}'
    
    message = {
        'type': 'task_update',
        'task_id': task_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    
    if result is not None:
        message['result'] = result
    
    if error is not None:
        message['error'] = error
    
    if progress is not None:
        message['progress'] = progress
    
    try:
        # Send message to WebSocket group
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            message
        )
        logger.info(f"Sent WebSocket update for task {task_id}: {status}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket update for task {task_id}: {str(e)}")


def send_batch_progress(batch_id, current, total, status_message=None):
    """
    Send progress update for batch operations.
    
    Args:
        batch_id (str): Batch operation identifier
        current (int): Current progress count
        total (int): Total items to process
        status_message (str, optional): Human-readable status message
    
    Example:
        send_batch_progress(
            batch_id='batch-job-123',
            current=5,
            total=20,
            status_message='Processing application 5 of 20'
        )
    """
    percent = int((current / total) * 100) if total > 0 else 0
    
    send_task_update(
        task_id=batch_id,
        status='progress',
        progress={
            'current': current,
            'total': total,
            'percent': percent,
            'message': status_message or f'Processing {current}/{total}'
        }
    )
