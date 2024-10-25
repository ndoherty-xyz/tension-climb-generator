import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import json

class ClimbGenerator:
    def __init__(self):
        self.transitions: Dict[str, Dict[Tuple[int, int, int], List[Tuple[int, int, int, float]]]] = defaultdict(lambda: defaultdict(list))
        self.start_positions: Dict[str, List[Tuple[int, int, int, float]]] = defaultdict(list)
        self.difficulties: List[str] = []
        
        # Constants for role constraints
        self.FOOTHOLD_ROLE = 8
        self.FOOTHOLD_MAX_Y = 32
        self.START_ROLE = 5        # Start holds
        self.FINISH_ROLE = 7       # Finish holds
        self.MAX_WINGSPAN = 50     # Maximum distance for paired holds

    @classmethod
    def from_json(cls, json_path: str) -> 'ClimbGenerator':
        """Create and train a generator from a JSON file."""
        generator = cls()
        
        # Load and validate JSON data
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            # Validate data structure
            if not isinstance(data, list):
                raise ValueError("JSON file should contain a list of climbs")
                
            generator.train_on_data(data)
            return generator
            
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON file")
        except FileNotFoundError:
            raise ValueError(f"File not found: {json_path}")
        
    def save_generated_climbs(self, climbs: List[Dict[str, any]], output_path: str):
        """Save generated climbs to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(climbs, f, indent=2)
        
    def add_climb(self, difficulty: str, moves: List[Dict[str, int]]):
        """Add a climb to the training data."""
        if difficulty not in self.difficulties:
            self.difficulties.append(difficulty)
            
        # Add starting hold to start_positions
        start = (moves[0]['x'], moves[0]['y'], moves[0]['role'])
        self._add_to_distribution(self.start_positions[difficulty], start)
        
        # Add transitions between consecutive holds
        for i in range(len(moves) - 1):
            current = (moves[i]['x'], moves[i]['y'], moves[i]['role'])
            next_hold = (moves[i + 1]['x'], moves[i + 1]['y'], moves[i + 1]['role'])
            self._add_to_distribution(self.transitions[difficulty][current], next_hold)
    
    def _add_to_distribution(self, distribution: List[Tuple[int, int, int, float]], 
                           state: Tuple[int, int, int]):
        """Add a state to a distribution and normalize probabilities."""
        for i, (x, y, role, _) in enumerate(distribution):
            if (x, y, role) == state:
                distribution[i] = (x, y, role, distribution[i][3] + 1)
                break
        else:
            distribution.append((*state, 1.0))
        
        total = sum(prob for _, _, _, prob in distribution)
        for i in range(len(distribution)):
            x, y, role, count = distribution[i]
            distribution[i] = (x, y, role, count / total)
    
    def _calculate_distance(self, hold1: Tuple[int, int, int], hold2: Tuple[int, int, int]) -> float:
        """Calculate distance between two holds."""
        return ((hold1[0] - hold2[0]) ** 2 + (hold1[1] - hold2[1]) ** 2) ** 0.5
        
    def _find_paired_hold_distance(self, climb: List[Dict[str, int]], role: int) -> Optional[float]:
        """Find distance between holds of the same role if there are multiple."""
        holds = [(h['x'], h['y']) for h in climb if h['role'] == role]
        if len(holds) == 2:
            return ((holds[0][0] - holds[1][0]) ** 2 + (holds[0][1] - holds[1][1]) ** 2) ** 0.5
        return None

    def _is_valid_paired_holds(self, climb: List[Dict[str, int]], new_hold: Tuple[int, int, int]) -> bool:
        """Check if adding this hold maintains valid paired hold distances."""
        temp_climb = climb.copy()
        temp_climb.append({"x": new_hold[0], "y": new_hold[1], "role": new_hold[2]})
        
        # Check start holds spacing
        if new_hold[2] == self.START_ROLE:
            distance = self._find_paired_hold_distance(temp_climb, self.START_ROLE)
            if distance and distance > self.MAX_WINGSPAN:
                return False
                
        # Check finish holds spacing
        if new_hold[2] == self.FINISH_ROLE:
            distance = self._find_paired_hold_distance(temp_climb, self.FINISH_ROLE)
            if distance and distance > self.MAX_WINGSPAN:
                return False
                
        return True
    
    def _select_from_distribution(self, distribution: List[Tuple[int, int, int, float]], 
                                current_climb: List[Dict[str, int]],
                                role_counts: Dict[int, int]) -> Optional[Tuple[int, int, int]]:
        """Select a state from a probability distribution with climbing constraints."""
        if not distribution:
            return None
            
        # Get current y position
        current_y = current_climb[-1]['y'] if current_climb else 0
            
        # Filter valid next holds based on constraints
        valid_holds = []
        for x, y, role, prob in distribution:
            # Enforce upward movement (allow small downward moves for traverses)
            if y < current_y - 8:  # Allow up to 8 units down for traverses
                continue
                
            # Enforce foothold height restriction
            if role == self.FOOTHOLD_ROLE and y > self.FOOTHOLD_MAX_Y:
                continue
                
            # Check role count constraints
            if role == self.START_ROLE and role_counts[role] >= 2:
                continue
            if role == self.FINISH_ROLE and role_counts[role] >= 2:
                continue
                
            # Check paired holds spacing
            if not self._is_valid_paired_holds(current_climb, (x, y, role)):
                continue
                
            valid_holds.append((x, y, role, prob))
        
        if not valid_holds:
            return None
            
        # Normalize probabilities of valid holds
        total_prob = sum(prob for _, _, _, prob in valid_holds)
        if total_prob == 0:
            return None
            
        r = np.random.random() * total_prob
        cumsum = 0
        for x, y, role, prob in valid_holds:
            cumsum += prob
            if r <= cumsum:
                return (x, y, role)
        return valid_holds[-1][:3]
    
    def _is_valid_transition(self, current: Tuple[int, int, int], next_hold: Tuple[int, int, int]) -> bool:
        """Validate if a transition is physically reasonable."""
        x1, y1, _ = current
        x2, y2, _ = next_hold
        
        distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        
        # Climbing-specific constraints
        MAX_REACH = 50  # Maximum reasonable reach distance
        MIN_REACH = 8   # Minimum distance between holds
        MAX_Y_CHANGE = 40  # Maximum vertical change in one move
        
        # Check distance constraints
        if not (MIN_REACH <= distance <= MAX_REACH):
            return False
            
        # Check vertical movement
        y_change = y2 - y1
        if abs(y_change) > MAX_Y_CHANGE:
            return False
            
        return True
    
    def generate_climb(self, difficulty: str, min_moves: int = 8, max_moves: int = 20,
                      max_attempts: int = 100) -> Optional[List[Dict[str, int]]]:
        """Generate a new climb of specified difficulty with climbing constraints."""
        if difficulty not in self.difficulties:
            raise ValueError(f"No training data for difficulty {difficulty}")
        
        for _ in range(max_attempts):
            climb = []
            role_counts = defaultdict(int)
            
            # Start with start hold(s)
            start = self._select_from_distribution(self.start_positions[difficulty], climb, role_counts)
            if not start:
                continue
                
            climb.append({"x": start[0], "y": start[1], "role": start[2]})
            role_counts[start[2]] += 1
            
            # If difficulty warrants two start holds, try to add another
            if np.random.random() < 0.3:  # 30% chance for two start holds
                second_start = self._select_from_distribution(
                    self.transitions[difficulty][start],
                    climb,
                    role_counts
                )
                if second_start and second_start[2] == self.START_ROLE:
                    climb.append({"x": second_start[0], "y": second_start[1], "role": second_start[2]})
                    role_counts[second_start[2]] += 1
            
            current = start
            
            # Generate subsequent moves
            for _ in range(max_moves - 1):
                next_hold = self._select_from_distribution(
                    self.transitions[difficulty][current],
                    climb,
                    role_counts
                )
                
                if not next_hold or not self._is_valid_transition(current, next_hold):
                    break
                    
                climb.append({"x": next_hold[0], "y": next_hold[1], "role": next_hold[2]})
                role_counts[next_hold[2]] += 1
                current = next_hold
                
                # If we have enough moves and at least one finish hold, consider ending
                if (len(climb) >= min_moves and 
                    1 <= role_counts[self.START_ROLE] <= 2 and 
                    role_counts[self.FINISH_ROLE] >= 1):
                    break
            
            # Validate final climb
            if (min_moves <= len(climb) <= max_moves and
                1 <= role_counts[self.START_ROLE] <= 2 and
                1 <= role_counts[self.FINISH_ROLE] <= 2):
                return climb
                
        return None

    def train_on_data(self, climbs_data: List[Dict[str, any]]):
        """Train the generator on a list of climbs."""
        for climb_data in climbs_data:
            self.add_climb(climb_data["difficulty"], climb_data["climb"])

# Example usage:
def example_usage():
    # Sample training data (in your format)
    training_data = [
        {
            "difficulty": "V0",
            "climb": [
                {"x": -16, "y": 4, "role": 8},
                {"x": 8, "y": 4, "role": 8},
                # ... more moves ...
            ]
        },
        # ... more climbs ...
    ]
    
    generator = ClimbGenerator()
    generator.train_on_data(training_data)
    new_climb = generator.generate_climb("V0", min_moves=8, max_moves=20)
    
    return new_climb