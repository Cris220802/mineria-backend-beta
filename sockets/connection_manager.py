# En un nuevo archivo, por ejemplo, connection_manager.py o en tu archivo principal de la app
from typing import Dict, List, Any
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        # Almacena las conexiones activas, mapeando ensaye_id (como string) a una lista de WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, ensaye_id: str, websocket: WebSocket):
        await websocket.accept()
        if ensaye_id not in self.active_connections:
            self.active_connections[ensaye_id] = []
        self.active_connections[ensaye_id].append(websocket)
        print(f"WebSocket connected for ensaye_id: {ensaye_id}, total connections: {len(self.active_connections[ensaye_id])}")


    def disconnect(self, ensaye_id: str, websocket: WebSocket):
        if ensaye_id in self.active_connections:
            try:
                self.active_connections[ensaye_id].remove(websocket)
                if not self.active_connections[ensaye_id]: # Si no quedan conexiones para este ensaye_id
                    del self.active_connections[ensaye_id]
                print(f"WebSocket disconnected for ensaye_id: {ensaye_id}")
            except ValueError:
                print(f"WebSocket not found for ensaye_id: {ensaye_id} during disconnect.")
                pass # El websocket ya no estaba en la lista


    async def send_status_update(self, ensaye_id: str, status_event: str, message_detail: str, success: bool = True, data: Any = None):
        ensaye_id_str = str(ensaye_id) # Asegurar que sea string
        if ensaye_id_str in self.active_connections:
            message_payload = {
                "event": status_event,
                "status": "success" if success else "failure",
                "ensaye_id": ensaye_id_str,
                "details": message_detail,
            }
            if data:
                message_payload["data"] = data
            
            print(f"Broadcasting to ensaye_id {ensaye_id_str}: {message_payload}")
            
            # Iterar sobre una copia de la lista por si hay desconexiones durante el envío
            connections_to_send = list(self.active_connections[ensaye_id_str])
            for connection in connections_to_send:
                try:
                    await connection.send_text(json.dumps(message_payload))
                except Exception as e:
                    print(f"Error sending message to a websocket for ensaye_id {ensaye_id_str}: {e}")
                    # Podrías manejar la desconexión aquí si el error indica que el socket está cerrado
                    # self.disconnect(ensaye_id_str, connection) # Cuidado con modificar la lista mientras iteras sin copia

# Instancia global del gestor
manager = ConnectionManager()