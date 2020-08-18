import pika
import json
import logging
logging.basicConfig()

 

username = 'guest'
password ='guest'
ipaddress = '127.0.0.1'
port = 5672
#exchange_name = 'data-collection-update-management'
#queue_name = 'data-collection-update-management.data-collection-group'
#routing_key = 'data-collection-update-management.data-collection-group'
exchange_name = 'data-collection-update-management'
queue_name = 'data-collection-update-management.data-collection-group'
routing_key = 'data-collection-update-management.data-collection-group'
#bodydata = {'filepath': '/mystic/telemetry/DCManager/tmp/adc_patches/DCManager_v_1_3_201.tgz'}
bodydata = {"feedback": {"mftFile": {"type": "Script"}},"filepath" : "/mystic/telemetry/DCManager/tmp/adc_patches/DCManager_v_1_3_201.tgz"}

 

bodyjson = json.dumps(bodydata)
credentials = pika.PlainCredentials(username, password)
connection = pika.BlockingConnection(pika.ConnectionParameters(ipaddress, port, '/', credentials))
channel = connection.channel()
# # # declare the queue
#queue = channel.queue_declare(queue=queue_name, durable=True, arguments={'x-message-ttl': int(2*24*60*60*1000)})
queue1 = channel.queue_declare(queue=queue_name, durable=True)
# # # declare the exchange
exchange = channel.exchange_declare(exchange=exchange_name, durable=True, exchange_type='topic')
# # # bind the queue and exchange
channel.queue_bind(exchange=exchange_name, routing_key=routing_key, queue=queue_name)
channel.basic_publish(exchange=exchange_name, routing_key=routing_key, body=bodyjson)
print("Send a Message to RabbitMQ!")