import hashlib
import struct
from typing import Dict, List, Any, Optional, Union

class TorrentParser:    
    def __init__(self, torrent_path: str):
        self.torrent_path = torrent_path
        self.torrent_data = None
        self.info_hash = None
        
    def parse(self) -> Dict[str, Any]:
        with open(self.torrent_path, 'rb') as f:
            torrent_bytes = f.read()
        
        self.torrent_data = self._decode_bencode(torrent_bytes)
        
        # Calculate info hash
        info_bytes = self._encode_bencode(self.torrent_data[b'info'])
        self.info_hash = hashlib.sha1(info_bytes).digest()
        
        return self._extract_metadata()
    
    def _decode_bencode(self, data: bytes) -> Any:
        def decode_next(data: bytes, index: int = 0):
            if data[index:index+1] == b'i':
                # Integer
                end = data.find(b'e', index)
                return int(data[index+1:end]), end + 1
            elif data[index:index+1] == b'l':
                # List
                result = []
                index += 1
                while data[index:index+1] != b'e':
                    item, index = decode_next(data, index)
                    result.append(item)
                return result, index + 1
            elif data[index:index+1] == b'd':
                # Dictionary
                result = {}
                index += 1
                while data[index:index+1] != b'e':
                    key, index = decode_next(data, index)
                    value, index = decode_next(data, index)
                    result[key] = value
                return result, index + 1
            elif data[index:index+1].isdigit():
                # String
                colon = data.find(b':', index)
                length = int(data[index:colon])
                return data[colon+1:colon+1+length], colon + 1 + length
            else:
                raise ValueError(f"Invalid bencode at index {index}")
        
        result, _ = decode_next(data)
        return result
    
    def _encode_bencode(self, data: Any) -> bytes:
        if isinstance(data, int):
            return f"i{data}e".encode()
        elif isinstance(data, bytes):
            return f"{len(data)}:".encode() + data
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
            return f"{len(data_bytes)}:".encode() + data_bytes
        elif isinstance(data, list):
            result = b'l'
            for item in data:
                result += self._encode_bencode(item)
            result += b'e'
            return result
        elif isinstance(data, dict):
            result = b'd'
            for key in sorted(data.keys()):
                result += self._encode_bencode(key)
                result += self._encode_bencode(data[key])
            result += b'e'
            return result
        else:
            raise ValueError(f"Cannot encode type {type(data)}")
    
    def _extract_metadata(self) -> Dict[str, Any]:
        info = self.torrent_data[b'info']
        
        metadata = {
            'announce': self.torrent_data[b'announce'].decode('utf-8'),
            'announce_list': [],
            'info_hash': self.info_hash,
            'piece_length': info[b'piece length'],
            'pieces': info[b'pieces'],
            'name': info[b'name'].decode('utf-8'),
            'files': [],
            'total_length': 0
        }
        
        # Handle announce list
        if b'announce-list' in self.torrent_data:
            for tier in self.torrent_data[b'announce-list']:
                tier_urls = [url.decode('utf-8') for url in tier]
                metadata['announce_list'].append(tier_urls)
        
        # Handle files (single or multiple)
        if b'files' in info:
            # Multi-file torrent
            for file_info in info[b'files']:
                file_path = '/'.join([path.decode('utf-8') for path in file_info[b'path']])
                metadata['files'].append({
                    'path': file_path,
                    'length': file_info[b'length']
                })
                metadata['total_length'] += file_info[b'length']
        else:
            # Single file torrent
            metadata['files'].append({
                'path': metadata['name'],
                'length': info[b'length']
            })
            metadata['total_length'] = info[b'length']
        
        # Calculate number of pieces
        metadata['num_pieces'] = len(metadata['pieces']) // 20
        
        return metadata
