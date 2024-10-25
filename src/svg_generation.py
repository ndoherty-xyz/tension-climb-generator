def generate_coordinate_svg(points, width=1290, height=1393, circle_radius=30, stroke_width=5, show_guides=True, 
                          background_image="assets/tension-board-12x12-spray.png"):
    """
    Generate SVG markup for visualizing coordinates with normalized positioning.
    
    Args:
        points: List of dictionaries containing x,y coordinates and color,
               e.g. [{"x": -64, "y": 140, "color": "red"}, ...]
               Valid colors are: "red", "green", "pink", "blue"
        width: Width of the SVG viewport (default: 1290)
        height: Height of the SVG viewport (default: 1393)
        circle_radius: Radius of the circles (default: 30)
        stroke_width: Width of the circle outline (default: 3)
        show_guides: Whether to show reference lines (default: True)
        background_image: Path to the background image
    
    Returns:
        String containing SVG markup
    """
    def normalize_x(x):
        """Normalize x from [-64, 64] to [31, 1253]"""
        input_range = 128  # 64 - (-64)
        output_range = 1253 - 31
        return 31 + ((x + 64) / input_range) * output_range
    
    def normalize_y(y):
        """Normalize y from [4, 140] to [1346, 54]"""
        input_range = 140 - 4
        output_range = 1346 - 54
        return 1346 - ((y - 4) / input_range) * output_range
    
    # Color mapping with specific values
    color_map = {
        "red": "#FF0000",
        "green": "#00FF00",
        "pink": "#FF69B4",
        "blue": "#0000FF"
    }
    
    # Start SVG markup with a defs section for the background image
    svg_elements = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
        '  <defs>',
        f'    <image id="background" width="{width}" height="{height}" xlink:href="{background_image}"/>',
        '  </defs>',
        
        # Add background rectangle with image
        '  <use xlink:href="#background" x="0" y="0"/>'
    ]
    
    # Add guide lines if requested
    if show_guides:
        guides = [
            # Vertical guides
            f'  <line x1="31" y1="0" x2="31" y2="{height}" stroke="lightgray" stroke-width="1" stroke-dasharray="4"/>',
            f'  <line x1="1253" y1="0" x2="1253" y2="{height}" stroke="lightgray" stroke-width="1" stroke-dasharray="4"/>',
            # Horizontal guides
            f'  <line x1="0" y1="54" x2="{width}" y2="54" stroke="lightgray" stroke-width="1" stroke-dasharray="4"/>',
            f'  <line x1="0" y1="1346" x2="{width}" y2="1346" stroke="lightgray" stroke-width="1" stroke-dasharray="4"/>'
        ]
        svg_elements.extend(guides)
    
    # Add circles for each point
    for point in points:
        x = normalize_x(point['x'])
        y = normalize_y(point['y'])
        color = color_map.get(point.get('color', 'blue').lower(), color_map['blue'])  # Default to blue if color is invalid
        circle = (f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{circle_radius}" '
                 f'fill="none" stroke="{color}" stroke-width="{stroke_width}"/>')
        svg_elements.append(circle)
    
    # Close SVG tag
    svg_elements.append('</svg>')
    
    return '\n'.join(svg_elements)

# Example usage
if __name__ == "__main__":
    test_points = [
        {"x": -64, "y": 140, "color": "red"},      # Red circle
        {"x": 64, "y": 4, "color": "green"},       # Green circle
        {"x": 0, "y": 72, "color": "pink"},        # Pink circle
        {"x": -32, "y": 100, "color": "blue"}      # Blue circle
    ]
    
    svg_output = generate_coordinate_svg(test_points)
    
    # Save to file
    with open('coordinates.svg', 'w') as f:
        f.write(svg_output)

    # Print the SVG markup
    print(svg_output)