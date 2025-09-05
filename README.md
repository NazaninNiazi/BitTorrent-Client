# BitTorrent Client

A complete **BitTorrent client** written in **Python**, implementing all the core features of the BitTorrent protocol.  
This project is designed both as a working torrent client and as a learning resource for understanding peer-to-peer communication.

---

## Features

- Parse `.torrent` files (with full bencode encoder/decoder)  
- Connect to **HTTP/HTTPS and UDP trackers**  
- Establish and manage **peer-to-peer connections**  
- Request and receive data blocks from peers  
- Manage pieces and verify data integrity with **SHA1 hashes**  
- Support for both **single-file and multi-file torrents**  
- Ability to **seed** to other peers  
- Efficient memory management and disk writing  

---

## Usage

### Quick Run
\`\`\`bash
python scripts/run_client.py path/to/file.torrent
\`\`\`

### Manual Run
\`\`\`bash
python scripts/bittorrent_client.py path/to/file.torrent
\`\`\`

## Project Structure
\`\`\`
📦 PyBitTorrent
 ┣ 📜 torrent_parser.py     # Torrent parser and bencode implementation
 ┣ 📜 tracker_client.py     # HTTP/UDP tracker communication
 ┣ 📜 peer_connection.py    # Peer connection and message handling
 ┣ 📜 piece_manager.py      # Piece and file writing management
 ┣ 📜 bittorrent_client.py  # Main BitTorrent client
 ┣ 📜 run_client.py         # Entry script for quick execution
\`\`\`

## Implementation Details

### Torrent Parser
- Full bencode encoder/decoder implementation
- Extracts metadata: announce URL, piece length, file list
- Computes info_hash for torrent identification

### Tracker Client
- Supports HTTP/HTTPS trackers
- Supports UDP trackers
- Handles announce lists and fallback logic

### Peer Connection
- Full handshake protocol implementation
- Handles standard BitTorrent messages:
  - choke, unchoke, interested, have, bitfield, request, piece
- Manages multiple concurrent connections
- Implements request pipelining for better performance

### Piece Manager
- Splits pieces into 16KB blocks
- Verifies integrity with SHA1 hash checks
- Writes data safely to disk
- Supports multi-file torrents

## Limitations and Notes

- Uses only the Python standard library (no external dependencies)
- Intended for learning and exploring the BitTorrent protocol
- Can serve as a foundation for advanced features such as DHT, magnet links, or streaming

## Example Output
\`\`\`yaml
=== PyBitTorrent Client ===
Loading torrent file: ubuntu.torrent
Loaded torrent: ubuntu-20.04.3-desktop-amd64.iso
Total size: 3379068928 bytes
Pieces: 1612
Files: 1
Download started!
Connected to peer: 192.168.1.100:51413
Received block: piece 0, offset 0
Completed piece 0/1612
Progress: 0.1% | Active peers: 3
Progress: 15.2% | Peers: 5/12 | Remaining: 2865432576 bytes
\`\`\`

## Conclusion

This project provides a fully functional BitTorrent client implemented from scratch in Python.
It is suitable for both practical file downloading and for learning the fundamentals of peer-to-peer networking and the BitTorrent protocol.
