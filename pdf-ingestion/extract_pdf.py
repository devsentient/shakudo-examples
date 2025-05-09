import pdfplumber
from gpt_image_converter import analyze_image
import os
from uuid import uuid4
IMAGE_EXTRACTION = False

def extract_text_and_images(pdf_path, output_folder="extracted_images", resolution=200):
    os.makedirs(output_folder, exist_ok=True)

    extracted_data = []
    image_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text()
            if text:
                extracted_data.append({"type": "text", "content": text.strip()})

            # Convert full page to high-resolution image
            pil_image = page.to_image(resolution=resolution).original
            img_width, img_height = pil_image.size  # Get image dimensions

            # Extract images
            for img_index, img in enumerate(page.images):
                image_count += 1
                uuid = uuid4()
                image_id = f"image_{uuid}.png"
                image_path = os.path.join(output_folder, image_id)

                # Get original PDF coordinate system size
                pdf_width, pdf_height = page.width, page.height

                # Scale coordinates based on the resolution change
                scale_x = img_width / pdf_width
                scale_y = img_height / pdf_height

                x0, top, x1, bottom = img["x0"], img["top"], img["x1"], img["bottom"]
                cropped_img = pil_image.crop(
                    (
                        int(x0 * scale_x),
                        int(top * scale_y),
                        int(x1 * scale_x),
                        int(bottom * scale_y),
                    )
                )

                # Save cropped image
                cropped_img.save(image_path, "PNG")

                extracted_data.append({"type": "image", "id": image_id})

    return extracted_data


import os


def process_pdfs(pdf_dir, md_dir, keep_image=False):
    """
    Loops over all PDF files in `pdf_dir`, extracts text and images,
    then writes the results to a single Markdown file `md_file_name`.
    """
    # Open the output markdown file in write mode
    os.makedirs(md_dir, exist_ok=True)
    # Loop over everything in the pdf_dir
    for file_name in os.listdir(pdf_dir):
        if file_name.lower().endswith(".pdf"):
            md_file_name = os.path.join(md_dir, file_name + ".md")
            with open(md_file_name, "w", encoding="utf-8") as md_file:
                pdf_path = os.path.join(pdf_dir, file_name)

                # Extract text and images from this PDF
                output = extract_text_and_images(pdf_path)

                # Write a header to separate sections for each PDF
                md_file.write(f"# Results for {file_name}\n\n")

                # Loop over the items returned by extract_text_and_images
                for item in output:
                    if item["type"] == "text":
                        # Write text content directly to the MD file
                        md_file.write(item["content"] + "\n\n")
                    elif item["type"] == "image" and IMAGE_EXTRACTION:
                        # Write a reference to the extracted image into the MD file
                        # (You could embed it using Markdown image syntax,
                        #  or simply note that an image was found.)
                        image_path = os.path.join("extracted_images", item["id"])
                        # md_file.write(f"![Image: {item['id']}]({image_path})\n\n")

                        # Optionally call analyze_image(image_path) and write its output
                        analysis = analyze_image(image_path)
                        if keep_image:
                            os.remove(image_path)
                        md_file.write(f"\n<Chart Analysis>\n {analysis}\n</Chart Analysis>\n")

                # Add a separator/newline before the next PDF
                md_file.write("\n---\n\n")


# Example usage
if __name__ == "__main__":
    pdf_folder = "./pdf_input"
    output_md = "./pdf_output"
    process_pdfs(pdf_folder, output_md)

    print(f"Results written to {output_md}")
