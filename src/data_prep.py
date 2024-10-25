import pandas as pd
import numpy as np
import sqlite3
from typing import List, Dict, Tuple
import os
import json
from pathlib import Path
import re

class ClimbSequencePreprocessor:
    def __init__(self, db_path: str, grades_path: str):
        """Initialize the preprocessor with SQLite database path and grades mapping path"""
        self.db_path = db_path
        self.grade_mapping = self._load_grade_mapping(grades_path)
        
    def _load_grade_mapping(self, grades_path: str) -> Dict[int, str]:
        """Load grade mapping from JSON file and extract V-grades"""
        with open(grades_path, 'r') as f:
            grades_data = json.load(f)
            
        # Create mapping from difficulty number to V-grade only
        grade_mapping = {}
        for item in grades_data:
            # Split on '/' and take the V-grade portion
            v_grade = item['boulder_name'].split('/')[1]
            grade_mapping[item['difficulty']] = v_grade
            
        return grade_mapping
        
    def get_connection(self):
        """Create a connection to the SQLite database"""
        return sqlite3.connect(self.db_path)
    
    def round_difficulty(self, difficulty: float) -> int:
        """Round difficulty to nearest integer and clamp between 1-39"""
        rounded = int(round(difficulty))
        return max(1, min(39, rounded))

    def parse_sequence(self, sequence: str) -> List[Tuple[int, int]]:
        """Parse sequence string into list of (placement_id, role) tuples"""
        # Pattern to match placement_id and role
        pattern = r'p(\d+)r(\d+)'
        return [(int(p), int(r)) for p, r in re.findall(pattern, sequence)]

    def get_placement_coordinates(self, placement_ids: List[int]) -> Dict[int, Dict]:
        """Get x,y coordinates for a list of placement IDs"""
        query = """
        SELECT p.id as placement_id, h.x, h.y
        FROM placements p
        JOIN holes h ON p.hole_id = h.id
        WHERE p.id IN ({})
        """.format(','.join('?' * len(placement_ids)))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, placement_ids)
            results = cursor.fetchall()
            
        # Create mapping of placement_id to coordinates
        return {pid: {'x': x, 'y': y} for pid, x, y in results}
    
    def fetch_raw_data(self) -> pd.DataFrame:
        """Fetch climbs with their difficulties and frames data"""
        query = """
            SELECT c.uuid, c.frames, ccf.display_difficulty
            FROM climbs c
            JOIN climb_cache_fields ccf ON c.uuid = ccf.climb_uuid
            WHERE c.is_listed = 1 
            AND c.is_draft = 0
            AND c.layout_id = 11
            AND display_difficulty IS NOT NULL
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)
    
    def validate_sequence(self, sequence: str) -> bool:
        """Validate that a sequence string is properly formatted"""
        if not sequence:
            return False
            
        # Should start with 'p'
        if not sequence.startswith('p'):
            return False
            
        # Basic pattern check
        pattern = r'^(p\d+r\d+)+$'
        return bool(re.match(pattern, sequence))
    
    def prepare_training_data(self) -> List[Dict]:
        """Prepare sequence training data with x,y coordinates"""
        # Fetch climbs data
        climbs_df = self.fetch_raw_data()
        
        training_data = []
        for _, climb in climbs_df.iterrows():
            try:
                sequence = climb['frames']
                if self.validate_sequence(sequence):
                    # Parse sequence into placement_id and role pairs
                    moves = self.parse_sequence(sequence)
                    
                    # Get coordinates for all placement_ids
                    placement_ids = [m[0] for m in moves]
                    coord_mapping = self.get_placement_coordinates(placement_ids)
                    
                    # Create climb sequence with coordinates and roles
                    climb_sequence = []
                    for pid, role in moves:
                        if pid in coord_mapping:
                            coords = coord_mapping[pid]
                            climb_sequence.append({
                                'x': coords['x'],
                                'y': coords['y'],
                                'role': role
                            })
                    
                    # Sort by y value increasing
                    climb_sequence.sort(key=lambda m: m['y'])
                    
                    # Round the difficulty and get the V-grade
                    rounded_difficulty = self.round_difficulty(climb['display_difficulty'])
                    v_grade = self.grade_mapping.get(rounded_difficulty)
                    
                    if v_grade and climb_sequence:  # Only add if we have valid grade and coordinates
                        training_example = {
                            'difficulty': v_grade,
                            'climb': climb_sequence
                        }
                        training_data.append(training_example)
                
            except Exception as e:
                print(f"Error processing climb {climb['uuid']}: {str(e)}")
                continue
        
        return training_data
    
    def analyze_sequences(self, training_data: List[Dict]) -> Dict:
        """Analyze sequence patterns in the dataset"""
        analysis = {
            'total_climbs': len(training_data),
            'grade_distribution': {},
            'sequence_lengths': {},
            'coordinate_ranges': {
                'x': {'min': float('inf'), 'max': float('-inf')},
                'y': {'min': float('inf'), 'max': float('-inf')}
            }
        }
        
        # Collect statistics
        lengths = []
        grades = {}
        
        for climb in training_data:
            # Sequence length
            seq_len = len(climb['climb'])
            lengths.append(seq_len)
            
            # Grade distribution
            grade = climb['difficulty']
            grades[grade] = grades.get(grade, 0) + 1
            
            # Track coordinate ranges
            for move in climb['climb']:
                analysis['coordinate_ranges']['x']['min'] = min(analysis['coordinate_ranges']['x']['min'], move['x'])
                analysis['coordinate_ranges']['x']['max'] = max(analysis['coordinate_ranges']['x']['max'], move['x'])
                analysis['coordinate_ranges']['y']['min'] = min(analysis['coordinate_ranges']['y']['min'], move['y'])
                analysis['coordinate_ranges']['y']['max'] = max(analysis['coordinate_ranges']['y']['max'], move['y'])
        
        # Calculate statistics
        analysis['sequence_lengths'] = {
            'mean': np.mean(lengths),
            'std': np.std(lengths),
            'min': min(lengths),
            'max': max(lengths)
        }
        
        # Sort grades by V-number
        sorted_grades = sorted(grades.items(), key=lambda x: int(x[0].replace('V', '')) if x[0] != 'V0' else 0)
        analysis['grade_distribution'] = dict(sorted_grades)
        
        return analysis
    
    def save_training_data(self, training_data: List[Dict], 
                          output_path: str) -> None:
        """Save processed training data to file"""
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)

def main():
    # Get the project root directory (2 levels up from this script)
    project_root = Path(__file__).parent.parent
    
    # Construct paths
    db_path = project_root / "dbs" / "Tension.sqlite"
    grades_path = project_root / "data" / "difficulty_grades.json"
    output_path = project_root / "data" / "processed" / "climb_sequences.json"
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize preprocessor
    preprocessor = ClimbSequencePreprocessor(str(db_path), str(grades_path))
    
    # Prepare training data
    training_data = preprocessor.prepare_training_data()
    
    # Analyze the sequences
    analysis = preprocessor.analyze_sequences(training_data)
    print("\nDataset Analysis:")
    print(f"Total climbs: {analysis['total_climbs']}")
    print(f"\nSequence Length Statistics:")
    print(f"Average length: {analysis['sequence_lengths']['mean']:.1f} moves")
    print(f"Length range: {analysis['sequence_lengths']['min']} - {analysis['sequence_lengths']['max']} moves")
    
    print(f"\nGrade Distribution:")
    for grade, count in analysis['grade_distribution'].items():
        print(f"{grade}: {count} climbs")
        
    print(f"\nCoordinate Ranges:")
    print(f"X: {analysis['coordinate_ranges']['x']['min']} to {analysis['coordinate_ranges']['x']['max']}")
    print(f"Y: {analysis['coordinate_ranges']['y']['min']} to {analysis['coordinate_ranges']['y']['max']}")
    
    # Save processed data
    preprocessor.save_training_data(training_data, str(output_path))
    
    print(f"\nProcessed {len(training_data)} climbs for training")
    print(f"Data saved to: {output_path}")

if __name__ == "__main__":
    main()