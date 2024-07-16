import redis
import json, time
from urllib.parse import urlparse
import bittensor as bt

class RedisClient():
    """ A client class to interact with Redis, allowing for publishing, reading,
    and managing messages in streams. This is useful for systems that require message
    queuing, processing, and real-time data handling."""
    def __init__(self, host=None, port=None, url=None, db=0):
        """
        Initializes the Redis client with given host, port, and database.
        If a URL is provided, it overrides host and port settings.
        """
        if url:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            port = parsed_url.port
            
        self.client = redis.Redis(host=host, port=port, db=db)
        self.reward_stream_name = "synapse_data"
        self.base_synapse_stream_name = "base_synapse"
        self.max_queue_size = 200
        self.count_success = {}

    def publish_to_stream(self, stream_name, message):
        message_id = self.client.xadd(stream_name, message)
        bt.logging.info(f"Published {stream_name} message ID: {message_id}")
        return message_id

    def read_from_stream(self, stream_name, count, block):
        messages = self.client.xread({stream_name: '0-0'}, count=count, block=block)  # read $count messages, block for $block miliseconds if no messages
        return messages
    
    def remove_from_stream(self, stream_name, message_id):
        self.client.xdel(stream_name, message_id)
        bt.logging.info(f"Removed {stream_name} message ID: {message_id}")

    def decode_message_stream(self, message_data):
        output = {}
        for key, value in message_data.items():
            output[key.decode('utf-8')] = value.decode('utf-8')
        return output
    
    def get_stream_info(self, stream_name, is_clear = False):
        bt.logging.info(f"Num success messages: {self.count_success}")
        count = self.client.xlen(stream_name)
        bt.logging.info(f"Number of messages remain in {stream_name} stream: {count}.")
        if is_clear:
            self.client.xtrim(stream_name, maxlen=0)
            bt.logging.info(f"Clear stream {stream_name} done !")
        elif self.max_queue_size:
            self.client.xtrim(stream_name, maxlen=self.max_queue_size)
            
        self.count_success = {}

    def update_meta_success(self, stream_name, meta):
        """Updates the count_success dictionary with metadata from successfully processed messages."""
        meta_count_success = meta["count_success"]
        if stream_name not in self.count_success:
            self.count_success[stream_name] = {}
        for key in meta_count_success:
            if key not in self.count_success[stream_name]:
                self.count_success[stream_name][key] = 0
            self.count_success[stream_name][key] += meta_count_success[key]

    async def process_message_from_stream_async(self, stream_name, process_callback, count=10, block=5000, always_ack = False, decode = True, retries = 10):
        """
        Asynchronously processes messages from the specified Redis stream using a callback function. 
        Handles message decoding, acknowledgment
        """
        while True:
            messages = self.read_from_stream(stream_name, count, block)

            if not messages:
                bt.logging.info("No new messages. Waiting for more...")
                continue

            all_messages = []
            for stream, message_list in messages:
                for message_id, message_data in message_list:
                    if decode:
                        message_data = self.decode_message_stream(message_data)
                    
                    all_messages.append({
                        "content": message_data,
                        "id": message_id.decode('utf-8')
                    })
                    if always_ack:
                        self.remove_from_stream(stream_name, message_id)
            
            try:
                success_message_ids, error_message_ids, meta  = await process_callback(all_messages)
                if len(success_message_ids) > 0:
                    self.update_meta_success(stream_name, meta)
                    bt.logging.info(f"Count success:  {self.count_success}")
                    if not  always_ack:
                        for message_id in success_message_ids:
                            self.remove_from_stream(stream_name, message_id)
            except Exception as ex:
                bt.logging.error(f"Exception process message in stream: {str(ex)}")