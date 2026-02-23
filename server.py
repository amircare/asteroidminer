import socket
import threading
import json
import time

class GameServer:
    def __init__(self, host="0.0.0.0", port=5555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind((self.host, self.port))
        self.players = {}  # {addr: {name, x, y, rotation, color_index, last_seen}}
        self.running = True
        self.timeout = 5.0  # Remove players after 5 seconds of no updates

    def cleanup_players(self):
        """Remove disconnected players"""
        current_time = time.time()
        to_remove = []
        for addr, data in self.players.items():
            if current_time - data.get("last_seen", 0) > self.timeout:
                to_remove.append(addr)
        for addr in to_remove:
            print(f"Player {self.players[addr].get('name', 'Unknown')} timed out")
            del self.players[addr]

    def broadcast_state(self):
        """Send all player states to all players"""
        if not self.players:
            return
        
        # Build player list (excluding sender for each recipient)
        all_players = []
        for addr, data in self.players.items():
            all_players.append({
                "id": f"{addr[0]}:{addr[1]}",
                "name": data.get("name", "Player"),
                "x": data.get("x", 0),
                "y": data.get("y", 0),
                "rotation": data.get("rotation", 0),
                "color_index": data.get("color_index", 0),
            })
        
        state_msg = json.dumps({"type": "state", "players": all_players}).encode()
        
        for addr in self.players.keys():
            try:
                self.server.sendto(state_msg, addr)
            except:
                pass

    def handle_message(self, data, addr):
        try:
            msg = json.loads(data.decode())
            msg_type = msg.get("type")

            if msg_type == "join":
                self.players[addr] = {
                    "name": msg.get("name", "Player"),
                    "x": msg.get("x", 0),
                    "y": msg.get("y", 0),
                    "rotation": msg.get("rotation", 0),
                    "color_index": msg.get("color_index", 0),
                    "last_seen": time.time()
                }
                print(f"Player {msg.get('name')} joined from {addr}")
                # Send confirmation
                response = json.dumps({"type": "joined", "id": f"{addr[0]}:{addr[1]}"}).encode()
                self.server.sendto(response, addr)

            elif msg_type == "update":
                if addr in self.players:
                    self.players[addr].update({
                        "x": msg.get("x", self.players[addr]["x"]),
                        "y": msg.get("y", self.players[addr]["y"]),
                        "rotation": msg.get("rotation", self.players[addr]["rotation"]),
                        "color_index": msg.get("color_index", self.players[addr]["color_index"]),
                        "last_seen": time.time()
                    })

            elif msg_type == "leave":
                if addr in self.players:
                    print(f"Player {self.players[addr].get('name')} left")
                    del self.players[addr]

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error handling message: {e}")

    def run(self):
        print(f"Server started on {self.host}:{self.port}")
        self.server.setblocking(False)
        
        last_broadcast = time.time()
        last_cleanup = time.time()
        broadcast_interval = 0.05  # 20 times per second
        cleanup_interval = 1.0

        while self.running:
            try:
                data, addr = self.server.recvfrom(4096)
                self.handle_message(data, addr)
            except BlockingIOError:
                pass
            except Exception as e:
                print(f"Error receiving: {e}")

            current_time = time.time()
            
            # Broadcast state periodically
            if current_time - last_broadcast >= broadcast_interval:
                self.broadcast_state()
                last_broadcast = current_time

            # Cleanup disconnected players
            if current_time - last_cleanup >= cleanup_interval:
                self.cleanup_players()
                last_cleanup = current_time

            time.sleep(0.01)  # Prevent CPU spinning

    def stop(self):
        self.running = False
        self.server.close()

if __name__ == "__main__":
    import sys
    port = 5555
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    server = GameServer(port=port)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
