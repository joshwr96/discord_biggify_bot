from PIL import Image
import io

def biggify_image(image_bytes: bytes, rows: int, stretch_factor: float = 1.5, output_scale_factor: float = 2.0) -> list[io.BytesIO]:
    """
    Stretches the image horizontally, splits it into horizontal strips, and then
    optionally scales up each strip for larger previews. This version does NOT
    perform any aspect ratio or resolution correction (cropping/padding).

    Args:
        image_bytes: The image data as bytes.
        rows: The number of horizontal strips to split the stretched image into.
        stretch_factor: A float (e.g., 1.5 for 150% width). A larger factor means
                        more horizontal stretching.
        output_scale_factor: A float (e.g., 2.0 to double the size of each output strip).
                             This scales the final cropped strips. Default is 2.0.

    Returns:
        A list of io.BytesIO objects, each containing a horizontally stretched, cropped,
        and potentially scaled image strip.
        Returns an empty list if an error occurs.
    """
    try:
        # Open the image from bytes
        original_img = Image.open(io.BytesIO(image_bytes))
        original_width, original_height = original_img.size

        # Validate input for rows, stretch_factor, and output_scale_factor
        if rows <= 0:
            print("Error: Rows must be a positive integer.")
            return []
        if not (1.0 <= stretch_factor <= 3.0): # Limiting stretch factor to prevent extreme distortion
            print("Error: Stretch factor must be between 1.0 and 3.0.")
            return []
        if not (0.5 <= output_scale_factor <= 4.0): # Limiting output scale to prevent excessive file sizes
            print("Error: Output scale factor must be between 0.5 and 4.0.")
            return []

        # --- No Aspect Ratio/Resolution Correction ---
        # The image is used as-is, without any initial cropping or padding.
        img_for_processing = original_img
        current_width, current_height = img_for_processing.size

        # 1. Horizontally stretch the entire image
        stretched_width = int(current_width * stretch_factor)
        
        # Resize the image, stretching it horizontally. Use LANCZOS for good quality.
        stretched_img = img_for_processing.resize((stretched_width, current_height), Image.LANCZOS)
        
        # Update dimensions to the new, stretched image's dimensions
        current_width, current_height = stretched_img.size # Re-assign after stretching

        # 2. Split this stretched image into horizontal strips
        part_height = current_height / rows

        cropped_images = []

        for r in range(rows):
            # Define the bounding box for the current horizontal strip
            left = 0
            top = int(r * part_height)
            right = current_width
            bottom = int((r + 1) * part_height)

            # Adjust for potential off-by-one errors due to integer division
            if r == rows - 1:
                bottom = current_height

            box = (left, top, right, bottom)
            
            # Crop the image to get the strip
            cropped_strip = stretched_img.crop(box)

            # 3. Apply output scaling to the cropped strip
            if output_scale_factor != 1.0: # Only resize if scaling is needed
                new_strip_width = int(cropped_strip.width * output_scale_factor)
                new_strip_height = int(cropped_strip.height * output_scale_factor)
                cropped_strip = cropped_strip.resize((new_strip_width, new_strip_height), Image.LANCZOS)

            # Save the cropped strip to a BytesIO object in memory
            img_byte_arr = io.BytesIO()
            # Use the original image format if available, otherwise default to PNG
            cropped_strip.save(img_byte_arr, format=original_img.format if original_img.format else "PNG")
            img_byte_arr.seek(0) # Rewind the buffer to the beginning for reading
            cropped_images.append(img_byte_arr)

        return cropped_images
    except Exception as e:
        print(f"Error processing image in biggify_image: {e}")
        return []

# Example usage for local testing (run this file directly to test the image processing)
if __name__ == '__main__':
    # Create a dummy image for testing if one doesn't exist
    try:
        # Attempt to open an existing image for testing
        with open("example.png", "rb") as f: 
            image_data = f.read()
        print("Using existing example.png for testing.")
    except FileNotFoundError:
        print("example.png not found. Creating a dummy image for testing.")
        # Create a simple dummy image (e.g., a face-like shape)
        # Make it a non-16:9 aspect ratio to test the padding
        dummy_img = Image.new('RGB', (300, 400), color = 'lightgray') 
        # Draw a simple "face" for better visual testing of centering
        from PIL import ImageDraw
        draw = ImageDraw.Draw(dummy_img)
        draw.ellipse((50, 100, 250, 300), fill='pink', outline='black') # Face
        draw.ellipse((90, 160, 120, 190), fill='blue') # Left eye
        draw.ellipse((180, 160, 210, 190), fill='blue') # Right eye
        draw.arc((120, 220, 180, 260), 0, 180, fill='black', width=3) # Mouth
        
        dummy_img_bytes_io = io.BytesIO()
        dummy_img.save(dummy_img_bytes_io, format="PNG")
        image_data = dummy_img_bytes_io.getvalue()
        with open("example.png", "wb") as f:
            f.write(image_data)
        print("Dummy example.png created.")

    try:
        # Test splitting into 4 rows with a stretch factor of 1.5 and default output scale of 2.0
        print("\nTesting 4 rows split (stretch 1.5, default output scale 2.0):")
        stretched_sections_4_rows = biggify_image(image_data, 4, stretch_factor=1.5)
        for i, section in enumerate(stretched_sections_4_rows):
            # For local testing, we need to reset the buffer after reading for saving
            section.seek(0)
            with open(f"section_4rows_stretched_scaled_part_{i+1}.png", "wb") as f:
                f.write(section.read())
            print(f"Saved section_4rows_stretched_scaled_part_{i+1}.png")
        print(f"Successfully saved {len(stretched_sections_4_rows)} sections.")

        # Test invalid input
        print("\nTesting invalid input (0 rows):")
        invalid_sections = biggify_image(image_data, 0)
        print(f"Invalid input test resulted in {len(invalid_sections)} sections.")

    except Exception as e:
        print(f"An unexpected error occurred during local testing: {e}")

def merge_images(image_bytes_list: list[bytes]) -> io.BytesIO | None:
    """
    Merges a list of image bytes (assumed to be horizontal strips) vertically into a single image.

    Args:
        image_bytes_list: A list of image data as bytes, where each item is a strip.

    Returns:
        An io.BytesIO object containing the merged image, or None if an error occurs.
    """
    if not image_bytes_list:
        print("Error: No images provided for merging.")
        return None

    try:
        images = []
        for img_bytes in image_bytes_list:
            images.append(Image.open(io.BytesIO(img_bytes)))

        # Determine the dimensions of the merged image
        # Width will be the width of the first image (assuming all have same width)
        # Height will be the sum of all image heights
        merged_width = images[0].width
        merged_height = sum(img.height for img in images)

        # Create a new blank image for the merged result
        # Use RGB mode for consistency, or determine from first image
        merged_img = Image.new('RGB', (merged_width, merged_height))

        current_height_offset = 0
        for img in images:
            merged_img.paste(img, (0, current_height_offset))
            current_height_offset += img.height

        # Save the merged image to a BytesIO object
        img_byte_arr = io.BytesIO()
        merged_img.save(img_byte_arr, format="PNG") # PNG is a good default for quality
        img_byte_arr.seek(0)
        return img_byte_arr

    except Exception as e:
        print(f"Error merging images: {e}")
        return None
