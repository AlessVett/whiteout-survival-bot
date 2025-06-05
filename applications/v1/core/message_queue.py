import asyncio
import json
from typing import Callable, Dict, Any
import aio_pika
from aio_pika import ExchangeType
from structlog import get_logger

logger = get_logger()


class MessageBroker:
    def __init__(self, rabbitmq_url: str):
        self.url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        
    async def connect(self):
        """Connect to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        logger.info("Connected to RabbitMQ")
        
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        logger.info("Disconnected from RabbitMQ")
        
    async def declare_exchange(
        self, 
        name: str, 
        exchange_type: ExchangeType = ExchangeType.TOPIC,
        durable: bool = True
    ):
        """Declare an exchange"""
        exchange = await self.channel.declare_exchange(
            name, 
            exchange_type,
            durable=durable
        )
        self.exchanges[name] = exchange
        return exchange
        
    async def declare_queue(
        self, 
        name: str, 
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ):
        """Declare a queue"""
        queue = await self.channel.declare_queue(
            name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete
        )
        self.queues[name] = queue
        return queue
        
    async def bind_queue(
        self, 
        queue_name: str, 
        exchange_name: str,
        routing_key: str
    ):
        """Bind a queue to an exchange"""
        queue = self.queues.get(queue_name)
        exchange = self.exchanges.get(exchange_name)
        
        if not queue or not exchange:
            raise ValueError("Queue or exchange not found")
            
        await queue.bind(exchange, routing_key)
        logger.info(f"Bound queue '{queue_name}' to exchange '{exchange_name}' with key '{routing_key}'")
        
    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True
    ):
        """Publish a message"""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            raise ValueError(f"Exchange '{exchange_name}' not found")
            
        message_body = json.dumps(message).encode()
        
        await exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT
            ),
            routing_key=routing_key
        )
        
        logger.debug(f"Published message to {exchange_name}/{routing_key}")
        
    async def consume(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ):
        """Consume messages from a queue"""
        queue = self.queues.get(queue_name)
        if not queue:
            raise ValueError(f"Queue '{queue_name}' not found")
            
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process(ignore_processed=True):
                try:
                    body = json.loads(message.body.decode())
                    await callback(body, message)
                    
                    if not auto_ack:
                        await message.ack()
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    if not auto_ack:
                        await message.nack(requeue=True)
                        
        await queue.consume(process_message, no_ack=auto_ack)
        logger.info(f"Started consuming from queue '{queue_name}'")


class EventBus:
    """High-level event bus built on top of MessageBroker"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.handlers: Dict[str, List[Callable]] = {}
        
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event"""
        await self.broker.publish(
            "events",
            event_type,
            {
                "type": event_type,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
    async def on(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
            
        self.handlers[event_type].append(handler)
        
    async def start(self):
        """Start listening for events"""
        await self.broker.declare_exchange("events", ExchangeType.TOPIC)
        
        for event_type in self.handlers:
            queue_name = f"event_{event_type}_{id(self)}"
            queue = await self.broker.declare_queue(queue_name, auto_delete=True)
            await self.broker.bind_queue(queue_name, "events", event_type)
            
            async def handle_event(body: Dict, message: aio_pika.IncomingMessage):
                for handler in self.handlers.get(body["type"], []):
                    try:
                        await handler(body["data"])
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
                        
            await self.broker.consume(queue_name, handle_event)