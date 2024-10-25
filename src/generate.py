# from pattern_recognition import ClimbingPatternAnalyzer, ClimbingGenerator
from markov_chain import ClimbGenerator
from sequence_decoder import SequenceDecoder
from svg_generation import generate_coordinate_svg
import json
import argparse

class IntegratedClimbGenerator:

    ROLE_TO_COLOR = {
        5: "green",
        6: "blue",
        7: "red",
        8: "pink"
    }

    def __init__(self, training_data_path: str, db_path: str):
        """
        Initialize the integrated climb generator.
        
        Args:
            training_data_path: Path to the JSON training data
            db_path: Path to the SQLite database
        """
        # Initialize the pattern analyzer and generator
        # self.analyzer = ClimbingPatternAnalyzer.from_json_file(training_data_path)
        # self.generator = ClimbingGenerator(self.analyzer)
        

        #initialize markov chain analyzer and generator
        self.generator = ClimbGenerator.from_json(training_data_path)
        
        # Initialize the sequence decoder
        self.decoder = SequenceDecoder(db_path)

    def generate_climb(self, difficulty: str, output_svg_path: str = None):
        """
        Generate a complete climbing problem.
        
        Args:
            difficulty: The target difficulty (e.g., "V3")
            output_svg_path: Optional path to save the SVG file
            
        Returns:
            tuple: (sequence, moves, svg_output)
        """
        # Generate the climb sequence
        try:
            moves = self.generator.generate_climb(difficulty)
            print(f"Generated sequence: {moves}")
        except Exception as e:
            raise Exception(f"Error generating climb: {e}")


        # Convert moves to the format expected by the SVG generator
        svg_points = [
            {
                "x": move['x'],
                "y": move['y'],
                "color": self.ROLE_TO_COLOR[move["role"]]
            }
            for move in moves
        ]

        # Generate SVG
        try:
            svg_output = generate_coordinate_svg(svg_points)
            if output_svg_path:
                with open(output_svg_path, 'w') as f:
                    f.write(svg_output)
                print(f"SVG saved to: {output_svg_path}")
        except Exception as e:
            raise Exception(f"Error generating SVG: {e}")

        return moves, svg_output

def main():
    parser = argparse.ArgumentParser(description='Generate a climbing problem')
    parser.add_argument('difficulty', type=str, help='Target difficulty (e.g., "V3")')
    parser.add_argument('--training-data', type=str, 
                        default='data/processed/climb_sequences.json',
                        help='Path to training data JSON')
    parser.add_argument('--db-path', type=str, 
                        default='dbs/Tension.sqlite',
                        help='Path to SQLite database')
    parser.add_argument('--output', type=str, 
                        default='generated_climb.svg',
                        help='Output path for SVG file')

    args = parser.parse_args()

    try:
        generator = IntegratedClimbGenerator(args.training_data, args.db_path)
        moves, svg = generator.generate_climb(args.difficulty, args.output)
        
        # Print summary
        print("\nGeneration Summary:")
        print(f"Difficulty: {args.difficulty}")
        print(f"Number of moves: {len(moves)}")
        print("Move sequence:")
        for i, move in enumerate(moves, 1):
            color = generator.ROLE_TO_COLOR[move["role"]]
            print(f"  {i}. ({move['x']}, {move['y']}) - {color}")
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()