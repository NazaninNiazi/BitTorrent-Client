import socket
import struct
import threading
import time
from typing import Dict, List, Optional, Callable
import hashlib

class PeerConnection:
    
    def __init__(self, peer_ip: str, peer_port: int, info_hash: bytes, 
                 peer_id: bytes, piece_manager, on_piece_received: Callable = None):
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.piece_manager = piece_manager
        self.on_piece_received = on_piece_received
        
        self.socket = None
        self.connected = False
        self.handshaked = False
        self.choked = True
        self.interested = False
        self.peer_choked = True
        self.peer_interested = False
        self.peer_bitfield = None
        
        self.pending_requests = {}
        self.running = False
        self.max_pending_requests = 10
        
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.peer_ip, self.peer_port))
            self.connected = True
            print(f"[+] TCP Connected to {self.peer_ip}:{self.peer_port}")
            
            # Send handshake
            handshake = self._build_handshake()
            self.socket.send(handshake)
            print(f"[>] Sent Handshake to {self.peer_ip}:{self.peer_port}")
            
            # Receive handshake response
            response = self.socket.recv(68)
            if len(response) != 68:
                return False
            
            # Verify handshake
            if response[28:48] != self.info_hash:
                return False
            
            self.handshaked = True
            self.socket.settimeout(30)
            print(f"[<] Received Handshake OK from {self.peer_ip}:{self.peer_port}")
            
            # Start message handling thread
            self.running = True
            threading.Thread(target=self._message_loop, daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"Connection error to {self.peer_ip}:{self.peer_port}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        self.running = False
        self.connected = False
        self.handshaked = False
        if self.connected:
            print(f"[-] Disconnected from {self.peer_ip}:{self.peer_port}")
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def _build_handshake(self) -> bytes:
        protocol = b"BitTorrent protocol"
        reserved = b'\x00' * 8
        return struct.pack('>B19s8s20s20s', 
                          len(protocol), protocol, reserved, 
                          self.info_hash, self.peer_id)
    
    def _message_loop(self):
        while self.running and self.connected:
            try:
                # Read message length
                length_data = self._recv_exact(4)
                if not length_data:
                    break
                
                length = struct.unpack('>I', length_data)[0]
                
                if length == 0:
                    # Keep-alive message
                    continue
                
                # Read message
                message_data = self._recv_exact(length)
                if not message_data:
                    break
                
                self._handle_message(message_data)
                
            except Exception as e:
                print(f"Message loop error: {e}")
                break
        
        self.disconnect()
    
    def _recv_exact(self, length: int) -> Optional[bytes]:
        data = b''
        while len(data) < length:
            try:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data
    
    def _handle_message(self, message: bytes):
        if len(message) == 0:
            return
        
        message_id = message[0]
        payload = message[1:]
        
        if message_id == 0:  # choke
            self.choked = True
            print(f"[<] Peer choked us")
        elif message_id == 1:  # unchoke
            self.choked = False
            print(f"[<] Peer unchoked us")
            self._request_pieces()
        elif message_id == 2:  # interested
            self.peer_interested = True
        elif message_id == 3:  # not interested
            self.peer_interested = False
        elif message_id == 4:  # have
            piece_index = struct.unpack('>I', payload)[0]
            print(f"[<] Peer has piece {piece_index}")
            if self.peer_bitfield is None:
                self.peer_bitfield = [False] * self.piece_manager.num_pieces
            if piece_index < len(self.peer_bitfield):
                self.peer_bitfield[piece_index] = True
            if not self.interested:
                self._send_interested()
            if not self.choked:
                self._request_pieces()
        elif message_id == 5:  # bitfield
            self.peer_bitfield = self._parse_bitfield(payload)
            self._send_interested()
            if not self.choked:
                self._request_pieces()
        elif message_id == 6:  # request
            # Handle piece request from peer
            self._handle_request(payload)
        elif message_id == 7:  # piece
            self._handle_piece(payload)
        elif message_id == 8:  # cancel
            pass  # Handle cancel if needed
    
    def _parse_bitfield(self, bitfield_data: bytes) -> List[bool]:
        bitfield = []
        for byte in bitfield_data:
            for i in range(8):
                bitfield.append(bool(byte & (1 << (7 - i))))
        return bitfield
    
    def _send_interested(self):
        if not self.interested:
            self.interested = True
            message = struct.pack('>IB', 1, 2)
            try:
                self.socket.send(message)
                print(f"[>] Sent interested to {self.peer_ip}:{self.peer_port}")
            except:
                pass
    
    def _request_pieces(self):
        if self.choked or not self.peer_bitfield:
            return
        
        requested_count = 0
        max_requests = 5  # Request up to 5 pieces at once
        
        # Find pieces we need that peer has
        missing_pieces = self.piece_manager.get_missing_pieces()
        
        for piece_index in missing_pieces:
            if requested_count >= max_requests:
                break
                
            if (piece_index < len(self.peer_bitfield) and 
                self.peer_bitfield[piece_index] and 
                not self.piece_manager.is_piece_complete(piece_index)):
                
                # Check if we're already requesting this piece
                piece_already_requested = any(
                    req_piece == piece_index for req_piece, _ in self.pending_requests.keys()
                )
                
                if not piece_already_requested and len(self.pending_requests) < self.max_pending_requests:
                    self._request_piece(piece_index)
                    requested_count += 1
                    print(f"[>] Requesting piece {piece_index} from {self.peer_ip}:{self.peer_port}")
    
    def _request_piece(self, piece_index: int):
        piece_length = self.piece_manager.get_piece_length(piece_index)
        block_size = 16384  # 16KB blocks
        
        for offset in range(0, piece_length, block_size):
            length = min(block_size, piece_length - offset)
            
            request_msg = struct.pack('>IBIII', 13, 6, piece_index, offset, length)
            try:
                self.socket.send(request_msg)
                self.pending_requests[(piece_index, offset)] = length
            except:
                break
    
    def _handle_piece(self, payload: bytes):
        if len(payload) < 8:
            return
        
        piece_index, offset = struct.unpack('>II', payload[:8])
        block_data = payload[8:]
        
        print(f"[<] Received block: piece {piece_index}, offset {offset}, size {len(block_data)}")
        
        # Remove from pending requests
        if (piece_index, offset) in self.pending_requests:
            del self.pending_requests[(piece_index, offset)]
        
        # Store block and check if piece is complete
        piece_completed = self.piece_manager.store_block(piece_index, offset, block_data)
        
        if piece_completed:
            if self.on_piece_received:
                self.on_piece_received(piece_index)
            print(f"[✓] Completed piece {piece_index}")
        
        self._request_pieces()

    def _handle_request(self, payload: bytes):
        if len(payload) != 12:
            return
        
        piece_index, offset, length = struct.unpack('>III', payload)
        
        # Check if we have this piece
        if self.piece_manager.is_piece_complete(piece_index):
            block_data = self.piece_manager.get_block(piece_index, offset, length)
            if block_data:
                # Send piece
                piece_msg = struct.pack('>IBII', 9 + len(block_data), 7, piece_index, offset) + block_data
                try:
                    self.socket.send(piece_msg)
                except:
                    pass
