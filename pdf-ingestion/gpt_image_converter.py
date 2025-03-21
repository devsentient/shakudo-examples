from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from llm_provider import llm_invoke
from PIL import Image
import base64
import os

# Set up OpenAI API key
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")


def encode_image(image_path):
    """Encodes an image into base64 format for sending to OpenAI Vision API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_image(image_path):
    """Uses GPT-4 Vision to analyze if an image can be converted into a table and returns structured data or a description."""

    # Encode image to base64
    base64_image = encode_image(image_path)

    # Construct the query
    query = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Does this image contain a table? If so, extract it in markdown format. If not, provide a concise description. When multiple charts exists. make sure it contains every chart. description should including trends, stats if possible. Return only the Markdown",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
            ]
        )
    ]

    # Get response from GPT-4 Vision
    response = llm_invoke(query)

    return response.content  # Returns either a table (markdown format) or a description


# Example usage:
if __name__ == "__main__":
    image_path = "./extracted_images/image_3.png"  # Replace with your image file path
    result = analyze_image(image_path)
    print(result)  # Prints either a table representation or a description
