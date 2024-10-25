import sqlite3
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Move:
    x: int
    y: int
    color: str

class SequenceDecoder:
    def __init__(self, db_path: str = "dbs/Tension.sqlite"):
        self.db_path = db_path
        self.color_map = {
            '5': 'green',
            '6': 'blue',
            '7': 'red',
            '8': 'pink'
        }

    def _get_db_connection(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(self.db_path)

    def _get_coordinates(self, conn: sqlite3.Connection, placement_id: int) -> Optional[tuple]:
        """Get x,y coordinates for a placement ID from the database."""
        query = """
            SELECT h.x, h.y 
            FROM placements p
            JOIN holes h ON p.hole_id = h.id
            WHERE p.id = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (placement_id,))
        return cursor.fetchone()

    def decode_sequence(self, sequence: str) -> List[Move]:
        """
        Decode a climbing sequence string into a list of moves with coordinates and colors.
        
        Args:
            sequence: String in format "p[num]r[num]..." where p is placement and r is color
            
        Returns:
            List of Move objects containing x, y coordinates and color
        """
        moves = []
        pattern = re.compile(r'p(\d+)r(\d+)')
        
        with self._get_db_connection() as conn:
            for match in pattern.finditer(sequence):
                placement_id = int(match.group(1))
                color_code = match.group(2)
                
                if color_code not in self.color_map:
                    print(f"Warning: Invalid color code {color_code} for placement {placement_id}")
                    continue
                
                coordinates = self._get_coordinates(conn, placement_id)
                if coordinates is None:
                    print(f"Warning: No coordinates found for placement {placement_id}")
                    continue
                
                moves.append(Move(
                    x=coordinates[0],
                    y=coordinates[1],
                    color=self.color_map[color_code]
                ))
        
        return moves

def decode_sequences(sequences: List[str]) -> Dict[str, List[Move]]:
    """
    Batch process multiple sequences.
    
    Args:
        sequences: List of sequence strings to decode
        
    Returns:
        Dictionary mapping sequence strings to their decoded moves
    """
    decoder = SequenceDecoder()
    return {sequence: decoder.decode_sequence(sequence) for sequence in sequences}

# Example usage:
if __name__ == "__main__":
    # Single sequence example
    decoder = SequenceDecoder()
    sequence = "p802r5p803r6"
    moves = decoder.decode_sequence(sequence)
    print(f"\nSequence: {sequence}")
    for move in moves:
        print(f"x: {move.x}, y: {move.y}, color: {move.color}")
    
    # Batch processing example
    sequences = [
        "p802r5p803r6",
        "p890r8p918r8p932r8"
    ]
    results = decode_sequences(sequences)
    
    print("\nBatch results:")
    for seq, moves in results.items():
        print(f"\nSequence: {seq}")
        for move in moves:
            print(f"x: {move.x}, y: {move.y}, color: {move.color}")