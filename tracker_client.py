import socket
import struct
import urllib.parse
import urllib.request
import random
from typing import List, Dict, Any, Tuple
import time

class TrackerClient:
  
    def __init__(self, peer_id: bytes, port: int = 6881):
        self.peer_id = peer_id
        self.port = port
        
    def scrape_http_tracker(self, announce_url: str, info_hash: bytes, 
                           uploaded: int = 0, downloaded: int = 0, 
                           left: int = 0, event: str = 'started') -> List[Dict[str, Any]]:
        params = {
            'info_hash': info_hash,
            'peer_id': self.peer_id,
            'port': self.port,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': left,
            'event': event,
            'compact': 1,
            'numwant': 50
        }
        
        # Build query string
        query_parts = []
        for key, value in params.items():
            if isinstance(value, bytes):
                query_parts.append(f"{key}={urllib.parse.quote(value)}")
            else:
                query_parts.append(f"{key}={value}")
        
        query_string = '&'.join(query_parts)
        full_url = f"{announce_url}?{query_string}"
        
        try:
            response = urllib.request.urlopen(full_url, timeout=10)
            response_data = response.read()
            
            # Parse bencode response
            from torrent_parser import TorrentParser
            parser = TorrentParser("")
            tracker_response = parser._decode_bencode(response_data)
            
            if b'failure reason' in tracker_response:
                print(f"Tracker error: {tracker_response[b'failure reason'].decode()}")
                return []
            
            return self._parse_peers(tracker_response[b'peers'])
            
        except Exception as e:
            print(f"HTTP tracker error: {e}")
            return []
    
    def scrape_udp_tracker(self, announce_url: str, info_hash: bytes,
                          uploaded: int = 0, downloaded: int = 0,
                          left: int = 0, event: int = 2) -> List[Dict[str, Any]]:
        try:
            # Parse UDP URL
            parsed = urllib.parse.urlparse(announce_url)
            host = parsed.hostname
            port = parsed.port or 80
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            
            # Connect request
            connection_id = 0x41727101980
            action = 0  # connect
            transaction_id = random.randint(0, 2**32 - 1)
            
            connect_request = struct.pack('>QII', connection_id, action, transaction_id)
            sock.sendto(connect_request, (host, port))
            
            response, _ = sock.recvfrom(16)
            resp_action, resp_transaction_id, connection_id = struct.unpack('>IIQ', response)
            
            if resp_action != 0 or resp_transaction_id != transaction_id:
                return []
            
            # Announce request
            action = 1  # announce
            transaction_id = random.randint(0, 2**32 - 1)
            key = random.randint(0, 2**32 - 1)
            
            announce_request = struct.pack(
                '>QII20s20sQQQIIIiH',
                connection_id, action, transaction_id,
                info_hash, self.peer_id,
                downloaded, left, uploaded,
                event, 0, key, -1, self.port
            )
            
            sock.sendto(announce_request, (host, port))
            response, _ = sock.recvfrom(1024)
            
            if len(response) < 20:
                return []
            
            resp_action, resp_transaction_id, interval, leechers, seeders = struct.unpack('>IIIII', response[:20])
            
            if resp_action != 1 or resp_transaction_id != transaction_id:
                return []
            
            # Parse peers
            peers_data = response[20:]
            return self._parse_compact_peers(peers_data)
            
        except Exception as e:
            print(f"UDP tracker error: {e}")
            return []
        finally:
            if 'sock' in locals():
                sock.close()
    
    def _parse_peers(self, peers_data: bytes) -> List[Dict[str, Any]]:
        return self._parse_compact_peers(peers_data)
    
    def _parse_compact_peers(self, peers_data: bytes) -> List[Dict[str, Any]]:
        """Parse compact peer format (6 bytes per peer: 4 for IP, 2 for port)"""
        peers = []
        for i in range(0, len(peers_data), 6):
            if i + 6 <= len(peers_data):
                ip_bytes = peers_data[i:i+4]
                port_bytes = peers_data[i+4:i+6]
                
                ip = '.'.join(str(b) for b in ip_bytes)
                port = struct.unpack('>H', port_bytes)[0]
                
                peers.append({
                    'ip': ip,
                    'port': port
                })
        
        return peers
