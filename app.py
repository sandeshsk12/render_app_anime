import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()
clients = set()

@app.on_event("startup")
async def startup_event():
    # Start background subscription task when the app starts
    asyncio.create_task(subscribe())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            # Keep connection alive. Optionally, you can wait for client messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def get():
    html_content = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Live Amount Claimed</title>
      </head>
      <body>
        <h1>Live Amount Claimed</h1>
        <div id="amount">Waiting for data...</div>
        <script>
          const ws = new WebSocket("wss://" + location.host + "/ws");
          ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById("amount").innerText = data.amount_claimed;
          }
          ws.onopen = () => console.log("WebSocket connection established.");
          ws.onerror = (err) => console.error("WebSocket error:", err);
        </script>
      </body>
    </html>
    """
    return html_content

async def subscribe():
    # Replace with your actual Infura API key
    uri = "wss://arbitrum-mainnet.infura.io/ws/v3/1707a57cddd6415e8f80ce787b35e05f"
    subscription_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_subscribe",
        "params": ["newHeads"]
    }
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(subscription_message))
        while True:
            try:
                response = await ws.recv()
                response_dict = json.loads(response)
                if 'params' in response_dict and 'result' in response_dict['params']:
                    amount_claimed_hex = response_dict['params']['result']['number']
                    amount_claimed = int(amount_claimed_hex, 16)
                    print(f"Amount claimed: {amount_claimed}")
                    
                    data = {"amount_claimed": amount_claimed}
                    for client in clients.copy():
                        try:
                            await client.send_json(data)
                        except Exception as e:
                            print("Error sending to client:", e)
                            clients.remove(client)
                else:
                    print("Unexpected response:", response_dict)
            except Exception as e:
                print("Subscription error:", e)
                await asyncio.sleep(5)  # Wait a bit before retrying
