"""
WebSocket consumer for real-time task status updates.

This consumer handles WebSocket connections for monitoring Celery task progress.
Clients connect to ws/tasks/<task_id>/ and receive real-time updates when tasks complete.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TaskStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for task status updates.
    
    URL: ws/tasks/<task_id>/
    
    Messages sent to clients:
    {
        "type": "task_update",
        "task_id": "abc-123",
        "status": "completed",
        "result": {...},
        "timestamp": "2025-11-29T18:00:00Z"
    }
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'
        
        # Join task-specific channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"WebSocket connected for task {self.task_id}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'task_id': self.task_id,
            'message': f'Connected to task {self.task_id}'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave task-specific channel group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected for task {self.task_id} (code: {close_code})")
    
    async def receive(self, text_data):
        """
        Handle messages from WebSocket client.
        
        Currently not used, but could be extended for:
        - Requesting current task status
        - Canceling tasks
        - Subscribing to multiple tasks
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
    
    async def task_update(self, event):
        """
        Handle task update messages from channel layer.
        
        This method is called when a message is sent to the group
        via channel_layer.group_send().
        """
        # Send message to WebSocket client
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'task_id': event['task_id'],
            'status': event['status'],
            'result': event.get('result'),
            'error': event.get('error'),
            'timestamp': event.get('timestamp'),
            'progress': event.get('progress'),  # For long-running tasks
        }))
