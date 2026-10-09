import sys
import os
import argparse
import ollama

# Add the parent directory to sys.path so we can import config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Send an image to Ollama for OCR.")
    parser.add_argument("image_path", help="Path to the image file")
    args = parser.parse_args()

    # 1. Check if the file exists
    if not os.path.exists(args.image_path):
        print(f"❌ Error: File not found at '{args.image_path}'.")
        print("   Please check the path and try again.")
        sys.exit(1)

    # 2. Send the image to Ollama
    try:
        print(f"⏳ Sending image to {config.MODEL_NAME}...")
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=[
                {
                    'role': 'user',
                    'content': 'Copy out the text you can read in this image, exactly as printed',
                    'images': [args.image_path]
                }
            ]
        )
        # 3. Print the answer
        print("\n--- Result ---")
        print(response['message']['content'])
        print("--------------")

    # 4. Handle Ollama not running
    except ConnectionError:
        print("❌ Error: Could not connect to Ollama.")
        print("   Please make sure the Ollama application is open and running in the background.")
        sys.exit(1)
        
    # 5. Handle Model not found
    except ollama.ResponseError as e:
        if e.status_code == 404:
            print(f"❌ Error: Model '{config.MODEL_NAME}' not found.")
            print("   Please run the following command in your terminal to pull the model:")
            print(f"   ollama pull {config.MODEL_NAME}")
        else:
            print(f"❌ Ollama returned an error: {e}")
        sys.exit(1)
        
    # 6. Handle any other unexpected errors
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()