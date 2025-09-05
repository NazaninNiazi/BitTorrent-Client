import hashlib
import os
import threading
from typing import Dict, List, Optional

class PieceManager:
    
    def __init__(self, torrent_metadata: Dict, download_path: str = "./downloads"):
        self.metadata = torrent_metadata
        self.download_path = download_path
        self.piece_length = torrent_metadata['piece_length']
        self.total_length = torrent_metadata['total_length']
        self.num_pieces = torrent_metadata['num_pieces']
        self.pieces_hashes = self._parse_pieces_hashes(torrent_metadata['pieces'])
        
        # Track piece completion
        self.completed_pieces = [False] * self.num_pieces
        self.piece_data = {}  # piece_index -> {offset -> data}
        self.piece_locks = {i: threading.Lock() for i in range(self.num_pieces)}
        
        # File handling
        self.files = torrent_metadata['files']
        self.file_handles = {}
        
        # Create download directory
        os.makedirs(self.download_path, exist_ok=True)
        
        # Initialize files
        self._initialize_files()
    
    def _parse_pieces_hashes(self, pieces_data: bytes) -> List[bytes]:
        hashes = []
        for i in range(0, len(pieces_data), 20):
            hashes.append(pieces_data[i:i+20])
        return hashes
    
    def _initialize_files(self):
        for file_info in self.files:
            file_path = os.path.join(self.download_path, file_info['path'])
            
            # Create directory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create or open file
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.seek(file_info['length'] - 1)
                    f.write(b'\0')
    
    def get_piece_length(self, piece_index: int) -> int:
        if piece_index == self.num_pieces - 1:
            # Last piece might be shorter
            return self.total_length - (piece_index * self.piece_length)
        return self.piece_length
    
    def is_piece_complete(self, piece_index: int) -> bool:
        return self.completed_pieces[piece_index]
    
    def store_block(self, piece_index: int, offset: int, data: bytes) -> bool:
        with self.piece_locks[piece_index]:
            if piece_index not in self.piece_data:
                self.piece_data[piece_index] = {}
            
            self.piece_data[piece_index][offset] = data
            
            # Check if piece is complete
            piece_length = self.get_piece_length(piece_index)
            total_received = sum(len(block) for block in self.piece_data[piece_index].values())
            
            if total_received >= piece_length:
                return self._complete_piece(piece_index)
        
        return False
    
    def _complete_piece(self, piece_index: int) -> bool:
        # Reconstruct piece data
        piece_data = b''
        piece_length = self.get_piece_length(piece_index)
        
        # Sort blocks by offset
        sorted_blocks = sorted(self.piece_data[piece_index].items())
        current_offset = 0
        
        for offset, block_data in sorted_blocks:
            if offset != current_offset:
                # Missing data
                return False
            piece_data += block_data
            current_offset += len(block_data)
        
        if len(piece_data) != piece_length:
            return False
        
        # Verify hash
        piece_hash = hashlib.sha1(piece_data).digest()
        if piece_hash != self.pieces_hashes[piece_index]:
            print(f"Hash mismatch for piece {piece_index}")
            return False
        
        # Write to disk
        self._write_piece_to_disk(piece_index, piece_data)
        
        # Mark as complete
        self.completed_pieces[piece_index] = True
        
        # Clean up memory
        del self.piece_data[piece_index]
        
        print(f"Completed piece {piece_index}/{self.num_pieces}")
        return True
    
    def _write_piece_to_disk(self, piece_index: int, piece_data: bytes):
        piece_start = piece_index * self.piece_length
        piece_offset = 0
        
        current_file_offset = 0
        
        for file_info in self.files:
            file_start = current_file_offset
            file_end = current_file_offset + file_info['length']
            
            # Check if this piece overlaps with this file
            if piece_start < file_end and piece_start + len(piece_data) > file_start:
                # Calculate overlap
                overlap_start = max(piece_start, file_start)
                overlap_end = min(piece_start + len(piece_data), file_end)
                
                if overlap_start < overlap_end:
                    # Calculate offsets
                    file_offset = overlap_start - file_start
                    piece_data_offset = overlap_start - piece_start
                    overlap_length = overlap_end - overlap_start
                    
                    # Write data
                    file_path = os.path.join(self.download_path, file_info['path'])
                    with open(file_path, 'r+b') as f:
                        f.seek(file_offset)
                        f.write(piece_data[piece_data_offset:piece_data_offset + overlap_length])
            
            current_file_offset += file_info['length']
    
    def get_block(self, piece_index: int, offset: int, length: int) -> Optional[bytes]:
        if not self.is_piece_complete(piece_index):
            return None
        
        # Read from disk
        piece_start = piece_index * self.piece_length
        absolute_offset = piece_start + offset
        
        current_file_offset = 0
        
        for file_info in self.files:
            file_start = current_file_offset
            file_end = current_file_offset + file_info['length']
            
            if absolute_offset >= file_start and absolute_offset < file_end:
                file_path = os.path.join(self.download_path, file_info['path'])
                with open(file_path, 'rb') as f:
                    f.seek(absolute_offset - file_start)
                    return f.read(length)
            
            current_file_offset += file_info['length']
        
        return None
    
    def get_completion_percentage(self) -> float:
        completed = sum(self.completed_pieces)
        return (completed / self.num_pieces) * 100 if self.num_pieces > 0 else 0
    
    def get_missing_pieces(self) -> List[int]:
        return [i for i, completed in enumerate(self.completed_pieces) if not completed]
