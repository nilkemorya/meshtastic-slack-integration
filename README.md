This script acts as a **bidirectional bridge** between a Slack channel and a Meshtastic mesh network via MQTT. It allows users on Slack to send messages to the mesh and allows mesh users to see their messages appear in Slack.

---

# Meshtastic ↔ Slack Bridge

A Python-based gateway that connects a Meshtastic mesh network to a Slack workspace. It uses MQTT to interface with the mesh and Slack's Socket Mode for real-time communication.

## 🚀 Features

* **Bidirectional Messaging:** Post from Slack to the Mesh (Broadcast) and from the Mesh to a Slack channel.
* **Encryption Support:** Handles AES-CTR encryption for Meshtastic channels using your provided PSK.
* **User Mapping:** Supports a manual lookup table to translate Meshtastic Node IDs into friendly names.
* **Socket Mode:** Uses Slack's Socket Mode, meaning you don't need to expose a public HTTP endpoint (no ngrok required).

---

## 🛠️ Prerequisites

* **Python 3.11+**
* **Meshtastic Node:** Configured with MQTT enabled.
* **MQTT Broker:** A reachable broker (e.g., `mqtt.meshtastic.org` or a local Mosquitto instance).
* **Slack App:** A Slack app created in your workspace with `chat:write` and `connections:write` permissions.

---

## 📦 Installation

1. **Clone this repository** (or save the script).
2. **Create a python venv** 
```bash
python -m venv Meshtastic
```
2. **Install dependencies:**
```bash
pip install paho-mqtt cryptography meshtastic slack_bolt slack_sdk meshtastic-mqtt-json

```
2b. **Install using requirements.txt:**
```bash
pip install -r requirements.txt

```


---

## ⚙️ Configuration

You must edit the following variables in the script:

### Slack Settings

* `slack_token`: Your Bot User OAuth Token (`xoxb-...`).
* `app_token`: Your Slack App-level Token (`xapp-...`).
* `channel_id`: The ID of the Slack channel where the bot should post.

### Meshtastic/MQTT Settings

* `BROKER`: Your MQTT server address.
* `KEY`: Your Meshtastic Channel PSK (Base64).
* `CHANNEL`: Your Meshtastic channel name (e.g., "LongFast").
* `SENDER_NODE_ID`: Your physical or virtual node ID.
* `NODE_NAME`: The name you want the bot to use when posting to the mesh.
* `BASE_MESH_PATH`: The MQTT topic root (e.g., `msh/US/2/e/`).

---

## 📖 How It Works

1. **MQTT Thread:** Listens for `TEXT_MESSAGE_APP` packets on the specified MQTT topic. When a message arrives, it decrypts the payload and posts it to Slack.
2. **Slack Thread:** Uses `SocketModeHandler` to listen for any message in the Slack channel. When a user types, the bot captures the text and injects it into the MQTT broker as an encrypted Meshtastic packet.
3. **Deduplication:** The `already_posted` list prevents the bot from echoing its own messages back and forth in an infinite loop.

---

## ⚠️ Important Notes

* **Security:** Never commit your tokens or PSK to a public repository. Use environment variables for production.
* **Protobufs:** This script relies on `meshtastic.protobuf`. Ensure your library versions match your node's firmware version to avoid decoding errors.

---