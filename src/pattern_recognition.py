from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Set, Dict, Any
import random
import re
import json

@dataclass
class ClimbingConstraints:
    MIN_X = -64  
    MAX_X = 64   
    MIN_Y = 4    
    MAX_Y = 140  
    MIN_ROLE = 5
    MAX_ROLE = 8
    MIN_R7_COUNT = 1
    MAX_R7_COUNT = 2
    MIN_R5_COUNT = 1
    MAX_R5_COUNT = 2
    R7_MIN_HEIGHT_PERCENTAGE = 0.7
    GRID_SIZE = 8
    Y_OFFSET = 4
    
    # Role 5/7 proximity constraints
    MAX_ROLE57_SPACING = 32
    MAX_ROLE57_Y_DIFF = 32
    
    # Role 5 height constraints
    R5_MIN_Y = 30
    R5_MAX_Y = 70

    @property
    def x_range(self) -> int:
        return self.MAX_X - self.MIN_X

    @property
    def y_range(self) -> int:
        return self.MAX_Y - self.MIN_Y

    def valid_x(self, x: int) -> bool:
        """Check if x coordinate is valid (divisible by 8)"""
        return (x % self.GRID_SIZE == 0) and (self.MIN_X <= x <= self.MAX_X)

    def valid_y(self, y: int) -> bool:
        """Check if y coordinate is valid (y % 8 == 4)"""
        return (y % self.GRID_SIZE == self.Y_OFFSET) and (self.MIN_Y <= y <= self.MAX_Y)
    
    def valid_r5_y(self, y: int) -> bool:
        """Check if y coordinate is valid for role 5 holds"""
        return (self.valid_y(y) and 
                self.R5_MIN_Y <= y <= self.R5_MAX_Y)

    def get_valid_x_coordinates(self) -> List[int]:
        """Get all valid x coordinates"""
        return list(range(self.MIN_X, self.MAX_X + 1, self.GRID_SIZE))

    def get_valid_y_coordinates(self) -> List[int]:
        """Get all valid y coordinates"""
        start_y = self.MIN_Y
        if start_y % self.GRID_SIZE != self.Y_OFFSET:
            start_y = ((start_y // self.GRID_SIZE) * self.GRID_SIZE) + self.Y_OFFSET
        return list(range(start_y, self.MAX_Y + 1, self.GRID_SIZE))
    
    def get_valid_r5_y_coordinates(self) -> List[int]:
        """Get valid y coordinates for role 5 holds"""
        return [y for y in self.get_valid_y_coordinates() 
                if self.R5_MIN_Y <= y <= self.R5_MAX_Y]

    def get_nearby_coordinates(self, x: int, y: int, used_coords: set, 
                             for_role: int = None) -> List[Tuple[int, int]]:
        """Get valid nearby coordinates within MAX_ROLE57_SPACING"""
        nearby_coords = []
        valid_x = self.get_valid_x_coordinates()
        
        # Use role-specific y coordinates if needed
        if for_role == 5:
            valid_y = self.get_valid_r5_y_coordinates()
        else:
            valid_y = self.get_valid_y_coordinates()
        
        for new_x in valid_x:
            if abs(new_x - x) > self.MAX_ROLE57_SPACING:
                continue
            for new_y in valid_y:
                if abs(new_y - y) > self.MAX_ROLE57_Y_DIFF:
                    continue
                if (new_x, new_y) not in used_coords:
                    nearby_coords.append((new_x, new_y))
        
        return nearby_coords

class ClimbingPatternAnalyzer:
    def __init__(self):
        self.constraints = ClimbingConstraints()
        self.difficulty_patterns = defaultdict(lambda: {
            'hold_counts': [],
            'role_frequencies': defaultdict(int),
            'vertical_spacing': [],
            'horizontal_spacing': [],
            'common_roles': [],
            'common_pairs': defaultdict(int),
            'coordinate_ranges': {
                'x': {'min': float('inf'), 'max': float('-inf')},
                'y': {'min': float('inf'), 'max': float('-inf')}
            },
            'x_distribution': defaultdict(int),
            'y_distribution': defaultdict(int),
            'role7_y_positions': []
        })

    @classmethod
    def from_json_file(cls, filepath: str):
        """Create and initialize an analyzer from a JSON file"""
        analyzer = cls()
        
        try:
            with open(filepath, 'r') as f:
                training_data = json.load(f)
            
            analyzer.analyze_climbs(training_data)
            print(f"Successfully loaded and analyzed {len(training_data)} climbs")
            
            # Print summary of difficulties found
            difficulties = set(climb['difficulty'] for climb in training_data)
            print(f"Found difficulties: {sorted(difficulties)}")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Training data file not found: {filepath}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in file: {filepath}")
        except KeyError as e:
            raise ValueError(f"Missing required field in training data: {e}")
            
        return analyzer

    def validate_climb(self, holds: List[Dict[str, int]]) -> bool:
        """Validate if a climb meets all constraints"""
        if not holds:
            return False
            
        # Check coordinate ranges and grid alignment
        for hold in holds:
            if not (self.constraints.valid_x(hold['x'])):
                return False
                     
            if (self.constraints.valid_y(hold['y'])):
                return False
            
        # Check role ranges and counts
        roles = [h['role'] for h in holds]
        r7_count = roles.count(7)
        r5_count = roles.count(5)
        
        if not all(self.constraints.MIN_ROLE <= r <= self.constraints.MAX_ROLE for r in roles):
            return False
            
        if not (self.constraints.MIN_R7_COUNT <= r7_count <= self.constraints.MAX_R7_COUNT):
            return False
            
        if not (self.constraints.MIN_R5_COUNT <= r5_count <= self.constraints.MAX_R5_COUNT):
            return False
        
        # Validate vertical progression
        for i in range(len(holds) - 1):
            if holds[i+1]['y'] < holds[i]['y'] - 8:  # Allow small downward movements
                return False

        # Validate role 7 placement
        max_y = max(h['y'] for h in holds)
        min_y = min(h['y'] for h in holds)
        height_threshold = min_y + (max_y - min_y) * self.constraints.R7_MIN_HEIGHT_PERCENTAGE
        
        role7_holds = [h for h in holds if h['role'] == 7]
        if any(h['y'] < height_threshold for h in role7_holds):
            return False
            
        return True

    def analyze_climbs(self, climbs_data: List[Dict[str, Any]]):
        """Analyze patterns in climbing data"""
        for climb_data in climbs_data:
            difficulty = climb_data['difficulty']
            holds = climb_data['climb']
            
            # if not self.validate_climb(holds):
            #     print(f"Warning: Invalid climb found for {difficulty}")
            #     continue
                
            patterns = self.difficulty_patterns[difficulty]
            
            # Find max height for this climb
            max_y = max(h['y'] for h in holds)
            min_y = min(h['y'] for h in holds)
            climb_height = max_y - min_y
            
            # Track relative positions of role 7 holds
            for hold in holds:
                if hold['role'] == 7:
                    relative_height = (hold['y'] - min_y) / climb_height if climb_height > 0 else 1
                    patterns['role7_y_positions'].append(relative_height)
            
            # Rest of the analysis...
            patterns['hold_counts'].append(len(holds))
            
            for hold in holds:
                patterns['role_frequencies'][hold['role']] += 1
                patterns['x_distribution'][hold['x']] += 1
                patterns['y_distribution'][hold['y']] += 1
            
            for hold in holds:
                patterns['coordinate_ranges']['x']['min'] = min(patterns['coordinate_ranges']['x']['min'], hold['x'])
                patterns['coordinate_ranges']['x']['max'] = max(patterns['coordinate_ranges']['x']['max'], hold['x'])
                patterns['coordinate_ranges']['y']['min'] = min(patterns['coordinate_ranges']['y']['min'], hold['y'])
                patterns['coordinate_ranges']['y']['max'] = max(patterns['coordinate_ranges']['y']['max'], hold['y'])
            
            for i in range(len(holds) - 1):
                vertical_spacing = holds[i+1]['y'] - holds[i]['y']
                horizontal_spacing = holds[i+1]['x'] - holds[i]['x']
                patterns['vertical_spacing'].append(vertical_spacing)
                patterns['horizontal_spacing'].append(horizontal_spacing)
                patterns['common_pairs'][(holds[i]['role'], holds[i+1]['role'])] += 1

class ClimbingGenerator:
    def __init__(self, analyzer: ClimbingPatternAnalyzer):
        self.analyzer = analyzer
        self.constraints = ClimbingConstraints()


    def generate_climb(self, difficulty: str) -> List[Dict[str, int]]:
        """Generate a new climb for the given difficulty"""
        patterns = self.analyzer.difficulty_patterns[difficulty]
        
        if not patterns['hold_counts']:
            raise ValueError(f"No patterns analyzed for difficulty {difficulty}")
        
        num_holds = random.choice(patterns['hold_counts'])
        roles = self._generate_valid_roles(num_holds)
        
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                return self._generate_valid_coordinates(num_holds, patterns, roles)
            except ValueError as e:
                if attempt == max_attempts - 1:
                    raise
                continue

    def _generate_valid_roles(self, num_holds: int) -> List[int]:
        """Generate a valid sequence of roles"""
        while True:
            roles = []
            # Ensure required r5s and r7s
            roles.extend([5] * random.randint(self.constraints.MIN_R5_COUNT, 
                                           self.constraints.MAX_R5_COUNT))
            roles.extend([7] * random.randint(self.constraints.MIN_R7_COUNT,
                                           self.constraints.MAX_R7_COUNT))
            
            # Fill remaining slots with 6s and 8s
            remaining = num_holds - len(roles)
            if remaining < 0:
                continue
                
            roles.extend(random.choices([6, 8], k=remaining))
            random.shuffle(roles)
            
            return roles

    def _generate_valid_coordinates(self, num_holds: int, patterns: Dict, roles: List[int]) -> List[Dict[str, int]]:
        """Generate valid coordinates for holds"""
        holds = []
        used_coords = set()
        
        valid_x_coords = self.constraints.get_valid_x_coordinates()
        valid_y_coords = self.constraints.get_valid_y_coordinates()
        
        # Calculate height threshold for role 7
        min_y = min(valid_y_coords)
        max_y = max(valid_y_coords)
        height_threshold = min_y + int((max_y - min_y) * self.constraints.R7_MIN_HEIGHT_PERCENTAGE)
        height_threshold = min(
            valid_y_coords[next(i for i, y in enumerate(valid_y_coords) if y >= height_threshold)],
            max_y
        )

        # Group holds by role
        role_groups = {
            5: [i for i, role in enumerate(roles) if role == 5],
            6: [i for i, role in enumerate(roles) if role == 6],
            7: [i for i, role in enumerate(roles) if role == 7],
            8: [i for i, role in enumerate(roles) if role == 8]
        }

        hold_positions = [None] * len(roles)

        # Helper function to find next standard coordinate
        def find_next_coordinate(current_x: int, current_y: int, 
                               is_role7: bool = False) -> Tuple[int, int]:
            valid_y_range = [y for y in valid_y_coords if y > current_y] if not is_role7 else \
                           [y for y in valid_y_coords if y >= height_threshold]
            
            if not valid_y_range:
                return None, None

            new_y = random.choice(valid_y_range[:3]) if not is_role7 else random.choice(valid_y_range)
            
            max_x_change = 3 * self.constraints.GRID_SIZE
            valid_x_range = [x for x in valid_x_coords 
                           if abs(x - current_x) <= max_x_change
                           and (x, new_y) not in used_coords]
            
            if not valid_x_range:
                valid_x_range = [x for x in valid_x_coords 
                               if (x, new_y) not in used_coords]
                
            if not valid_x_range:
                return None, None
                
            new_x = random.choice(valid_x_range)
            return new_x, new_y

        # Place role 5 holds (within specific height range)
        if role_groups[5]:
            # Place first role 5 hold
            current_x = random.choice(valid_x_coords)
            valid_r5_y = self.constraints.get_valid_r5_y_coordinates()
            if not valid_r5_y:
                raise ValueError("No valid y coordinates available for role 5 holds")
            
            current_y = random.choice(valid_r5_y)
            
            hold_positions[role_groups[5][0]] = {
                'x': current_x,
                'y': current_y,
                'role': 5
            }
            used_coords.add((current_x, current_y))

            # Place additional role 5 holds nearby
            for idx in role_groups[5][1:]:
                nearby_coords = self.constraints.get_nearby_coordinates(
                    current_x, current_y, used_coords, for_role=5)
                
                if not nearby_coords:
                    raise ValueError("Could not find valid coordinates for additional role 5 hold")
                
                new_x, new_y = random.choice(nearby_coords)
                hold_positions[idx] = {
                    'x': new_x,
                    'y': new_y,
                    'role': 5
                }
                used_coords.add((new_x, new_y))

        # Place role 7 holds (near the top, close together)
        if role_groups[7]:
            # Place first role 7 hold
            current_x = random.choice(valid_x_coords)
            valid_top_y = [y for y in valid_y_coords if y >= height_threshold]
            current_y = random.choice(valid_top_y)
            
            hold_positions[role_groups[7][0]] = {
                'x': current_x,
                'y': current_y,
                'role': 7
            }
            used_coords.add((current_x, current_y))

            # Place additional role 7 holds nearby
            for idx in role_groups[7][1:]:
                nearby_coords = self.constraints.get_nearby_coordinates(
                    current_x, current_y, used_coords, for_role=7)
                nearby_coords = [(x, y) for x, y in nearby_coords if y >= height_threshold]
                
                if not nearby_coords:
                    raise ValueError("Could not find valid coordinates for additional role 7 hold")
                
                new_x, new_y = random.choice(nearby_coords)
                hold_positions[idx] = {
                    'x': new_x,
                    'y': new_y,
                    'role': 7
                }
                used_coords.add((new_x, new_y))

        # Place remaining holds (roles 6 and 8)
        current_x = random.choice(valid_x_coords)
        current_y = min(valid_y_coords) + self.constraints.GRID_SIZE

        for role in [6, 8]:
            for idx in role_groups[role]:
                if (current_x, current_y) in used_coords:
                    current_x, current_y = find_next_coordinate(current_x, current_y)
                    if current_x is None:
                        raise ValueError(f"Could not find valid coordinates for role {role} hold")
                
                hold_positions[idx] = {
                    'x': current_x,
                    'y': current_y,
                    'role': role
                }
                used_coords.add((current_x, current_y))
                
                current_x, current_y = find_next_coordinate(current_x, current_y)
                if current_x is None:
                    raise ValueError(f"Could not find valid coordinates for next hold")

        # Remove any None values and sort by height
        holds = [h for h in hold_positions if h is not None]
        holds.sort(key=lambda h: h['y'])
        
        return holds
    
    def save_patterns_to_json(self, filepath: str):
        """Save analyzed patterns to a JSON file"""
        serializable_patterns = {}
        for difficulty, patterns in self.analyzer.difficulty_patterns.items():
            serializable_patterns[difficulty] = {
                'hold_counts': patterns['hold_counts'],
                'role_frequencies': dict(patterns['role_frequencies']),
                'vertical_spacing': patterns['vertical_spacing'],
                'horizontal_spacing': patterns['horizontal_spacing'],
                'coordinate_ranges': patterns['coordinate_ranges'],
                'x_distribution': dict(patterns['x_distribution']),
                'y_distribution': dict(patterns['y_distribution']),
                'common_pairs': {str(k): v for k, v in patterns['common_pairs'].items()}
            }
            
        with open(filepath, 'w') as f:
            json.dump(serializable_patterns, f, indent=2)

def main():
    # Path to your JSON training data file
    training_data_path = "data/processed/climb_sequences.json"
    
    try:
        # Create analyzer from JSON file
        analyzer = ClimbingPatternAnalyzer.from_json_file(training_data_path)
        
        # Create generator
        generator = ClimbingGenerator(analyzer)
        
        # Generate example climbs for each difficulty found in the training data
        for difficulty in analyzer.difficulty_patterns.keys():
            print(f"\nGenerating new {difficulty} climb:")
            try:
                new_climb = generator.generate_climb(difficulty)
                print(new_climb)
            except Exception as e:
                print(f"Error generating {difficulty} climb: {e}")
        
        # Optionally save patterns for later use
        analyzer.save_patterns_to_json("data/processed/analyzed_patterns.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()