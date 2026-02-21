# python 3.11

import base64
import logging
import random
import threading
from datetime import datetime

import paho.mqtt.client as mqtt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import BROADCAST_NUM
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2
from meshtastic_mqtt_json import MeshtasticMQTT
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

LOGGER = logging.getLogger(__name__)

SLACK_TOKEN = '<BOT TOKEN HERE>'
SIGNING_SECRET = '<SIGNING SECRET HERE>'
BROKER = '<MQTT SERVER>'
KEY = '<CHANNEL PSK>'
CHANNEL = '<YOUR CHANNEL NAME>'
CHANNEL_ID = '<YOUR CHANNEL ID>'
APP_TOKEN = 'APP TOKEN HERE>'
# Meshtatsic Default MQTT
BASE_MESH_PATH = 'msh/US/2/e/'
# start with a pseudorandom message ID to prevent copies
global_message_id = random.getrandbits(32)
SENDER_NODE_ID = 123456  # <REPLACE WITH YOUR NODE ID>
NODE_NAME = '<NODE ID TO POST AS>'

already_posted = []
# Username lookup for posting to slack. 
# TODO: Figure out how to do this with id packets
user_names = {
}

slack_client = WebClient(token=SLACK_TOKEN)
app = App(token=SLACK_TOKEN, SIGNING_SECRET=SIGNING_SECRET)


def on_connect(client, userdata, flags, rc, properties):
    '''Simple feedback function to indicate you connected to MQTT server'''
    if rc == 0:
        print("Connected successfully to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")


def xor_hash(data: bytes) -> int:
    """Return XOR hash of all bytes in the provided string."""

    result = 0
    for char in data:
        result ^= char
    return result


def generate_hash(name: str, key: str) -> int:
    """Generates a has of the key"""

    replaced_key = key.replace('-', '+').replace('_', '/')
    key_bytes = base64.b64decode(replaced_key.encode('utf-8'))
    h_name = xor_hash(bytes(name, 'utf-8'))
    h_key = xor_hash(key_bytes)
    result: int = h_name ^ h_key
    return result


mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2, client_id="", clean_session=True,
    userdata=None)
mqtt_client.on_connect = on_connect
# Default meshtastic username and password, replace as needed
mqtt_client.username_pw_set("meshdev", "large4cats")
# Default packets
mqtt_client.connect(BROKER, 1883, 60)
mqtt_client.loop_start()


def encrypt_message(channel, key, mesh_packet, encoded_message):
    '''Modified from https://github.com/pdxlocations/connect'''
    mesh_packet.channel = generate_hash(channel, key)
    key_bytes = base64.b64decode(key.encode('ascii'))

    # print (f"id = {mesh_packet.id}")
    nonce_packet_id = mesh_packet.id.to_bytes(8, "little")
    nonce_from_node = SENDER_NODE_ID.to_bytes(8, "little")
    # Put both parts into a single byte array.
    nonce = nonce_packet_id + nonce_from_node

    cipher = Cipher(
        algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_bytes = encryptor.update(
        encoded_message.SerializeToString()) + encryptor.finalize()

    return encrypted_bytes


def generate_mesh_packet(destination_id, encoded_message):
    """Send a packet out over the mesh. Modified from
        https://github.com/pdxlocations/connect"""

    global global_message_id
    mesh_packet = mesh_pb2.MeshPacket()

    # Use the global message ID and increment it for the next call
    mesh_packet.id = global_message_id
    global_message_id += 1

    setattr(mesh_packet, "from", SENDER_NODE_ID)
    mesh_packet.to = destination_id
    mesh_packet.want_ack = False
    mesh_packet.channel = generate_hash(CHANNEL, KEY)
    mesh_packet.hop_limit = 7
    mesh_packet.hop_start = 1

    mesh_packet.encrypted = encrypt_message(
            CHANNEL, KEY, mesh_packet, encoded_message)

    service_envelope = mqtt_pb2.ServiceEnvelope()
    service_envelope.packet.CopyFrom(mesh_packet)
    service_envelope.channel_id = CHANNEL
    service_envelope.gateway_id = NODE_NAME
    # print (service_envelope)

    payload = service_envelope.SerializeToString()
    # print(payload)
    mqtt_client.publish(f'msh/US/bayarea/2/e/MeshSnark/{NODE_NAME}', payload)


def publish_message(destination_id, text):
    message_text = text
    if message_text:
        encoded_message = mesh_pb2.Data()
        encoded_message.portnum = portnums_pb2.TEXT_MESSAGE_APP
        encoded_message.payload = message_text.encode("utf-8")
        encoded_message.bitfield = 1
        generate_mesh_packet(destination_id, encoded_message)


def on_text_message(json_data):
    '''Posts your MQTT messages to a specified slack channel if not already 
    posted'''
    message_id = json_data['id']
    message = json_data['decoded']['payload']
    fromid = json_data['from']
    if fromid in user_names.keys():
        name = user_names[fromid]
    else:
        name = fromid
    if message_id not in already_posted and fromid != 3654430706:
        already_posted.append(message_id)
        slack_message = f'from: {name}, Message: {message}'
        slack_client.chat_postMessage(channel=CHANNEL_ID, text=slack_message)
    print(f'{datetime.now()}: {json_data}')


def on_position(json_data):
    # Just debugging position info at this time
    print(f'Received position update: {json_data["decoded"]["payload"]}')


def meshtastic_go():
    # Start up meshtastic monitor thread
    client = MeshtasticMQTT()
    client.register_callback('TEXT_MESSAGE_APP', on_text_message)
    client.register_callback('POSITION_APP', on_position)

    client.connect(
        broker=BROKER,
        port=1883,
        root=BASE_MESH_PATH,
        channel=CHANNEL,
        username='meshdev',
        password='large4cats',
        key=KEY)


@app.message()
def handle_slack(message, say):
    '''Message to handle slack messages and post to mesh'''
    payload = message['text']
    username = app.client.users_info(
        user=message['user'])["user"]["profile"]["display_name"]
    LOGGER.debug(f'{username} posted {payload}')
    publish_message(BROADCAST_NUM, f'{username} posted {payload}')


def slack_thread():
    SocketModeHandler(app, APP_TOKEN).start()


if __name__ == '__main__':
    t1 = threading.Thread(target=meshtastic_go)
    t2 = threading.Thread(target=slack_thread)
    t1.start()
    t2.start()

    t1.join()
    t2.join()
