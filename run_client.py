#!/usr/bin/env python3
"""
Simple script to run the BitTorrent client
Usage: python run_client.py <path_to_torrent_file>
"""

import sys
import os
import time
from bittorrent_client import BitTorrentClient
import peer_connection
print("Using PeerConnection from:", peer_connection.__file__)


def main():
    print("=== PyBitTorrent Client ===")
    
    if len(sys.argv) != 2:
        print("Usage: python run_client.py <torrent_file>")
        print("Example: python run_client.py ubuntu.torrent")
        return
    
    torrent_file = sys.argv[1]
    
    if not os.path.exists(torrent_file):
        print(f"Error: Torrent file '{torrent_file}' not found!")
        return
    
    # Create downloads directory
    download_dir = "./downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # Initialize client
    print(f"Initializing BitTorrent client...")
    client = BitTorrentClient(download_dir)
    
    # Load torrent
    print(f"Loading torrent file: {torrent_file}")
    if not client.load_torrent(torrent_file):
        print("Failed to load torrent file!")
        return
    
    # Start download
    print("Starting download...")
    client.start_download()
    
    try:
        # Monitor progress
        while client.running:
            status = client.get_status()
            if isinstance(status, dict) and 'completion' in status:
                print(f"\rProgress: {status['completion']:.1f}% | "
                      f"Peers: {status['active_peers']}/{status['total_peers']} | "
                      f"Remaining: {status['bytes_left']} bytes", end='', flush=True)
                
                if status['completion'] >= 100.0:
                    print("\n✅ Download completed successfully!")
                    break
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Download interrupted by user")
    finally:
        print("Stopping client...")
        client.stop_download()
        print("Client stopped.")

if __name__ == "__main__":
    main()
