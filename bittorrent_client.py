import os
import random
import string
import threading
import time
from typing import List, Dict, Any
from torrent_parser import TorrentParser
from tracker_client import TrackerClient
from peer_connection import PeerConnection
from piece_manager import PieceManager

class BitTorrentClient:    
    def __init__(self, download_path: str = "./downloads"):
        self.download_path = download_path
        self.peer_id = self._generate_peer_id()
        self.port = 6881
        
        self.torrent_metadata = None
        self.piece_manager = None
        self.tracker_client = None
        self.peer_connections = {}
        
        self.running = False
        
    def _generate_peer_id(self) -> bytes:
        prefix = b"-PY0001-"
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        return prefix + suffix.encode()
    
    def load_torrent(self, torrent_path: str) -> bool:
        try:
            parser = TorrentParser(torrent_path)
            self.torrent_metadata = parser.parse()
            
            print(f"Loaded torrent: {self.torrent_metadata['name']}")
            print(f"Total size: {self.torrent_metadata['total_length']} bytes")
            print(f"Pieces: {self.torrent_metadata['num_pieces']}")
            print(f"Files: {len(self.torrent_metadata['files'])}")
            
            # Initialize piece manager
            self.piece_manager = PieceManager(self.torrent_metadata, self.download_path)
            
            # Initialize tracker client
            self.tracker_client = TrackerClient(self.peer_id, self.port)
            
            return True
            
        except Exception as e:
            print(f"Error loading torrent: {e}")
            return False
    
    def start_download(self):
        if not self.torrent_metadata:
            print("No torrent loaded!")
            return
        
        self.running = True
        
        # Start peer discovery and connection thread
        threading.Thread(target=self._peer_discovery_loop, daemon=True).start()
        
        # Start status reporting thread
        threading.Thread(target=self._status_loop, daemon=True).start()
        
        print("Download started!")
    
    def stop_download(self):
        self.running = False
        
        # Disconnect all peers
        for peer_conn in list(self.peer_connections.values()):
            peer_conn.disconnect()
        
        self.peer_connections.clear()
        print("Download stopped!")
    
    def _peer_discovery_loop(self):
        while self.running:
            try:
                # Get peers from trackers
                peers = self._get_peers_from_trackers()
                
                # Connect to new peers
                for peer in peers:
                    if len(self.peer_connections) >= 50:  # Limit connections
                        break
                    
                    peer_key = f"{peer['ip']}:{peer['port']}"
                    if peer_key not in self.peer_connections:
                        self._connect_to_peer(peer['ip'], peer['port'])
                
                # Clean up dead connections
                self._cleanup_dead_connections()
                
                time.sleep(30)  # Wait before next tracker scrape
                
            except Exception as e:
                print(f"Peer discovery error: {e}")
                time.sleep(10)
    
    def _get_peers_from_trackers(self) -> List[Dict[str, Any]]:
        all_peers = []
        
        # Try main announce URL
        announce_url = self.torrent_metadata['announce']
        if announce_url.startswith('http'):
            peers = self.tracker_client.scrape_http_tracker(
                announce_url, 
                self.torrent_metadata['info_hash'],
                left=self._get_bytes_left()
            )
            all_peers.extend(peers)
        elif announce_url.startswith('udp'):
            peers = self.tracker_client.scrape_udp_tracker(
                announce_url,
                self.torrent_metadata['info_hash'],
                left=self._get_bytes_left()
            )
            all_peers.extend(peers)
        
        # Try announce list
        for tier in self.torrent_metadata['announce_list']:
            for url in tier:
                if len(all_peers) >= 100:  # Limit peer list
                    break
                
                try:
                    if url.startswith('http'):
                        peers = self.tracker_client.scrape_http_tracker(
                            url,
                            self.torrent_metadata['info_hash'],
                            left=self._get_bytes_left()
                        )
                        all_peers.extend(peers)
                    elif url.startswith('udp'):
                        peers = self.tracker_client.scrape_udp_tracker(
                            url,
                            self.torrent_metadata['info_hash'],
                            left=self._get_bytes_left()
                        )
                        all_peers.extend(peers)
                except:
                    continue
        
        return all_peers
    
    def _get_bytes_left(self) -> int:
        if not self.piece_manager:
            return self.torrent_metadata['total_length']
        
        completed_bytes = 0
        for i, is_complete in enumerate(self.piece_manager.completed_pieces):
            if is_complete:
                completed_bytes += self.piece_manager.get_piece_length(i)
        
        return max(0, self.torrent_metadata['total_length'] - completed_bytes)
    
    def _connect_to_peer(self, ip: str, port: int):
        peer_key = f"{ip}:{port}"
        
        try:
            peer_conn = PeerConnection(
                ip, port,
                self.torrent_metadata['info_hash'],
                self.peer_id,
                self.piece_manager,
                self._on_piece_received
            )
            
            if peer_conn.connect():
                self.peer_connections[peer_key] = peer_conn
                print(f"Connected to peer: {peer_key}")
            
        except Exception as e:
            print(f"Failed to connect to {peer_key}: {e}")
    
    def _cleanup_dead_connections(self):
        dead_peers = []
        for peer_key, peer_conn in self.peer_connections.items():
            if not peer_conn.connected:
                dead_peers.append(peer_key)
        
        for peer_key in dead_peers:
            del self.peer_connections[peer_key]
    
    def _on_piece_received(self, piece_index: int):
        completion = self.piece_manager.get_completion_percentage()
        completed_pieces = sum(self.piece_manager.completed_pieces)
        total_pieces = self.piece_manager.num_pieces
        print(f"[✓] Completed piece {piece_index} ({completed_pieces}/{total_pieces}) - Progress: {completion:.3f}%")
        
        # Check if download is complete
        if completion >= 100.0:
            print("Download completed!")
            self.stop_download()

    def _status_loop(self):
        while self.running:
            if self.piece_manager:
                completion = self.piece_manager.get_completion_percentage()
                completed_pieces = sum(self.piece_manager.completed_pieces)
                total_pieces = self.piece_manager.num_pieces
                active_peers = len([p for p in self.peer_connections.values() if p.connected])
                total_peers = len(self.peer_connections)
                bytes_left = self._get_bytes_left()
                downloaded_bytes = self.torrent_metadata['total_length'] - bytes_left
                print(f"Progress: {completion:.3f}% ({completed_pieces}/{total_pieces} pieces) | Downloaded: {downloaded_bytes:,} bytes | Peers: {active_peers}/{total_peers} | Remaining: {bytes_left:,} bytes")
            
            time.sleep(10)

    def get_status(self) -> Dict[str, Any]:
        if not self.piece_manager:
            return {"status": "No torrent loaded"}
        
        return {
            "completion": self.piece_manager.get_completion_percentage(),
            "active_peers": len([p for p in self.peer_connections.values() if p.connected]),
            "total_peers": len(self.peer_connections),
            "bytes_left": self._get_bytes_left(),
            "total_size": self.torrent_metadata['total_length']
        }

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python bittorrent_client.py <torrent_file>")
        return
    
    torrent_file = sys.argv[1]
    
    if not os.path.exists(torrent_file):
        print(f"Torrent file not found: {torrent_file}")
        return
    
    # Create client
    client = BitTorrentClient()
    
    # Load torrent
    if not client.load_torrent(torrent_file):
        print("Failed to load torrent file")
        return
    
    # Start download
    client.start_download()
    
    try:
        # Keep running until user stops
        while client.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping download...")
        client.stop_download()

if __name__ == "__main__":
    main()
