import socket
import threading
import json
import time

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        
        self.lobbies = {}  # {lobby_id: {'host': username, 'players': [username1, username2], 'ready': {username1: False, username2: False}, 'roles': {'username1': 'player1', 'username2': 'player2'}}}
        self.clients = {}  # {client_socket: {'username': username, 'lobby': lobby_id, 'role': 'player1' or 'player2'}}
        self.next_lobby_id = 1
        
        print(f"Server started on {host}:{port}")
        
    def start(self):
        while True:
            client, address = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()
            
    def handle_client(self, client):
        while True:
            try:
                data = client.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                message = json.loads(data)
                command = message.get('command')
                
                if command == 'create_lobby':
                    self.handle_create_lobby(client, message)
                elif command == 'join_lobby':
                    self.handle_join_lobby(client, message)
                elif command == 'ready':
                    self.handle_ready(client, message)
                elif command == 'leave_lobby':
                    self.handle_leave_lobby(client)
                elif command == 'get_lobbies':
                    self.send_lobby_list(client)
                elif command == 'chat':
                    self.handle_chat(client, message)
                elif command == 'game_update':
                    self.handle_game_update(client, message)
                    
            except Exception as e:
                print(f"Error handling client: {e}")
                break
                
        self.handle_disconnect(client)
        
    def handle_create_lobby(self, client, message):
        username = message.get('username')
        lobby_id = str(self.next_lobby_id)
        self.next_lobby_id += 1
        
        self.lobbies[lobby_id] = {
            'host': username,
            'players': [username],
            'ready': {username: False},
            'roles': {username: 'player1'}
        }
        
        self.clients[client] = {
            'username': username,
            'lobby': lobby_id,
            'role': 'player1'
        }
        
        response = {
            'type': 'lobby_created',
            'lobby_id': lobby_id,
            'status': 'success',
            'role': 'player1'
        }
        client.send(json.dumps(response).encode('utf-8'))
        
    def handle_join_lobby(self, client, message):
        lobby_id = message.get('lobby_id')
        username = message.get('username')
        
        if lobby_id in self.lobbies and len(self.lobbies[lobby_id]['players']) < 2:
            self.lobbies[lobby_id]['players'].append(username)
            self.lobbies[lobby_id]['ready'][username] = False
            self.lobbies[lobby_id]['roles'][username] = 'player2'
            
            self.clients[client] = {
                'username': username,
                'lobby': lobby_id,
                'role': 'player2'
            }
            
            # Notify all players in the lobby
            self.broadcast_to_lobby(lobby_id, {
                'type': 'player_joined',
                'username': username,
                'players': self.lobbies[lobby_id]['players'],
                'roles': self.lobbies[lobby_id]['roles'],
                'ready': self.lobbies[lobby_id]['ready']
            })
        else:
            response = {
                'type': 'join_failed',
                'message': 'Lobby is full or does not exist'
            }
            client.send(json.dumps(response).encode('utf-8'))
            
    def handle_ready(self, client, message):
        if client in self.clients:
            lobby_id = self.clients[client]['lobby']
            username = self.clients[client]['username']
            
            if lobby_id in self.lobbies:
                # Toggle ready status for the specific player
                self.lobbies[lobby_id]['ready'][username] = not self.lobbies[lobby_id]['ready'][username]
                
                # Check if all players are ready
                if all(self.lobbies[lobby_id]['ready'].values()):
                    self.broadcast_to_lobby(lobby_id, {
                        'type': 'game_start',
                        'players': self.lobbies[lobby_id]['players'],
                        'roles': self.lobbies[lobby_id]['roles'],
                        'ready': self.lobbies[lobby_id]['ready']
                    })
                else:
                    # Send ready update to all players
                    self.broadcast_to_lobby(lobby_id, {
                        'type': 'ready_update',
                        'players': self.lobbies[lobby_id]['players'],
                        'ready': self.lobbies[lobby_id]['ready'],
                        'roles': self.lobbies[lobby_id]['roles']
                    })
                    
    def handle_leave_lobby(self, client):
        if client in self.clients:
            lobby_id = self.clients[client]['lobby']
            username = self.clients[client]['username']
            
            if lobby_id in self.lobbies:
                self.lobbies[lobby_id]['players'].remove(username)
                del self.lobbies[lobby_id]['ready'][username]
                del self.lobbies[lobby_id]['roles'][username]
                
                if not self.lobbies[lobby_id]['players']:
                    del self.lobbies[lobby_id]
                else:
                    self.broadcast_to_lobby(lobby_id, {
                        'type': 'player_left',
                        'username': username,
                        'players': self.lobbies[lobby_id]['players'],
                        'roles': self.lobbies[lobby_id]['roles'],
                        'ready': self.lobbies[lobby_id]['ready']
                    })
                    
            del self.clients[client]
            
    def handle_disconnect(self, client):
        self.handle_leave_lobby(client)
        client.close()
        
    def broadcast_to_lobby(self, lobby_id, message):
        for client, data in self.clients.items():
            if data['lobby'] == lobby_id:
                try:
                    client.send(json.dumps(message).encode('utf-8'))
                except:
                    pass
                    
    def send_lobby_list(self, client):
        lobby_list = {
            'type': 'lobby_list',
            'lobbies': [
                {
                    'id': lobby_id,
                    'host': data['host'],
                    'players': len(data['players']),
                    'max_players': 2
                }
                for lobby_id, data in self.lobbies.items()
            ]
        }
        client.send(json.dumps(lobby_list).encode('utf-8'))

    def handle_chat(self, client, message):
        if client in self.clients:
            lobby_id = self.clients[client]['lobby']
            username = self.clients[client]['username']
            chat_message = message.get('message')
            
            if lobby_id in self.lobbies:
                # Broadcast the chat message to all players in the lobby
                self.broadcast_to_lobby(lobby_id, {
                    'type': 'chat_message',
                    'username': username,
                    'message': chat_message
                })

    def handle_game_update(self, client, message):
        if client not in self.clients:
            return
            
        lobby_id = self.clients[client]['lobby']
        if lobby_id not in self.lobbies:
            return
            
        # Get the sender's username
        sender = self.clients[client]['username']
        
        # Create update message for other player
        update_message = {
            'type': 'game_update',
            'sender': sender,
            'board': message.get('board'),
            'score': message.get('score'),
            'combo': message.get('combo'),
            'current_piece': message.get('current_piece'),
            'next_piece': message.get('next_piece'),
            'hold_piece': message.get('hold_piece'),
            'piece_pos': message.get('piece_pos')
        }
        
        # Broadcast to other player in the lobby
        for other_client, client_data in self.clients.items():
            if client_data['lobby'] == lobby_id and client_data['username'] != sender:
                try:
                    other_client.send(json.dumps(update_message).encode('utf-8'))
                except:
                    pass

if __name__ == "__main__":
    server = GameServer()
    server.start() 
