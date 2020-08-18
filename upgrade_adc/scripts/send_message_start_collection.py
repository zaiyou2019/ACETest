#!/usr/bin/rnv
import pika
import json
import logging
import argparse
logging.basicConfig()

def get_args():
    # Supports the command-line arguments listed below.
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-q', '--output',
                        required=False, action='store', help='output path to save  json file')
    parser.add_argument('-f', '--file', required=False)
    parser.add_argument('-t', '--type', required=False)
    parser.add_argument('-g', '--group', required=False)
    args = parser.parse_args()
    return args

arguments = get_args()
username = 'guest'
password ='guest'
ipaddress = '127.0.0.1'
port = 5672
if arguments.type == 'adc':
	exchange_name = 'dp_communication_adc'
	queue_name = 'dp_communication_adc.trigger_data_collection'
	routing_key = 'dp_communication_adc.trigger_data_collection'
	bodydata = {'group_name': str(arguments.group), 'start': True}
else:
	exchange_name = 'data-collection-update-management'
	queue_name = 'data-collection-update-management.data-collection-group'
	routing_key = 'data-collection-update-management.data-collection-group'
	bodydata = {'filepath': str(arguments.file), 
	            'feedback': {'mftFile': {'type': 'Script'}}}
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



# --------------------------------------------------------

# print(queue.method.message_count)
