"""
Redis Real-Time Features & WebSocket Integration
===============================================

Advanced real-time features using Redis Pub/Sub with WebSocket support
for live inventory updates, order tracking, and notifications.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime
import uuid
from enum import Enum

try:
    import websockets
    from fastapi import WebSocket, WebSocketDisconnect
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

from .redis_database import redis_db, realtime

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of real-time messages"""
    INVENTORY_UPDATE = "inventory_update"
    ORDER_STATUS = "order_status"
    USER_NOTIFICATION = "user_notification"
    PRICE_UPDATE = "price_update"
    SYSTEM_ALERT = "system_alert"
    BOOKING_UPDATE = "booking_update"
    LIVE_CHAT = "live_chat"
    ACTIVITY_FEED = "activity_feed"

class RedisWebSocketManager:
    """Manage WebSocket connections with Redis coordination"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}  # user_id -> set of connection_ids
        self.connection_subscriptions: Dict[str, Set[str]] = {}  # connection_id -> set of channels
        self.channel_subscribers: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        
        # Redis channels for different message types
        self.channels = {
            MessageType.INVENTORY_UPDATE: "realtime:inventory",
            MessageType.ORDER_STATUS: "realtime:orders",
            MessageType.USER_NOTIFICATION: "realtime:notifications",
            MessageType.PRICE_UPDATE: "realtime:prices",
            MessageType.SYSTEM_ALERT: "realtime:system",
            MessageType.BOOKING_UPDATE: "realtime:bookings",
            MessageType.LIVE_CHAT: "realtime:chat",
            MessageType.ACTIVITY_FEED: "realtime:activity"
        }
        
        # Start Redis subscribers
        if redis_db.enabled:
            asyncio.create_task(self._start_redis_subscribers())
    
    async def connect(self, websocket: WebSocket, user_id: int = None, 
                     connection_id: str = None) -> str:
        """Accept WebSocket connection and register with Redis"""
        await websocket.accept()
        
        if not connection_id:
            connection_id = str(uuid.uuid4())
        
        self.active_connections[connection_id] = websocket
        
        # Associate with user if provided
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        # Store connection info in Redis for cluster coordination
        if redis_db.enabled:
            connection_info = {
                "user_id": user_id,
                "connected_at": datetime.now().isoformat(),
                "server_id": "server_1"  # For multi-server deployments
            }
            redis_db.client.setex(
                f"ws_connection:{connection_id}",
                3600,  # 1 hour TTL
                json.dumps(connection_info)
            )
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket and clean up"""
        
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from user connections
        for user_id, conn_set in self.user_connections.items():
            if connection_id in conn_set:
                conn_set.remove(connection_id)
                if not conn_set:  # Remove empty sets
                    del self.user_connections[user_id]
                break
        
        # Remove from channel subscriptions
        if connection_id in self.connection_subscriptions:
            for channel in self.connection_subscriptions[connection_id]:
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(connection_id)
            del self.connection_subscriptions[connection_id]
        
        # Clean up Redis
        if redis_db.enabled:
            redis_db.client.delete(f"ws_connection:{connection_id}")
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe WebSocket connection to a channel"""
        if connection_id not in self.active_connections:
            return False
        
        # Add to subscriptions
        if connection_id not in self.connection_subscriptions:
            self.connection_subscriptions[connection_id] = set()
        self.connection_subscriptions[connection_id].add(channel)
        
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to {channel}")
        return True
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe WebSocket connection from a channel"""
        if connection_id in self.connection_subscriptions:
            self.connection_subscriptions[connection_id].discard(channel)
        
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(connection_id)
        
        logger.info(f"Connection {connection_id} unsubscribed from {channel}")
    
    async def send_message_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific WebSocket connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(
                    json.dumps(message, default=str)
                )
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                await self.disconnect(connection_id)
                return False
        return False
    
    async def send_message_to_user(self, user_id: int, message: Dict[str, Any]):
        """Send message to all connections of a user"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            sent_count = 0
            
            for conn_id in connection_ids:
                if await self.send_message_to_connection(conn_id, message):
                    sent_count += 1
            
            return sent_count
        return 0
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel"""
        if channel in self.channel_subscribers:
            connection_ids = list(self.channel_subscribers[channel])
            sent_count = 0
            
            for conn_id in connection_ids:
                if await self.send_message_to_connection(conn_id, message):
                    sent_count += 1
            
            return sent_count
        return 0
    
    async def _start_redis_subscribers(self):
        """Start Redis Pub/Sub subscribers for all channels"""
        try:
            for message_type, channel in self.channels.items():
                await realtime.subscribe_to_channel(
                    channel,
                    lambda msg, ch=channel: self._handle_redis_message(ch, msg)
                )
            logger.info("Started Redis subscribers for WebSocket integration")
        except Exception as e:
            logger.error(f"Failed to start Redis subscribers: {e}")
    
    async def _handle_redis_message(self, channel: str, message: Dict[str, Any]):
        """Handle incoming Redis Pub/Sub message"""
        try:
            # Add channel info to message
            message["channel"] = channel
            message["timestamp"] = datetime.now().isoformat()
            
            # Broadcast to WebSocket subscribers
            sent_count = await self.broadcast_to_channel(channel, message)
            logger.debug(f"Broadcasted Redis message to {sent_count} WebSocket connections")
            
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "total_users_connected": sum(1 for conns in self.user_connections.values() if conns),
            "channel_subscriptions": {
                channel: len(subscribers) 
                for channel, subscribers in self.channel_subscribers.items()
            },
            "redis_enabled": redis_db.enabled
        }

class RedisLiveInventory:
    """Real-time inventory tracking with Redis"""
    
    def __init__(self, websocket_manager: RedisWebSocketManager):
        self.ws_manager = websocket_manager
        self.inventory_cache_ttl = 60  # 1 minute
    
    async def update_product_availability(self, product_id: int, 
                                        availability_data: Dict[str, Any]):
        """Update product availability and notify subscribers"""
        
        # Update Redis cache
        if redis_db.enabled:
            cache_key = f"live_inventory:{product_id}"
            availability_data["last_updated"] = datetime.now().isoformat()
            redis_db.client.setex(
                cache_key,
                self.inventory_cache_ttl,
                json.dumps(availability_data, default=str)
            )
        
        # Publish to Redis for other servers
        await realtime.publish_inventory_update(product_id, availability_data)
        
        # Notify WebSocket subscribers
        message = {
            "type": MessageType.INVENTORY_UPDATE.value,
            "product_id": product_id,
            "data": availability_data
        }
        
        channel = self.ws_manager.channels[MessageType.INVENTORY_UPDATE]
        await self.ws_manager.broadcast_to_channel(channel, message)
        
        logger.info(f"Updated live inventory for product {product_id}")
    
    async def get_live_availability(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get real-time availability data"""
        if not redis_db.enabled:
            return None
        
        cache_key = f"live_inventory:{product_id}"
        cached_data = redis_db.client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def subscribe_to_product_updates(self, connection_id: str, product_ids: List[int]):
        """Subscribe connection to specific product updates"""
        for product_id in product_ids:
            channel = f"product_updates:{product_id}"
            await self.ws_manager.subscribe_to_channel(connection_id, channel)

class RedisLiveOrders:
    """Real-time order tracking with Redis"""
    
    def __init__(self, websocket_manager: RedisWebSocketManager):
        self.ws_manager = websocket_manager
    
    async def update_order_status(self, order_id: int, status: str, 
                                user_id: int, additional_data: Dict[str, Any] = None):
        """Update order status and notify user"""
        
        # Store in Redis
        if redis_db.enabled:
            order_update = {
                "order_id": order_id,
                "status": status,
                "user_id": user_id,
                "updated_at": datetime.now().isoformat(),
                "additional_data": additional_data or {}
            }
            
            redis_db.client.setex(
                f"live_order:{order_id}",
                86400,  # 24 hours
                json.dumps(order_update, default=str)
            )
        
        # Publish to Redis
        await realtime.publish_order_update(order_id, status, user_id)
        
        # Send to user's WebSocket connections
        message = {
            "type": MessageType.ORDER_STATUS.value,
            "order_id": order_id,
            "status": status,
            "data": additional_data or {}
        }
        
        await self.ws_manager.send_message_to_user(user_id, message)
        
        logger.info(f"Updated order {order_id} status to {status} for user {user_id}")
    
    async def get_live_order_status(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get real-time order status"""
        if not redis_db.enabled:
            return None
        
        cached_data = redis_db.client.get(f"live_order:{order_id}")
        if cached_data:
            return json.loads(cached_data)
        return None

class RedisLiveNotifications:
    """Real-time notifications with Redis"""
    
    def __init__(self, websocket_manager: RedisWebSocketManager):
        self.ws_manager = websocket_manager
    
    async def send_notification(self, user_id: int, notification: Dict[str, Any]):
        """Send real-time notification to user"""
        
        # Add metadata
        notification.update({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "read": False
        })
        
        # Store in Redis for persistence
        if redis_db.enabled:
            # Add to user's notification list
            notification_key = f"user_notifications:{user_id}"
            redis_db.client.lpush(notification_key, json.dumps(notification, default=str))
            redis_db.client.ltrim(notification_key, 0, 99)  # Keep last 100 notifications
            redis_db.client.expire(notification_key, 7 * 86400)  # 7 days
        
        # Publish to Redis
        await realtime.publish_user_notification(user_id, notification)
        
        # Send via WebSocket
        message = {
            "type": MessageType.USER_NOTIFICATION.value,
            "notification": notification
        }
        
        sent_count = await self.ws_manager.send_message_to_user(user_id, message)
        logger.info(f"Sent notification to user {user_id} via {sent_count} connections")
    
    async def get_user_notifications(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's recent notifications"""
        if not redis_db.enabled:
            return []
        
        notification_key = f"user_notifications:{user_id}"
        notifications_data = redis_db.client.lrange(notification_key, 0, limit - 1)
        
        notifications = []
        for data in notifications_data:
            try:
                notifications.append(json.loads(data))
            except json.JSONDecodeError:
                continue
        
        return notifications
    
    async def mark_notification_read(self, user_id: int, notification_id: str):
        """Mark notification as read"""
        if not redis_db.enabled:
            return
        
        # This is a simplified implementation
        # In a full system, you'd update the specific notification
        logger.info(f"Marked notification {notification_id} as read for user {user_id}")

class RedisLivePricing:
    """Real-time price updates with Redis"""
    
    def __init__(self, websocket_manager: RedisWebSocketManager):
        self.ws_manager = websocket_manager
    
    async def update_product_price(self, product_id: int, new_price: float, 
                                 pricing_unit: str = "day"):
        """Update product price and notify subscribers"""
        
        price_update = {
            "product_id": product_id,
            "new_price": new_price,
            "pricing_unit": pricing_unit,
            "updated_at": datetime.now().isoformat()
        }
        
        # Store in Redis
        if redis_db.enabled:
            redis_db.client.setex(
                f"live_price:{product_id}",
                3600,  # 1 hour
                json.dumps(price_update, default=str)
            )
        
        # Broadcast to WebSocket subscribers
        message = {
            "type": MessageType.PRICE_UPDATE.value,
            "data": price_update
        }
        
        channel = self.ws_manager.channels[MessageType.PRICE_UPDATE]
        await self.ws_manager.broadcast_to_channel(channel, message)
        
        logger.info(f"Updated price for product {product_id} to {new_price}")

# Global instances
ws_manager = RedisWebSocketManager() if WEBSOCKET_AVAILABLE else None
live_inventory = RedisLiveInventory(ws_manager) if ws_manager else None
live_orders = RedisLiveOrders(ws_manager) if ws_manager else None
live_notifications = RedisLiveNotifications(ws_manager) if ws_manager else None
live_pricing = RedisLivePricing(ws_manager) if ws_manager else None

# WebSocket endpoint decorator
def websocket_endpoint(path: str):
    """Decorator for WebSocket endpoints with Redis integration"""
    def decorator(func):
        async def wrapper(websocket: WebSocket, *args, **kwargs):
            if not ws_manager:
                await websocket.close(code=1000, reason="WebSocket not available")
                return
            
            connection_id = None
            try:
                # Extract user_id from function signature or token
                user_id = kwargs.get('user_id')
                connection_id = await ws_manager.connect(websocket, user_id)
                
                # Call the decorated function
                await func(websocket, connection_id, *args, **kwargs)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: {connection_id}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                if connection_id:
                    await ws_manager.disconnect(connection_id)
        
        return wrapper
    return decorator

# Export all real-time utilities
__all__ = [
    'ws_manager', 'live_inventory', 'live_orders', 'live_notifications', 'live_pricing',
    'RedisWebSocketManager', 'RedisLiveInventory', 'RedisLiveOrders', 
    'RedisLiveNotifications', 'RedisLivePricing', 'MessageType', 'websocket_endpoint'
]
